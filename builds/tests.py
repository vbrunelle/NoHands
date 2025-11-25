from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from .models import Build
from projects.models import GitRepository, Branch, Commit
from .dagger_pipeline import BuildResult


class BuildModelTest(TestCase):
    """Tests for Build model."""
    
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
            sha="abc123def456",
            message="Test commit",
            author="Test Author",
            author_email="test@example.com",
            committed_at=timezone.now()
        )
        self.build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="pending"
        )
    
    def test_build_creation(self):
        """Test that build is created correctly."""
        self.assertEqual(self.build.repository, self.repo)
        self.assertEqual(self.build.commit, self.commit)
        self.assertEqual(self.build.branch_name, "main")
        self.assertEqual(self.build.status, "pending")
    
    def test_build_str(self):
        """Test string representation."""
        build_str = str(self.build)
        self.assertIn("test-repo", build_str)
        self.assertIn("abc123de", build_str)
        self.assertIn("pending", build_str)
    
    def test_build_status_choices(self):
        """Test build status choices."""
        self.build.status = 'running'
        self.build.save()
        self.assertEqual(self.build.status, 'running')
        
        self.build.status = 'success'
        self.build.save()
        self.assertEqual(self.build.status, 'success')
        
        self.build.status = 'failed'
        self.build.save()
        self.assertEqual(self.build.status, 'failed')
    
    def test_build_duration_property(self):
        """Test duration property calculation."""
        # No duration yet
        self.assertEqual(self.build.duration, "N/A")
        
        # With duration
        self.build.started_at = timezone.now()
        self.build.completed_at = self.build.started_at + timezone.timedelta(minutes=5, seconds=30)
        self.build.save()
        self.assertEqual(self.build.duration, "5m 30s")


class BuildListViewTest(TestCase):
    """Tests for build list view."""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('build_list')
        
        # Create and login a test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.login(username='testuser', password='testpass')
        
        # Create test data
        self.repo = GitRepository.objects.create(
            name="test-repo",
            url="https://github.com/test/repo.git"
        )
        self.commit = Commit.objects.create(
            repository=self.repo,
            sha="abc123",
            message="Test",
            author="Test",
            author_email="test@example.com",
            committed_at=timezone.now()
        )
    
    def test_view_url_accessible(self):
        """Test that the view is accessible."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
    
    def test_view_uses_correct_template(self):
        """Test that correct template is used."""
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'builds/build_list.html')
    
    def test_view_shows_builds(self):
        """Test that builds are displayed."""
        build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success"
        )
        response = self.client.get(self.url)
        self.assertContains(response, "test-repo")
        self.assertContains(response, "success")


class BuildDetailViewTest(TestCase):
    """Tests for build detail view."""
    
    def setUp(self):
        self.client = Client()
        
        # Create and login a test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.login(username='testuser', password='testpass')
        
        # Create test data
        self.repo = GitRepository.objects.create(
            name="test-repo",
            url="https://github.com/test/repo.git"
        )
        self.commit = Commit.objects.create(
            repository=self.repo,
            sha="abc123def456",
            message="Test commit",
            author="Test Author",
            author_email="test@example.com",
            committed_at=timezone.now()
        )
        self.build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success",
            logs="Build successful",
            image_tag="test-repo:abc123de"
        )
        self.url = reverse('build_detail', args=[self.build.id])
    
    def test_view_url_accessible(self):
        """Test that the view is accessible."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
    
    def test_view_uses_correct_template(self):
        """Test that correct template is used."""
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'builds/build_detail.html')
    
    def test_view_shows_build_info(self):
        """Test that build info is displayed."""
        response = self.client.get(self.url)
        self.assertContains(response, "test-repo")
        self.assertContains(response, "abc123de")
        self.assertContains(response, "success")
        self.assertContains(response, "Build successful")
        self.assertContains(response, "test-repo:abc123de")


class BuildCreateViewTest(TestCase):
    """Tests for build create view."""
    
    def setUp(self):
        self.client = Client()
        
        # Create and login a test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.login(username='testuser', password='testpass')
        
        # Create test data
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
            sha="abc123def456",
            message="Test commit",
            author="Test Author",
            author_email="test@example.com",
            committed_at=timezone.now()
        )
        self.url = reverse('build_create', args=[self.repo.id, self.commit.id])
    
    def test_view_url_accessible_get(self):
        """Test that the view is accessible via GET."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
    
    def test_view_uses_correct_template(self):
        """Test that correct template is used."""
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'builds/build_create.html')
    
    @patch('builds.views.threading.Thread')
    def test_create_build_post(self, mock_thread):
        """Test creating a build via POST."""
        response = self.client.post(self.url, {
            'push_to_registry': 'on'
        })
        
        # Should redirect to build detail
        self.assertEqual(response.status_code, 302)
        
        # Build should be created
        build = Build.objects.filter(repository=self.repo, commit=self.commit).first()
        self.assertIsNotNone(build)
        self.assertEqual(build.status, 'pending')
        self.assertTrue(build.push_to_registry)
        
        # Thread should be started
        mock_thread.assert_called_once()


class BuildResultTest(TestCase):
    """Tests for BuildResult class."""
    
    def test_build_result_creation(self):
        """Test creating a BuildResult."""
        result = BuildResult(
            status='success',
            image_tag='test:abc123',
            logs='Build completed',
            duration=120.5
        )
        
        self.assertEqual(result.status, 'success')
        self.assertEqual(result.image_tag, 'test:abc123')
        self.assertEqual(result.logs, 'Build completed')
        self.assertEqual(result.duration, 120.5)
    
    def test_build_result_to_dict(self):
        """Test converting BuildResult to dict."""
        result = BuildResult(
            status='success',
            image_tag='test:abc123',
            logs='Build completed',
            error_message='',
            duration=120.5
        )
        
        result_dict = result.to_dict()
        
        self.assertEqual(result_dict['status'], 'success')
        self.assertEqual(result_dict['image_tag'], 'test:abc123')
        self.assertEqual(result_dict['logs'], 'Build completed')
        self.assertEqual(result_dict['duration'], 120.5)


class DaggerPipelineTest(TestCase):
    """Tests for Dagger pipeline functions."""
    
    @patch('builds.dagger_pipeline.asyncio.run')
    def test_run_build_sync(self, mock_asyncio_run):
        """Test synchronous build wrapper."""
        from builds.dagger_pipeline import run_build_sync, BuildResult
        
        # Mock the async function result
        mock_result = BuildResult(
            status='success',
            image_tag='test:abc123',
            logs='Build completed',
            duration=60.0
        )
        mock_asyncio_run.return_value = mock_result
        
        result = run_build_sync(
            source_dir=Path('/tmp/test'),
            dockerfile_path='Dockerfile',
            image_name='test',
            image_tag='abc123'
        )
        
        self.assertEqual(result.status, 'success')
        self.assertEqual(result.image_tag, 'test:abc123')
        mock_asyncio_run.assert_called_once()


class URLRoutingTest(TestCase):
    """Tests for URL routing."""
    
    def test_build_list_url_resolves(self):
        """Test build list URL resolves correctly."""
        url = reverse('build_list')
        self.assertEqual(url, '/builds/')
    
    def test_build_detail_url_resolves(self):
        """Test build detail URL resolves correctly."""
        url = reverse('build_detail', args=[1])
        self.assertEqual(url, '/builds/1/')
    
    def test_build_create_url_resolves(self):
        """Test build create URL resolves correctly."""
        url = reverse('build_create', args=[1, 1])
        self.assertEqual(url, '/builds/create/1/1/')
