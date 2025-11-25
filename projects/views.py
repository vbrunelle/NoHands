from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.sites.models import Site
from django.views.decorators.http import require_http_methods
from pathlib import Path
import logging
import os
from github import Github
from allauth.socialaccount.models import SocialToken, SocialApp

from .models import GitRepository, Branch, Commit
from .git_utils import clone_or_update_repo, list_branches, list_commits, GitUtilsError

logger = logging.getLogger(__name__)


def get_env_file_path():
    """Get the path to the .env file in the project root."""
    return settings.BASE_DIR / '.env'


def read_env_values():
    """
    Read GitHub OAuth credentials from .env file if it exists.
    Returns a dict with client_id and client_secret (empty strings if not found).
    """
    env_path = get_env_file_path()
    values = {'client_id': '', 'client_secret': ''}
    
    if env_path.exists():
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key == 'GITHUB_CLIENT_ID':
                            values['client_id'] = value
                        elif key == 'GITHUB_CLIENT_SECRET':
                            values['client_secret'] = value
        except Exception as e:
            logger.warning(f"Failed to read .env file: {e}")
    
    # Also check environment variables
    if not values['client_id']:
        values['client_id'] = os.environ.get('GITHUB_CLIENT_ID', '')
    if not values['client_secret']:
        values['client_secret'] = os.environ.get('GITHUB_CLIENT_SECRET', '')
    
    return values


def write_env_values(client_id, client_secret):
    """
    Write GitHub OAuth credentials to .env file.
    Creates the file if it doesn't exist, updates existing values if it does.
    """
    env_path = get_env_file_path()
    existing_lines = []
    client_id_found = False
    client_secret_found = False
    
    # Read existing content
    if env_path.exists():
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith('GITHUB_CLIENT_ID='):
                        existing_lines.append(f'GITHUB_CLIENT_ID="{client_id}"\n')
                        client_id_found = True
                    elif stripped.startswith('GITHUB_CLIENT_SECRET='):
                        existing_lines.append(f'GITHUB_CLIENT_SECRET="{client_secret}"\n')
                        client_secret_found = True
                    else:
                        existing_lines.append(line)
        except Exception as e:
            logger.warning(f"Failed to read .env file: {e}")
    
    # Add missing values
    if not client_id_found:
        existing_lines.append(f'GITHUB_CLIENT_ID="{client_id}"\n')
    if not client_secret_found:
        existing_lines.append(f'GITHUB_CLIENT_SECRET="{client_secret}"\n')
    
    # Write file with restrictive permissions
    try:
        with open(env_path, 'w') as f:
            f.writelines(existing_lines)
        # Set restrictive permissions (owner read/write only)
        os.chmod(env_path, 0o600)
        return True
    except Exception as e:
        logger.error(f"Failed to write .env file: {e}")
        return False


def setup_github_oauth(client_id, client_secret, site_domain='localhost:8000'):
    """
    Configure GitHub OAuth in the database.
    Returns True on success, False on failure.
    """
    try:
        # Update or create site
        site, _ = Site.objects.get_or_create(pk=1)
        site.domain = site_domain
        site.name = 'NoHands'
        site.save()

        # Create or update GitHub social app
        social_app, created = SocialApp.objects.get_or_create(
            provider='github',
            defaults={
                'name': 'GitHub',
                'client_id': client_id,
                'secret': client_secret,
            }
        )

        if not created:
            social_app.client_id = client_id
            social_app.secret = client_secret
            social_app.save()

        # Associate with site
        if site not in social_app.sites.all():
            social_app.sites.add(site)

        return True
    except Exception as e:
        logger.error(f"Failed to setup GitHub OAuth: {e}")
        return False


def initial_setup(request):
    """
    Initial setup page for first-time server access.
    
    This page is displayed when no users exist in the system.
    The user must connect via GitHub OAuth to create the first admin account.
    Allows administrators to configure OAuth credentials directly from this page.
    """
    # Check if users already exist
    has_users = User.objects.exists()
    
    if has_users:
        # If users exist, redirect to the main page
        return redirect('repository_list')
    
    # Check if OAuth is already configured
    oauth_configured = SocialApp.objects.filter(provider='github').exists()
    
    # Read default values from .env file or environment
    env_values = read_env_values()
    
    error_message = None
    success_message = None
    
    if request.method == 'POST':
        # Handle form submission
        client_id = request.POST.get('client_id', '').strip()
        client_secret = request.POST.get('client_secret', '').strip()
        save_to_env = request.POST.get('save_to_env') == 'on'
        
        if not client_id or not client_secret:
            error_message = "Both Client ID and Client Secret are required."
        else:
            # Save to database
            db_success = setup_github_oauth(client_id, client_secret)
            
            # Save to .env file if requested
            env_success = True
            if save_to_env:
                env_success = write_env_values(client_id, client_secret)
            
            if db_success:
                success_message = "GitHub OAuth configured successfully! You can now connect with GitHub."
                oauth_configured = True
                # Update env_values for display
                env_values['client_id'] = client_id
                env_values['client_secret'] = client_secret
            else:
                error_message = "Failed to save OAuth configuration to database. Please try again."
            
            if save_to_env and not env_success:
                if success_message:
                    success_message += " (Note: Could not save to .env file)"
                else:
                    error_message = "Failed to save to .env file."
    
    return render(request, 'projects/initial_setup.html', {
        'oauth_configured': oauth_configured,
        'env_values': env_values,
        'error_message': error_message,
        'success_message': success_message,
    })


@login_required
def repository_list(request):
    """List all Git repositories."""
    repositories = GitRepository.objects.filter(is_active=True)
    
    # Try to fetch available GitHub repos if user has a token
    available_github_repos = []
    has_github_token = False
    
    try:
        social_token = SocialToken.objects.get(
            account__user=request.user,
            account__provider='github'
        )
        has_github_token = True
        access_token = social_token.token
        
        # Fetch GitHub repositories
        try:
            g = Github(access_token)
            user = g.get_user()
            # Limit to first 100 repos for performance
            repos_list = list(user.get_repos()[:100])
            
            # Get list of already connected repo IDs
            connected_repo_ids = set(
                GitRepository.objects.filter(github_id__isnull=False)
                .values_list('github_id', flat=True)
            )
            
            # Only show repos that are not yet connected
            for repo in repos_list:
                if str(repo.id) not in connected_repo_ids:
                    available_github_repos.append({
                        'id': repo.id,
                        'name': repo.name,
                        'full_name': repo.full_name,
                        'description': repo.description or '',
                        'clone_url': repo.clone_url,
                        'default_branch': repo.default_branch,
                        'private': repo.private,
                    })
        except Exception as e:
            logger.error(f"Failed to fetch GitHub repositories: {e}")
            messages.warning(request, "Could not load available GitHub repositories.")
    except SocialToken.DoesNotExist:
        pass  # User doesn't have GitHub token
    
    return render(request, 'projects/repository_list.html', {
        'repositories': repositories,
        'available_github_repos': available_github_repos,
        'has_github_token': has_github_token,
    })


@login_required
def connect_github_repository(request):
    """Connect a GitHub repository by selecting from user's repositories."""
    # Only handle POST requests (connection requests)
    if request.method != 'POST':
        # Redirect to repository list for GET requests
        return redirect('repository_list')
    
    # Get GitHub access token
    try:
        social_token = SocialToken.objects.get(
            account__user=request.user,
            account__provider='github'
        )
        access_token = social_token.token
    except SocialToken.DoesNotExist:
        messages.error(request, "Please connect your GitHub account first.")
        return redirect('repository_list')
    
    # Connect selected repository
    repo_id = request.POST.get('repo_id')
    repo_name = request.POST.get('repo_name')
    repo_url = request.POST.get('repo_url')
    repo_description = request.POST.get('repo_description')
    default_branch = request.POST.get('default_branch')
    
    try:
        # Check if repository already exists
        if GitRepository.objects.filter(name=repo_name).exists():
            messages.warning(request, f"Repository '{repo_name}' is already connected.")
            return redirect('repository_list')
        
        # Create new repository
        repository = GitRepository.objects.create(
            name=repo_name,
            url=repo_url,
            description=repo_description,
            default_branch=default_branch,
            user=request.user,
            github_id=repo_id,
            is_active=True
        )
        
        messages.success(request, f"Successfully connected repository '{repo_name}'")
        return redirect('repository_detail', repo_id=repository.id)
        
    except Exception as e:
        logger.error(f"Failed to connect repository: {e}")
        messages.error(request, "Failed to connect repository. Please try again.")
        return redirect('repository_list')


def refresh_repository_branches(repository):
    """
    Helper function to refresh branches for a repository.
    Returns (success: bool, message: str, branch_count: int)
    """
    try:
        # Clone or update the repository
        repo_cache_path = settings.GIT_CHECKOUT_DIR / 'cache' / repository.name
        clone_or_update_repo(repository.url, repo_cache_path)
        
        # List branches
        branches_data = list_branches(repo_cache_path)
        
        # Update database
        for branch_data in branches_data:
            Branch.objects.update_or_create(
                repository=repository,
                name=branch_data['name'],
                defaults={'commit_sha': branch_data['commit_sha']}
            )
        
        return True, f"Refreshed {len(branches_data)} branches", len(branches_data)
    except GitUtilsError as e:
        logger.error(f"Failed to refresh branches for {repository.name}: {e}")
        return False, str(e), 0


@login_required
def repository_detail(request, repo_id):
    """View repository details and branches."""
    repository = get_object_or_404(GitRepository, id=repo_id)
    
    # Automatically refresh branches on page load
    success, message, count = refresh_repository_branches(repository)
    if success and count > 0:
        messages.success(request, message)
    elif not success:
        messages.error(request, f"Failed to refresh branches: {message}")
    
    branches = repository.branches.all()
    recent_commits = repository.commits.all()[:10]
    
    return render(request, 'projects/repository_detail.html', {
        'repository': repository,
        'branches': branches,
        'recent_commits': recent_commits
    })


def refresh_branch_commits(repository, branch):
    """
    Helper function to refresh commits for a branch.
    Returns (success: bool, message: str, commit_count: int)
    """
    try:
        repo_cache_path = settings.GIT_CHECKOUT_DIR / 'cache' / repository.name
        commits_data = list_commits(repo_cache_path, branch.name)
        
        # Update database
        for commit_data in commits_data:
            Commit.objects.update_or_create(
                repository=repository,
                sha=commit_data['sha'],
                defaults={
                    'branch': branch,
                    'message': commit_data['message'],
                    'author': commit_data['author'],
                    'author_email': commit_data['author_email'],
                    'committed_at': commit_data['committed_at']
                }
            )
        
        return True, f"Refreshed {len(commits_data)} commits", len(commits_data)
    except GitUtilsError as e:
        logger.error(f"Failed to refresh commits for {branch.name}: {e}")
        return False, str(e), 0


@login_required
def branch_commits(request, repo_id, branch_id):
    """List commits for a specific branch."""
    repository = get_object_or_404(GitRepository, id=repo_id)
    branch = get_object_or_404(Branch, id=branch_id, repository=repository)
    
    # Automatically refresh commits on page load
    success, message, count = refresh_branch_commits(repository, branch)
    if success and count > 0:
        messages.success(request, message)
    elif not success:
        messages.error(request, f"Failed to refresh commits: {message}")
    
    commits = branch.commits.all()
    
    return render(request, 'projects/branch_commits.html', {
        'repository': repository,
        'branch': branch,
        'commits': commits
    })

