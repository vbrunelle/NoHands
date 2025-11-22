from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from .models import GitRepository, Branch, Commit
from .git_utils import GitUtilsError


class GitRepositoryModelTest(TestCase):
    """Tests for GitRepository model."""
    
    def setUp(self):
        self.repo = GitRepository.objects.create(
            name="test-repo",
            url="https://github.com/test/repo.git",
            description="Test repository",
            default_branch="main",
            dockerfile_path="Dockerfile",
            is_active=True
        )
    
    def test_repository_creation(self):
        """Test that repository is created correctly."""
        self.assertEqual(self.repo.name, "test-repo")
        self.assertEqual(self.repo.url, "https://github.com/test/repo.git")
        self.assertEqual(self.repo.default_branch, "main")
        self.assertTrue(self.repo.is_active)
    
    def test_repository_with_user(self):
        """Test repository creation with user association."""
        user = User.objects.create_user(username='testuser', password='testpass')
        repo = GitRepository.objects.create(
            name="user-repo",
            url="https://github.com/user/repo.git",
            user=user,
            github_id="12345"
        )
        self.assertEqual(repo.user, user)
        self.assertEqual(repo.github_id, "12345")
    
    def test_repository_str(self):
        """Test string representation."""
        self.assertEqual(str(self.repo), "test-repo")
    
    def test_repository_ordering(self):
        """Test repositories are ordered by creation date."""
        repo2 = GitRepository.objects.create(
            name="test-repo-2",
            url="https://github.com/test/repo2.git"
        )
        repos = list(GitRepository.objects.all())
        self.assertEqual(repos[0], repo2)  # Most recent first


class BranchModelTest(TestCase):
    """Tests for Branch model."""
    
    def setUp(self):
        self.repo = GitRepository.objects.create(
            name="test-repo",
            url="https://github.com/test/repo.git"
        )
        self.branch = Branch.objects.create(
            repository=self.repo,
            name="main",
            commit_sha="abc123def456"
        )
    
    def test_branch_creation(self):
        """Test that branch is created correctly."""
        self.assertEqual(self.branch.name, "main")
        self.assertEqual(self.branch.commit_sha, "abc123def456")
        self.assertEqual(self.branch.repository, self.repo)
    
    def test_branch_str(self):
        """Test string representation."""
        self.assertEqual(str(self.branch), "test-repo/main")
    
    def test_branch_unique_constraint(self):
        """Test that repository+name must be unique."""
        with self.assertRaises(Exception):
            Branch.objects.create(
                repository=self.repo,
                name="main",
                commit_sha="xyz789"
            )


class CommitModelTest(TestCase):
    """Tests for Commit model."""
    
    def setUp(self):
        self.repo = GitRepository.objects.create(
            name="test-repo",
            url="https://github.com/test/repo.git"
        )
        self.branch = Branch.objects.create(
            repository=self.repo,
            name="main",
            commit_sha="abc123"
        )
        self.commit = Commit.objects.create(
            repository=self.repo,
            branch=self.branch,
            sha="abc123def456789",
            message="Initial commit",
            author="Test Author",
            author_email="test@example.com",
            committed_at=timezone.now()
        )
    
    def test_commit_creation(self):
        """Test that commit is created correctly."""
        self.assertEqual(self.commit.sha, "abc123def456789")
        self.assertEqual(self.commit.message, "Initial commit")
        self.assertEqual(self.commit.author, "Test Author")
        self.assertEqual(self.commit.author_email, "test@example.com")
    
    def test_commit_str(self):
        """Test string representation."""
        self.assertIn("abc123de", str(self.commit))
        self.assertIn("Initial commit", str(self.commit))


class RepositoryListViewTest(TestCase):
    """Tests for repository list view."""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('repository_list')
    
    def test_view_url_accessible(self):
        """Test that the view is accessible."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
    
    def test_view_uses_correct_template(self):
        """Test that correct template is used."""
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'projects/repository_list.html')
    
    def test_view_shows_repositories(self):
        """Test that repositories are displayed."""
        GitRepository.objects.create(
            name="test-repo",
            url="https://github.com/test/repo.git",
            is_active=True
        )
        response = self.client.get(self.url)
        self.assertContains(response, "test-repo")


class RepositoryDetailViewTest(TestCase):
    """Tests for repository detail view."""
    
    def setUp(self):
        self.client = Client()
        self.repo = GitRepository.objects.create(
            name="test-repo",
            url="https://github.com/test/repo.git",
            is_active=True
        )
        self.url = reverse('repository_detail', args=[self.repo.id])
    
    def test_view_url_accessible(self):
        """Test that the view is accessible."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
    
    def test_view_uses_correct_template(self):
        """Test that correct template is used."""
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'projects/repository_detail.html')
    
    def test_view_shows_repository_info(self):
        """Test that repository info is displayed."""
        response = self.client.get(self.url)
        self.assertContains(response, "test-repo")
        self.assertContains(response, self.repo.url)
    
    @patch('projects.views.clone_or_update_repo')
    @patch('projects.views.list_branches')
    def test_refresh_branches(self, mock_list_branches, mock_clone):
        """Test refreshing branches."""
        mock_list_branches.return_value = [
            {'name': 'main', 'commit_sha': 'abc123', 'last_commit_date': timezone.now()}
        ]
        
        response = self.client.post(self.url, {'refresh_branches': 'true'})
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertTrue(Branch.objects.filter(repository=self.repo, name='main').exists())


class BranchCommitsViewTest(TestCase):
    """Tests for branch commits view."""
    
    def setUp(self):
        self.client = Client()
        self.repo = GitRepository.objects.create(
            name="test-repo",
            url="https://github.com/test/repo.git",
            is_active=True
        )
        self.branch = Branch.objects.create(
            repository=self.repo,
            name="main",
            commit_sha="abc123"
        )
        self.url = reverse('branch_commits', args=[self.repo.id, self.branch.id])
    
    def test_view_url_accessible(self):
        """Test that the view is accessible."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
    
    def test_view_uses_correct_template(self):
        """Test that correct template is used."""
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'projects/branch_commits.html')
    
    def test_view_shows_commits(self):
        """Test that commits are displayed."""
        commit = Commit.objects.create(
            repository=self.repo,
            branch=self.branch,
            sha="abc123def456",
            message="Test commit",
            author="Test Author",
            author_email="test@example.com",
            committed_at=timezone.now()
        )
        response = self.client.get(self.url)
        self.assertContains(response, "abc123de")


class GitUtilsTest(TestCase):
    """Tests for Git utilities."""
    
    @patch('projects.git_utils.Repo')
    def test_clone_or_update_repo_clone(self, mock_repo_class):
        """Test cloning a new repository."""
        from projects.git_utils import clone_or_update_repo
        
        mock_repo = MagicMock()
        mock_repo_class.clone_from.return_value = mock_repo
        
        result = clone_or_update_repo(
            "https://github.com/test/repo.git",
            Path("/tmp/test-repo")
        )
        
        self.assertEqual(result, mock_repo)
        mock_repo_class.clone_from.assert_called_once()
    
    @patch('projects.git_utils.Repo')
    def test_list_branches(self, mock_repo_class):
        """Test listing branches."""
        from projects.git_utils import list_branches
        import git
        
        # Create mock branch
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_commit.committed_date = 1234567890
        
        mock_branch = MagicMock(spec=git.Head)
        mock_branch.name = "main"
        mock_branch.commit = mock_commit
        
        mock_repo = MagicMock()
        mock_repo.references = [mock_branch]
        mock_repo_class.return_value = mock_repo
        
        branches = list_branches(Path("/tmp/test-repo"))
        
        self.assertEqual(len(branches), 1)
        self.assertEqual(branches[0]['name'], 'main')
        self.assertEqual(branches[0]['commit_sha'], 'abc123')
    
    def test_git_utils_error(self):
        """Test GitUtilsError exception."""
        from projects.git_utils import GitUtilsError
        
        with self.assertRaises(GitUtilsError):
            raise GitUtilsError("Test error")


class ConnectGitHubRepositoryViewTest(TestCase):
    """Tests for connecting GitHub repositories."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.url = reverse('connect_github_repository')
    
    def test_view_requires_authentication(self):
        """Test that the view requires login."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn('/accounts/login/', response.url)
    
    @patch('projects.views.SocialToken.objects.get')
    def test_view_redirects_without_github_token(self, mock_social_token):
        """Test redirect when user has no GitHub token."""
        from allauth.socialaccount.models import SocialToken
        mock_social_token.side_effect = SocialToken.DoesNotExist
        
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('repository_list'))
    
    @patch('projects.views.Github')
    @patch('projects.views.SocialToken.objects.get')
    def test_view_displays_github_repos(self, mock_social_token, mock_github_class):
        """Test that GitHub repositories are displayed."""
        # Mock social token
        mock_token = MagicMock()
        mock_token.token = 'fake_token'
        mock_social_token.return_value = mock_token
        
        # Mock GitHub API
        mock_repo = MagicMock()
        mock_repo.id = 123
        mock_repo.name = 'test-repo'
        mock_repo.full_name = 'testuser/test-repo'
        mock_repo.description = 'Test repository'
        mock_repo.clone_url = 'https://github.com/testuser/test-repo.git'
        mock_repo.default_branch = 'main'
        mock_repo.private = False
        
        mock_user = MagicMock()
        mock_user.get_repos.return_value = [mock_repo]
        
        mock_github = MagicMock()
        mock_github.get_user.return_value = mock_user
        mock_github_class.return_value = mock_github
        
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test-repo')
        self.assertContains(response, 'testuser/test-repo')
    
    @patch('projects.views.SocialToken.objects.get')
    def test_connect_repository(self, mock_social_token):
        """Test connecting a repository."""
        # Mock social token
        mock_token = MagicMock()
        mock_token.token = 'fake_token'
        mock_social_token.return_value = mock_token
        
        self.client.login(username='testuser', password='testpass')
        
        response = self.client.post(self.url, {
            'repo_id': '123',
            'repo_name': 'testuser/test-repo',
            'repo_url': 'https://github.com/testuser/test-repo.git',
            'repo_description': 'Test repository',
            'default_branch': 'main'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Check that repository was created
        repo = GitRepository.objects.get(name='testuser/test-repo')
        self.assertEqual(repo.user, self.user)
        self.assertEqual(repo.github_id, '123')
        self.assertEqual(repo.url, 'https://github.com/testuser/test-repo.git')
    
    @patch('projects.views.SocialToken.objects.get')
    def test_connect_duplicate_repository(self, mock_social_token):
        """Test connecting a repository that already exists."""
        # Mock social token
        mock_token = MagicMock()
        mock_token.token = 'fake_token'
        mock_social_token.return_value = mock_token
        
        # Create existing repository
        GitRepository.objects.create(
            name='testuser/test-repo',
            url='https://github.com/testuser/test-repo.git',
            user=self.user
        )
        
        self.client.login(username='testuser', password='testpass')
        
        response = self.client.post(self.url, {
            'repo_id': '123',
            'repo_name': 'testuser/test-repo',
            'repo_url': 'https://github.com/testuser/test-repo.git',
            'repo_description': 'Test repository',
            'default_branch': 'main'
        })
        
        self.assertEqual(response.status_code, 302)
        # Should only have one repository
        self.assertEqual(GitRepository.objects.filter(name='testuser/test-repo').count(), 1)
