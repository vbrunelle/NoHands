from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from pathlib import Path
import logging

from .models import GitRepository, Branch, Commit
from .git_utils import clone_or_update_repo, list_branches, list_commits, GitUtilsError

logger = logging.getLogger(__name__)


def repository_list(request):
    """List all Git repositories."""
    repositories = GitRepository.objects.filter(is_active=True)
    return render(request, 'projects/repository_list.html', {
        'repositories': repositories
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

