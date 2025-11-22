from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from pathlib import Path
import logging
import threading

from .models import Build
from projects.models import GitRepository, Commit
from projects.git_utils import checkout_commit, clone_or_update_repo, GitUtilsError
from .dagger_pipeline import run_build_sync

logger = logging.getLogger(__name__)


def build_list(request):
    """List all builds."""
    builds = Build.objects.select_related('repository', 'commit').all()
    return render(request, 'builds/build_list.html', {
        'builds': builds
    })


def build_detail(request, build_id):
    """View build details and logs."""
    build = get_object_or_404(Build, id=build_id)
    return render(request, 'builds/build_detail.html', {
        'build': build
    })


def build_create(request, repo_id, commit_id):
    """Create a new build for a specific commit."""
    repository = get_object_or_404(GitRepository, id=repo_id)
    commit = get_object_or_404(Commit, id=commit_id, repository=repository)
    
    if request.method == 'POST':
        push_to_registry = request.POST.get('push_to_registry') == 'on'
        
        # Create build record
        build = Build.objects.create(
            repository=repository,
            commit=commit,
            branch_name=commit.branch.name if commit.branch else 'unknown',
            status='pending',
            push_to_registry=push_to_registry
        )
        
        # Start build in background thread
        thread = threading.Thread(target=execute_build, args=(build.id,))
        thread.daemon = True
        thread.start()
        
        messages.success(request, f"Build #{build.id} started")
        return redirect('build_detail', build_id=build.id)
    
    return render(request, 'builds/build_create.html', {
        'repository': repository,
        'commit': commit
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

