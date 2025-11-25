from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from pathlib import Path
import logging
import threading
import os

from .models import Build
from projects.models import GitRepository, Commit
from projects.git_utils import checkout_commit, clone_or_update_repo, GitUtilsError
from .dagger_pipeline import run_build_sync
from .docker_utils import (
    start_container, stop_container, remove_container,
    get_container_logs, get_container_status, load_image_from_tar, DockerError
)

logger = logging.getLogger(__name__)


@login_required
def build_list(request):
    """List all builds."""
    builds = Build.objects.select_related('repository', 'commit').all()
    return render(request, 'builds/build_list.html', {
        'builds': builds
    })


@login_required
def build_detail(request, build_id):
    """View build details and logs."""
    build = get_object_or_404(Build, id=build_id)
    return render(request, 'builds/build_detail.html', {
        'build': build
    })


@login_required
def build_create(request, repo_id, commit_id):
    """Create a new build for a specific commit."""
    repository = get_object_or_404(GitRepository, id=repo_id)
    commit = get_object_or_404(Commit, id=commit_id, repository=repository)
    
    if request.method == 'POST':
        push_to_registry = request.POST.get('push_to_registry') == 'on'
        container_port = request.POST.get('container_port', 8080)
        
        try:
            container_port = int(container_port)
            if container_port < 1 or container_port > 65535:
                container_port = 8080
        except (ValueError, TypeError):
            container_port = 8080
        
        # Create build record
        build = Build.objects.create(
            repository=repository,
            commit=commit,
            branch_name=commit.branch.name if commit.branch else 'unknown',
            status='pending',
            push_to_registry=push_to_registry,
            container_port=container_port
        )
        
        # Start build in background thread
        # NOTE: For production, use a proper task queue like Celery instead of threading
        thread = threading.Thread(target=execute_build, args=(build.id,))
        thread.daemon = True
        thread.start()
        
        messages.success(request, f"Build #{build.id} started")
        return redirect('build_detail', build_id=build.id)
    
    return render(request, 'builds/build_create.html', {
        'repository': repository,
        'commit': commit
    })


@login_required
def start_build_container(request, build_id):
    """Start a container for a successful build."""
    build = get_object_or_404(Build, id=build_id)
    
    if request.method != 'POST':
        return redirect('build_detail', build_id=build_id)
    
    if build.status != 'success':
        messages.error(request, "Can only start containers for successful builds")
        return redirect('build_detail', build_id=build_id)
    
    if build.container_status == 'running':
        messages.warning(request, "Container is already running")
        return redirect('build_detail', build_id=build_id)
    
    try:
        # Determine the image tag to use
        image_tag = build.image_tag
        
        # If the build was local (not pushed to registry), we need to load from tar
        if not build.push_to_registry and build.image_tag:
            image_name = build.repository.name.lower().replace(' ', '-')
            commit_tag = build.commit.sha[:8]
            tar_path = settings.GIT_CHECKOUT_DIR / 'builds' / f"build_{build.id}" / f"{image_name}_{commit_tag}.tar"
            
            if os.path.exists(tar_path):
                image_tag = load_image_from_tar(str(tar_path))
            else:
                image_tag = build.image_tag
        
        build.container_status = 'starting'
        build.save()
        
        container_name = f"nohands-build-{build.id}"
        container_id, host_port = start_container(
            image_tag=image_tag,
            container_port=build.container_port,
            container_name=container_name
        )
        
        build.container_id = container_id
        build.host_port = host_port
        build.container_status = 'running'
        build.save()
        
        messages.success(request, f"Container started on port {host_port}")
        
    except DockerError as e:
        build.container_status = 'error'
        build.save()
        messages.error(request, f"Failed to start container: {e}")
        logger.error(f"Failed to start container for build #{build_id}: {e}")
    
    return redirect('build_detail', build_id=build_id)


@login_required
def stop_build_container(request, build_id):
    """Stop a running container for a build."""
    build = get_object_or_404(Build, id=build_id)
    
    if request.method != 'POST':
        return redirect('build_detail', build_id=build_id)
    
    if not build.container_id:
        messages.warning(request, "No container to stop")
        return redirect('build_detail', build_id=build_id)
    
    try:
        stop_container(build.container_id)
        remove_container(build.container_id)
        
        build.container_status = 'stopped'
        build.container_id = ''
        build.host_port = None
        build.save()
        
        messages.success(request, "Container stopped")
        
    except DockerError as e:
        messages.error(request, f"Failed to stop container: {e}")
        logger.error(f"Failed to stop container for build #{build_id}: {e}")
    
    return redirect('build_detail', build_id=build_id)


@login_required
def container_logs(request, build_id):
    """Get container logs for a build (JSON API)."""
    build = get_object_or_404(Build, id=build_id)
    
    if not build.container_id:
        return JsonResponse({
            'success': False,
            'error': 'No container running',
            'logs': ''
        })
    
    try:
        # Get the last 200 lines of logs
        tail = request.GET.get('tail', 200)
        try:
            tail = int(tail)
        except (ValueError, TypeError):
            tail = 200
        
        logs = get_container_logs(build.container_id, tail=tail)
        status = get_container_status(build.container_id)
        
        # Update container status if changed
        if status == 'exited' and build.container_status == 'running':
            build.container_status = 'stopped'
            build.save()
        
        return JsonResponse({
            'success': True,
            'logs': logs,
            'status': status,
            'container_id': build.container_id[:12]
        })
        
    except DockerError as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'logs': ''
        })


def execute_build(build_id: int):
    """
    Execute a build in the background.
    This function runs in a separate thread.
    """
    try:
        build = Build.objects.get(id=build_id)
        build.status = 'running'
        build.started_at = timezone.now()
        build.save()
        
        logger.info(f"Starting build #{build.id}")
        
        # Clone/update repository
        repo_cache_path = settings.GIT_CHECKOUT_DIR / 'cache' / build.repository.name
        clone_or_update_repo(build.repository.url, repo_cache_path)
        
        # Checkout specific commit
        checkout_path = settings.GIT_CHECKOUT_DIR / 'builds' / f"build_{build.id}"
        checkout_commit(repo_cache_path, build.commit.sha, checkout_path)
        
        # Generate image tag
        image_name = build.repository.name.lower().replace(' ', '-')
        image_tag = f"{build.commit.sha[:8]}"
        
        # Run Dagger build
        result = run_build_sync(
            source_dir=checkout_path,
            dockerfile_path=build.repository.dockerfile_path,
            image_name=image_name,
            image_tag=image_tag,
            push_to_registry=build.push_to_registry,
            registry_url=settings.DOCKER_REGISTRY if build.push_to_registry else None,
            registry_username=settings.DOCKER_REGISTRY_USERNAME if build.push_to_registry else None,
            registry_password=settings.DOCKER_REGISTRY_PASSWORD if build.push_to_registry else None,
        )
        
        # Update build with results
        build.status = result.status
        build.logs = result.logs
        build.image_tag = result.image_tag
        build.error_message = result.error_message
        build.completed_at = timezone.now()
        build.save()
        
        logger.info(f"Build #{build.id} completed with status: {result.status}")
        
    except Exception as e:
        logger.error(f"Build #{build_id} failed: {e}")
        try:
            build = Build.objects.get(id=build_id)
            build.status = 'failed'
            build.error_message = str(e)
            build.completed_at = timezone.now()
            build.save()
        except Exception:
            pass

