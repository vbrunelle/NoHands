from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.db.models import Case, When, Value, IntegerField
from http.cookies import SimpleCookie
from pathlib import Path
import logging
import threading
import os
import requests
import re

from .models import Build, DEFAULT_DOCKERFILE_TEMPLATE, get_dockerfile_templates, get_default_template, get_env_templates, get_default_env_template
from projects.models import GitRepository, Commit
from projects.git_utils import (
    checkout_commit, clone_or_update_repo, GitUtilsError,
    list_files_in_commit, get_file_content
)
from .dagger_pipeline import run_build_sync
from .docker_utils import (
    start_container, stop_container, remove_container,
    get_container_logs, get_container_status, load_image_from_tar, 
    exec_command_in_container, DockerError
)

logger = logging.getLogger(__name__)


def _validate_container_port(port_value, default=8080):
    """
    Validate and return a container port value.
    
    Args:
        port_value: The port value to validate (can be string or int)
        default: Default port to return if validation fails
        
    Returns:
        A valid port number between 1 and 65535
    """
    try:
        port = int(port_value) if port_value else default
        if port < 1 or port > 65535:
            return default
        return port
    except (ValueError, TypeError):
        return default


@login_required
def build_list(request):
    """List all builds."""
    # Sort builds: active (running, pending) first, then by repository name alphabetically
    # Using Case to put active statuses first (value 0), others second (value 1)
    builds = Build.objects.select_related('repository', 'commit').annotate(
        is_active=Case(
            When(status__in=['running', 'pending'], then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by('is_active', 'repository__name')
    
    return render(request, 'builds/build_list.html', {
        'builds': builds
    })


@login_required
def container_list(request):
    """List all builds with running or available containers."""
    # Get all builds that have containers (either running or with a successful build that can be started)
    # Sort: running containers first, then by repository name alphabetically
    builds_with_containers = Build.objects.select_related('repository', 'commit').filter(
        status='success'
    ).annotate(
        is_running=Case(
            When(container_status='running', then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by('is_running', 'repository__name')
    
    return render(request, 'builds/container_list.html', {
        'builds': builds_with_containers
    })


@login_required
def build_detail(request, build_id):
    """View build details and logs."""
    build = get_object_or_404(Build, id=build_id)
    
    # Sync container status with actual Docker state
    build.sync_container_status()
    
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
        container_port = _validate_container_port(request.POST.get('container_port', 8080))
        
        # Dockerfile configuration
        dockerfile_source = request.POST.get('dockerfile_source', 'generated')
        dockerfile_content = request.POST.get('dockerfile_content', DEFAULT_DOCKERFILE_TEMPLATE)
        dockerfile_path = request.POST.get('dockerfile_path', 'Dockerfile')
        
        # Environment configuration
        env_content = request.POST.get('env_content', '')
        
        # Validate dockerfile_source
        if dockerfile_source not in ['generated', 'custom', 'repo_file']:
            dockerfile_source = 'generated'
        
        # Create build record
        build = Build.objects.create(
            repository=repository,
            commit=commit,
            branch_name=commit.branch.name if commit.branch else 'unknown',
            status='pending',
            push_to_registry=push_to_registry,
            container_port=container_port,
            dockerfile_source=dockerfile_source,
            dockerfile_content=dockerfile_content,
            dockerfile_path=dockerfile_path,
            env_content=env_content
        )
        
        # Start build in background thread
        # NOTE: For production, use a proper task queue like Celery instead of threading
        thread = threading.Thread(target=execute_build, args=(build.id,))
        thread.daemon = True
        thread.start()
        
        messages.success(request, f"Build #{build.id} started")
        return redirect('build_detail', build_id=build.id)
    
    # Get Dockerfile templates and .env templates
    templates = get_dockerfile_templates()
    default_template = get_default_template()
    env_templates = get_env_templates()
    default_env_template = get_default_env_template()
    
    return render(request, 'builds/build_create.html', {
        'repository': repository,
        'commit': commit,
        'default_dockerfile': default_template,
        'dockerfile_templates': templates,
        'env_templates': env_templates,
        'default_env': default_env_template
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
        
        # Get NoHands URL to configure CSRF trusted origins
        # Build absolute URI to get the scheme, host and port
        nohands_url = request.build_absolute_uri('/')
        # Remove trailing slash and get base URL
        nohands_base = nohands_url.rstrip('/')
        
        # Prepare environment variables for the container
        env_vars = {
            'CSRF_TRUSTED_ORIGINS': nohands_base,
        }
        
        container_name = f"nohands-build-{build.id}"
        container_id, host_port = start_container(
            image_tag=image_tag,
            container_port=build.container_port,
            container_name=container_name,
            env_vars=env_vars,
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


@login_required
def execute_container_command(request, build_id):
    """
    Execute a command in a running container (JSON API).
    POST with 'command' parameter.
    """
    build = get_object_or_404(Build, id=build_id)
    
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'POST method required'
        }, status=405)
    
    if not build.container_id:
        return JsonResponse({
            'success': False,
            'error': 'No container running'
        })
    
    if build.container_status != 'running':
        return JsonResponse({
            'success': False,
            'error': f'Container is not running (status: {build.container_status})'
        })
    
    command = request.POST.get('command', '')
    if not command:
        return JsonResponse({
            'success': False,
            'error': 'Command parameter is required'
        })
    
    try:
        output, exit_code = exec_command_in_container(build.container_id, command)
        
        return JsonResponse({
            'success': True,
            'output': output,
            'exit_code': exit_code,
            'command': command,
            'container_id': build.container_id[:12]
        })
        
    except DockerError as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'output': ''
        })


@login_required
def list_commit_files(request, repo_id, commit_id):
    """
    List files in a specific commit (JSON API).
    Used for the file selector in the build create form.
    """
    repository = get_object_or_404(GitRepository, id=repo_id)
    commit = get_object_or_404(Commit, id=commit_id, repository=repository)
    
    try:
        # Clone/update repository to get files
        repo_cache_path = settings.GIT_CHECKOUT_DIR / 'cache' / repository.name
        clone_or_update_repo(repository.url, repo_cache_path)
        
        # List files in the commit
        files = list_files_in_commit(repo_cache_path, commit.sha)
        
        return JsonResponse({
            'success': True,
            'files': files
        })
        
    except GitUtilsError as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'files': []
        })


@login_required
def get_commit_file_content(request, repo_id, commit_id):
    """
    Get content of a file at a specific commit (JSON API).
    Used for loading Dockerfile content from repo.
    """
    repository = get_object_or_404(GitRepository, id=repo_id)
    commit = get_object_or_404(Commit, id=commit_id, repository=repository)
    
    file_path = request.GET.get('path', '')
    if not file_path:
        return JsonResponse({
            'success': False,
            'error': 'File path is required',
            'content': ''
        })
    
    try:
        # Clone/update repository to get file
        repo_cache_path = settings.GIT_CHECKOUT_DIR / 'cache' / repository.name
        clone_or_update_repo(repository.url, repo_cache_path)
        
        # Get file content
        content = get_file_content(repo_cache_path, commit.sha, file_path)
        
        return JsonResponse({
            'success': True,
            'content': content,
            'path': file_path
        })
        
    except GitUtilsError as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'content': ''
        })


@login_required
def get_dockerfile_template(request, template_name):
    """
    Get a specific Dockerfile template by name (JSON API).
    """
    templates = get_dockerfile_templates()
    
    if template_name in templates:
        return JsonResponse({
            'success': True,
            'name': template_name,
            'content': templates[template_name]
        })
    else:
        return JsonResponse({
            'success': False,
            'error': f"Template '{template_name}' not found",
            'content': ''
        })


@login_required
def get_env_template(request, template_name):
    """
    Get a specific .env template by name (JSON API).
    """
    templates = get_env_templates()
    
    if template_name in templates:
        return JsonResponse({
            'success': True,
            'name': template_name,
            'content': templates[template_name]
        })
    else:
        return JsonResponse({
            'success': False,
            'error': f".env template '{template_name}' not found",
            'content': ''
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
        
        # Determine Dockerfile path and handle custom content
        dockerfile_path = 'Dockerfile'
        
        if build.dockerfile_source == 'generated' or build.dockerfile_source == 'custom':
            # Write custom Dockerfile content to the checkout directory
            custom_dockerfile_path = checkout_path / 'Dockerfile'
            with open(custom_dockerfile_path, 'w') as f:
                f.write(build.dockerfile_content)
            dockerfile_path = 'Dockerfile'
            logger.info(f"Using custom Dockerfile content for build #{build.id}")
        elif build.dockerfile_source == 'repo_file':
            # Use specified file from repo as Dockerfile
            dockerfile_path = build.dockerfile_path
            logger.info(f"Using repository file '{dockerfile_path}' as Dockerfile for build #{build.id}")
        
        # Write .env file if env_content is provided
        if build.env_content:
            env_file_path = checkout_path / '.env'
            with open(env_file_path, 'w') as f:
                f.write(build.env_content)
            logger.info(f"Wrote .env file for build #{build.id}")
        
        # Generate image tag
        image_name = build.repository.name.lower().replace(' ', '-')
        image_tag = f"{build.commit.sha[:8]}"
        
        # Run Dagger build
        result = run_build_sync(
            source_dir=checkout_path,
            dockerfile_path=dockerfile_path,
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


@login_required
@csrf_exempt  # Les POST sont destinés au conteneur, pas à Django NoHands
def proxy_to_container(request, build_id, path=''):
    """
    Proxy requests to a running container.
    This allows accessing the container through Django without port forwarding.
    
    URL pattern: /builds/<build_id>/fwd/<path>
    Example: /builds/9/fwd/ -> http://localhost:8002/
             /builds/9/fwd/admin/ -> http://localhost:8002/admin/
             
    Note: @csrf_exempt is required because POST requests are forwarded to the container,
    which has its own CSRF protection. Django's CSRF check would incorrectly reject
    these requests since the CSRF token comes from the container, not from Django.
    """
    build = get_object_or_404(Build, id=build_id)
    
    # Sync container status with actual Docker state
    build.sync_container_status()
    
    # Check if container is running
    if build.container_status != 'running' or not build.host_port:
        return HttpResponse(
            f"Container is not running. Status: {build.container_status}",
            status=503
        )
    
    # Build target URL
    target_url = f"http://127.0.0.1:{build.host_port}/{path}"
    
    # Copy query parameters
    if request.GET:
        query_string = request.GET.urlencode()
        target_url += f"?{query_string}"
    
    try:
        # Forward the request to the container
        # Exclude NoHands-specific cookies to avoid session conflicts
        headers = {
            key: value for key, value in request.headers.items()
            if key.lower() not in ['host', 'connection', 'cookie', 'referer', 'origin']
        }
        
        # Set proper headers for CSRF validation in the container
        # Django checks that Origin/Referer match the Host
        headers['Host'] = f"127.0.0.1:{build.host_port}"
        if request.method == 'POST':
            # Set Referer to point to the same page on the container
            # This is required for Django CSRF validation
            headers['Referer'] = f"http://127.0.0.1:{build.host_port}/{path}"
            headers['Origin'] = f"http://127.0.0.1:{build.host_port}"
        
        # Extract and forward only non-NoHands cookies to the container
        if 'Cookie' in request.headers:
            nohands_cookies = ['nohands_sessionid', 'nohands_csrftoken']
            cookies = request.headers['Cookie'].split('; ')
            filtered_cookies = [
                cookie for cookie in cookies
                if not any(cookie.startswith(f'{name}=') for name in nohands_cookies)
            ]
            if filtered_cookies:
                headers['Cookie'] = '; '.join(filtered_cookies)
                logger.debug(f"Forwarding cookies to container: {headers['Cookie']}")
            else:
                logger.debug("No cookies to forward to container")
        else:
            logger.debug("No Cookie header in request")
        
        # Make the request to the container
        if request.method == 'GET':
            resp = requests.get(target_url, headers=headers, stream=True, timeout=30)
        elif request.method == 'POST':
            logger.info(f"POST to container: {target_url}")
            logger.info(f"Headers: Host={headers.get('Host')}, Referer={headers.get('Referer')}, Origin={headers.get('Origin')}")
            logger.info(f"Cookies: {headers.get('Cookie', 'None')}")
            resp = requests.post(
                target_url,
                data=request.body,
                headers=headers,
                stream=True,
                timeout=30
            )
        elif request.method == 'PUT':
            resp = requests.put(
                target_url,
                data=request.body,
                headers=headers,
                stream=True,
                timeout=30
            )
        elif request.method == 'DELETE':
            resp = requests.delete(target_url, headers=headers, timeout=30)
        elif request.method == 'PATCH':
            resp = requests.patch(
                target_url,
                data=request.body,
                headers=headers,
                timeout=30
            )
        else:
            return HttpResponse(f"Method {request.method} not supported", status=405)
        
        # Get content type
        content_type = resp.headers.get('content-type', '')
        
        # For HTML responses, rewrite URLs to use proxy path
        if 'text/html' in content_type:
            # Read full content for URL rewriting
            content = resp.content.decode('utf-8', errors='replace')
            
            # Proxy base path
            proxy_base = f"/builds/{build_id}/fwd"
            
            # Rewrite absolute URLs that point to localhost or container
            # Pattern 1: http://localhost:PORT/path -> /builds/ID/fwd/path
            content = re.sub(
                rf'https?://localhost:{build.host_port}(/[^"\'\s]*)',
                rf'{proxy_base}\1',
                content
            )
            content = re.sub(
                rf'https?://127\.0\.0\.1:{build.host_port}(/[^"\'\s]*)',
                rf'{proxy_base}\1',
                content
            )
            
            # Pattern 2: Relative URLs starting with / -> /builds/ID/fwd/
            # This handles href="/path" or src="/static/file.js"
            content = re.sub(
                r'(href|src|action)="(/[^"]*)"',
                rf'\1="{proxy_base}\2"',
                content
            )
            content = re.sub(
                r"(href|src|action)='(/[^']*)'",
                rf"\1='{proxy_base}\2'",
                content
            )
            
            # Rewrite Location header for redirects
            response = HttpResponse(content, status=resp.status_code, content_type=content_type)
        else:
            # For non-HTML content, stream as before
            response = StreamingHttpResponse(
                resp.iter_content(chunk_size=8192),
                status=resp.status_code,
                content_type=content_type
            )
        
        # Copy response headers
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'location', 'set-cookie']
        for key, value in resp.headers.items():
            if key.lower() not in excluded_headers:
                response[key] = value
        
        # Handle Set-Cookie headers - need to adjust path for proxy
        # Parse and rewrite all Set-Cookie headers
        if hasattr(resp, 'cookies') and resp.cookies:
            try:
                cookie_count = len(resp.cookies)
                logger.info(f"Processing {cookie_count} cookies from container")
            except (TypeError, AttributeError):
                logger.info("Processing cookies from container")
            
            for cookie in resp.cookies:
                logger.info(f"Setting cookie: {cookie.name}={cookie.value[:20]}... with Path=/builds/{build_id}/fwd/")
                # Set the cookie with the modified path
                kwargs = {
                    'key': cookie.name,
                    'value': cookie.value,
                    'path': f'/builds/{build_id}/fwd/',
                }
                
                # Add optional attributes only if they exist and are not None
                # Note: We don't set domain to let the browser use the current domain
                if cookie.expires:
                    kwargs['expires'] = cookie.expires
                # Skip domain to avoid cross-domain issues
                # if cookie.domain and cookie.domain != '':
                #     kwargs['domain'] = cookie.domain
                if cookie.secure:
                    kwargs['secure'] = True
                
                # Check for additional attributes that might be in _rest
                if hasattr(cookie, '_rest'):
                    if 'HttpOnly' in cookie._rest:
                        kwargs['httponly'] = True
                    if 'SameSite' in cookie._rest:
                        kwargs['samesite'] = cookie._rest['SameSite']
                
                response.set_cookie(**kwargs)
        else:
            logger.info("No cookies from container response")
        
        # Rewrite Location header for redirects
        if 'location' in resp.headers:
            location = resp.headers['location']
            # Rewrite absolute URLs in redirects
            location = re.sub(
                rf'https?://localhost:{build.host_port}(/.*)',
                rf'{proxy_base}\1',
                location
            )
            location = re.sub(
                rf'https?://127\.0\.0\.1:{build.host_port}(/.*)',
                rf'{proxy_base}\1',
                location
            )
            # Rewrite relative redirects
            if location.startswith('/'):
                location = f'{proxy_base}{location}'
            response['Location'] = location
        
        return response
        
    except requests.exceptions.ConnectionError:
        return HttpResponse(
            f"Could not connect to container on port {build.host_port}",
            status=503
        )
    except requests.exceptions.Timeout:
        return HttpResponse(
            f"Request to container timed out",
            status=504
        )
    except Exception as e:
        logger.error(f"Proxy error for build {build_id}: {e}")
        return HttpResponse(f"Proxy error: {str(e)}", status=500)

