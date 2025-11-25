"""
Git utilities for interacting with repositories.
"""
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

import git
from git import Repo, GitCommandError

logger = logging.getLogger(__name__)


class GitUtilsError(Exception):
    """Base exception for Git utilities."""
    pass


def clone_or_update_repo(repo_url: str, local_path: Path) -> Repo:
    """
    Clone a repository or update it if it already exists.
    
    Args:
        repo_url: Git repository URL or local path
        local_path: Local path to clone/update the repository
        
    Returns:
        Repo: GitPython Repo object
        
    Raises:
        GitUtilsError: If cloning or updating fails
    """
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        if local_path.exists() and (local_path / '.git').exists():
            logger.info(f"Updating existing repository at {local_path}")
            repo = Repo(local_path)
            origin = repo.remotes.origin
            origin.fetch()
            return repo
        else:
            logger.info(f"Cloning repository from {repo_url} to {local_path}")
            if local_path.exists():
                shutil.rmtree(local_path)
            repo = Repo.clone_from(repo_url, local_path)
            return repo
    except GitCommandError as e:
        raise GitUtilsError(f"Failed to clone/update repository: {e}")


def list_branches(repo_path: Path) -> List[Dict[str, str]]:
    """
    List all branches in a repository.
    
    Args:
        repo_path: Path to the Git repository
        
    Returns:
        List of dictionaries with branch information
        
    Raises:
        GitUtilsError: If listing branches fails
    """
    try:
        repo = Repo(repo_path)
        branches = []
        
        for ref in repo.references:
            if isinstance(ref, git.Head):
                branches.append({
                    'name': ref.name,
                    'commit_sha': ref.commit.hexsha,
                    'last_commit_date': datetime.fromtimestamp(ref.commit.committed_date)
                })
        
        return branches
    except Exception as e:
        raise GitUtilsError(f"Failed to list branches: {e}")


def list_commits(repo_path: Path, branch: str, max_count: int = 50) -> List[Dict[str, str]]:
    """
    List commits from a specific branch.
    
    Args:
        repo_path: Path to the Git repository
        branch: Branch name
        max_count: Maximum number of commits to retrieve
        
    Returns:
        List of dictionaries with commit information
        
    Raises:
        GitUtilsError: If listing commits fails
    """
    try:
        repo = Repo(repo_path)
        
        # Get the branch reference
        if branch not in repo.heads:
            raise GitUtilsError(f"Branch '{branch}' not found")
        
        branch_ref = repo.heads[branch]
        commits = []
        
        for commit in repo.iter_commits(branch_ref, max_count=max_count):
            commits.append({
                'sha': commit.hexsha,
                'message': commit.message.strip(),
                'author': commit.author.name,
                'author_email': commit.author.email,
                'committed_at': datetime.fromtimestamp(commit.committed_date)
            })
        
        return commits
    except GitUtilsError:
        raise
    except Exception as e:
        raise GitUtilsError(f"Failed to list commits: {e}")


def checkout_commit(repo_path: Path, sha: str, dest_dir: Path) -> Path:
    """
    Checkout a specific commit to a destination directory.
    
    Args:
        repo_path: Path to the Git repository
        sha: Commit SHA to checkout
        dest_dir: Destination directory for the checkout
        
    Returns:
        Path to the checked out directory
        
    Raises:
        GitUtilsError: If checkout fails
    """
    try:
        repo = Repo(repo_path)
        
        # Verify commit exists
        try:
            commit = repo.commit(sha)
        except Exception:
            raise GitUtilsError(f"Commit '{sha}' not found")
        
        # Create destination directory
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Remove existing content if any (with safety check)
        if dest_dir.exists() and any(dest_dir.iterdir()):
            # Ensure dest_dir is within a safe base path to prevent accidents
            try:
                # Check if it's a subdirectory of expected paths
                if not str(dest_dir.resolve()).startswith('/tmp/') and not str(dest_dir.resolve()).startswith(str(Path.home())):
                    raise GitUtilsError(f"Refusing to clean directory outside safe paths: {dest_dir}")
                
                for item in dest_dir.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
            except Exception as e:
                raise GitUtilsError(f"Failed to clean destination directory: {e}")
        
        # Clone repository to destination
        checkout_repo = Repo.clone_from(repo_path, dest_dir)
        checkout_repo.git.checkout(sha)
        
        logger.info(f"Checked out commit {sha} to {dest_dir}")
        return dest_dir
    except GitUtilsError:
        raise
    except Exception as e:
        raise GitUtilsError(f"Failed to checkout commit: {e}")


def get_repository_info(repo_path: Path) -> Dict[str, str]:
    """
    Get basic information about a repository.
    
    Args:
        repo_path: Path to the Git repository
        
    Returns:
        Dictionary with repository information
        
    Raises:
        GitUtilsError: If getting info fails
    """
    try:
        repo = Repo(repo_path)
        
        return {
            'active_branch': repo.active_branch.name if not repo.head.is_detached else 'detached',
            'head_commit': repo.head.commit.hexsha,
            'remote_url': repo.remotes.origin.url if repo.remotes else 'local',
        }
    except Exception as e:
        raise GitUtilsError(f"Failed to get repository info: {e}")


def list_files_in_commit(repo_path: Path, sha: str, path_filter: str = '') -> List[Dict[str, str]]:
    """
    List all files in a specific commit.
    
    Args:
        repo_path: Path to the Git repository
        sha: Commit SHA
        path_filter: Optional path prefix to filter files
        
    Returns:
        List of dictionaries with file information (path, type)
        
    Raises:
        GitUtilsError: If listing files fails
    """
    try:
        repo = Repo(repo_path)
        
        # Get the commit
        try:
            commit = repo.commit(sha)
        except Exception:
            raise GitUtilsError(f"Commit '{sha}' not found")
        
        files = []
        
        def traverse_tree(tree, prefix=''):
            for item in tree:
                item_path = f"{prefix}{item.name}" if prefix else item.name
                
                if item.type == 'blob':
                    # Apply path filter for files
                    if path_filter and not item_path.startswith(path_filter):
                        continue
                    files.append({
                        'path': item_path,
                        'type': 'file',
                        'size': item.size
                    })
                elif item.type == 'tree':
                    # Always recurse into directories to find matching files
                    # but only add directory to results if it matches filter or no filter
                    if not path_filter or item_path.startswith(path_filter):
                        files.append({
                            'path': item_path,
                            'type': 'directory',
                            'size': 0
                        })
                    traverse_tree(item, f"{item_path}/")
        
        traverse_tree(commit.tree)
        
        # Sort files by path
        files.sort(key=lambda x: x['path'])
        
        return files
    except GitUtilsError:
        raise
    except Exception as e:
        raise GitUtilsError(f"Failed to list files in commit: {e}")


def get_file_content(repo_path: Path, sha: str, file_path: str) -> str:
    """
    Get the content of a file at a specific commit.
    
    Args:
        repo_path: Path to the Git repository
        sha: Commit SHA
        file_path: Path to the file in the repository
        
    Returns:
        File content as string
        
    Raises:
        GitUtilsError: If getting file content fails
    """
    try:
        repo = Repo(repo_path)
        
        # Get the commit
        try:
            commit = repo.commit(sha)
        except Exception:
            raise GitUtilsError(f"Commit '{sha}' not found")
        
        # Get the file blob
        try:
            blob = commit.tree / file_path
        except KeyError:
            raise GitUtilsError(f"File '{file_path}' not found in commit '{sha[:8]}'")
        
        # Return content as string
        return blob.data_stream.read().decode('utf-8')
    except GitUtilsError:
        raise
    except UnicodeDecodeError:
        raise GitUtilsError(f"File '{file_path}' is not a text file")
    except Exception as e:
        raise GitUtilsError(f"Failed to get file content: {e}")
