from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from pathlib import Path
import logging
from github import Github
from allauth.socialaccount.models import SocialToken

from .models import GitRepository, Branch, Commit
from .git_utils import clone_or_update_repo, list_branches, list_commits, GitUtilsError

logger = logging.getLogger(__name__)


def repository_list(request):
    """List all Git repositories."""
    repositories = GitRepository.objects.filter(is_active=True)
    return render(request, 'projects/repository_list.html', {
        'repositories': repositories
    })


@login_required
def connect_github_repository(request):
    """Connect a GitHub repository by selecting from user's repositories."""
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
    
    # Get user's GitHub repositories
    github_repos = []
    if request.method == 'GET':
        try:
            g = Github(access_token)
            user = g.get_user()
            github_repos = []
            for repo in user.get_repos():
                github_repos.append({
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
            messages.error(request, f"Failed to fetch GitHub repositories: {e}")
    
    # Connect selected repository
    if request.method == 'POST':
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
            messages.error(request, f"Failed to connect repository: {e}")
    
    return render(request, 'projects/connect_github.html', {
        'github_repos': github_repos
    })


def repository_detail(request, repo_id):
    """View repository details and branches."""
    repository = get_object_or_404(GitRepository, id=repo_id)
    
    # Get or update branches
    if request.method == 'POST' and 'refresh_branches' in request.POST:
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
            
            messages.success(request, f"Refreshed {len(branches_data)} branches")
        except GitUtilsError as e:
            messages.error(request, f"Failed to refresh branches: {e}")
        
        return redirect('repository_detail', repo_id=repo_id)
    
    branches = repository.branches.all()
    recent_commits = repository.commits.all()[:10]
    
    return render(request, 'projects/repository_detail.html', {
        'repository': repository,
        'branches': branches,
        'recent_commits': recent_commits
    })


def branch_commits(request, repo_id, branch_id):
    """List commits for a specific branch."""
    repository = get_object_or_404(GitRepository, id=repo_id)
    branch = get_object_or_404(Branch, id=branch_id, repository=repository)
    
    # Refresh commits if requested
    if request.method == 'POST' and 'refresh_commits' in request.POST:
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
            
            messages.success(request, f"Refreshed {len(commits_data)} commits")
        except GitUtilsError as e:
            messages.error(request, f"Failed to refresh commits: {e}")
        
        return redirect('branch_commits', repo_id=repo_id, branch_id=branch_id)
    
    commits = branch.commits.all()
    
    return render(request, 'projects/branch_commits.html', {
        'repository': repository,
        'branch': branch,
        'commits': commits
    })

