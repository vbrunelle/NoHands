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
    
    def test_container_list_url_resolves(self):
        """Test container list URL resolves correctly."""
        url = reverse('container_list')
        self.assertEqual(url, '/builds/containers/')
    
    def test_build_detail_url_resolves(self):
        """Test build detail URL resolves correctly."""
        url = reverse('build_detail', args=[1])
        self.assertEqual(url, '/builds/1/')
    
    def test_build_create_url_resolves(self):
        """Test build create URL resolves correctly."""
        url = reverse('build_create', args=[1, 1])
        self.assertEqual(url, '/builds/create/1/1/')
    
    def test_start_container_url_resolves(self):
        """Test start container URL resolves correctly."""
        url = reverse('start_build_container', args=[1])
        self.assertEqual(url, '/builds/1/start-container/')
    
    def test_stop_container_url_resolves(self):
        """Test stop container URL resolves correctly."""
        url = reverse('stop_build_container', args=[1])
        self.assertEqual(url, '/builds/1/stop-container/')
    
    def test_container_logs_url_resolves(self):
        """Test container logs URL resolves correctly."""
        url = reverse('container_logs', args=[1])
        self.assertEqual(url, '/builds/1/container-logs/')


class ContainerListViewTest(TestCase):
    """Tests for container list view."""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('container_list')
        
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
        self.assertTemplateUsed(response, 'builds/container_list.html')
    
    def test_view_shows_successful_builds(self):
        """Test that only successful builds are displayed."""
        # Create a successful build
        success_build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success",
            image_tag="test:abc123"
        )
        # Create a failed build (should not appear)
        Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="failed"
        )
        response = self.client.get(self.url)
        self.assertContains(response, "test-repo")
        self.assertContains(response, "test:abc123")
    
    def test_view_shows_running_container_status(self):
        """Test that running container status is displayed."""
        Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success",
            container_status="running",
            host_port=8080,
            container_id="abc123container"
        )
        response = self.client.get(self.url)
        self.assertContains(response, "Running")
        self.assertContains(response, "8080")
    
    def test_view_shows_stopped_container_status(self):
        """Test that stopped container status is displayed."""
        Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success",
            container_status="stopped"
        )
        response = self.client.get(self.url)
        self.assertContains(response, "Stopped")
    
    def test_view_empty_state(self):
        """Test that empty state is displayed when no builds."""
        response = self.client.get(self.url)
        self.assertContains(response, "No containers available")
    
    def test_view_requires_login(self):
        """Test that the view requires authentication."""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)  # Redirects to login


class BuildModelExtendedTest(TestCase):
    """Extended tests for Build model with container fields."""
    
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
    
    def test_container_fields_default(self):
        """Test container fields have correct defaults."""
        build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="pending"
        )
        self.assertEqual(build.container_port, 8080)
        self.assertIsNone(build.host_port)
        self.assertEqual(build.container_id, '')
        self.assertEqual(build.container_status, 'none')
    
    def test_container_url_property_running(self):
        """Test container_url property when container is running."""
        build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success",
            container_status="running",
            host_port=8080
        )
        self.assertEqual(build.container_url, "http://localhost:8080")
    
    def test_container_url_property_not_running(self):
        """Test container_url property when container is not running."""
        build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success",
            container_status="stopped"
        )
        self.assertEqual(build.container_url, "")


class ContainerViewsTest(TestCase):
    """Tests for container control views."""
    
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
        self.build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success",
            image_tag="test-repo:abc123de"
        )
    
    def test_start_container_get_redirects(self):
        """Test that GET request redirects to build detail."""
        url = reverse('start_build_container', args=[self.build.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
    
    def test_start_container_failed_build(self):
        """Test that container cannot be started for failed build."""
        self.build.status = 'failed'
        self.build.save()
        
        url = reverse('start_build_container', args=[self.build.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        # Verify container status unchanged
        self.build.refresh_from_db()
        self.assertEqual(self.build.container_status, 'none')
    
    def test_stop_container_get_redirects(self):
        """Test that GET request redirects to build detail."""
        url = reverse('stop_build_container', args=[self.build.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
    
    def test_stop_container_no_container(self):
        """Test stopping when no container is running."""
        url = reverse('stop_build_container', args=[self.build.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
    
    def test_container_logs_no_container(self):
        """Test getting logs when no container is running."""
        url = reverse('container_logs', args=[self.build.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'No container running')


class DockerUtilsTest(TestCase):
    """Tests for Docker utilities."""
    
    def test_find_available_port(self):
        """Test finding an available port."""
        from builds.docker_utils import find_available_port
        
        port = find_available_port(start_port=49000)
        self.assertIsInstance(port, int)
        self.assertGreaterEqual(port, 49000)
        self.assertLess(port, 49100)
    
    @patch('builds.docker_utils.subprocess.run')
    def test_get_container_logs(self, mock_run):
        """Test getting container logs."""
        from builds.docker_utils import get_container_logs
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Log line 1\nLog line 2",
            stderr=""
        )
        
        logs = get_container_logs("abc123", tail=100)
        self.assertIn("Log line 1", logs)
        mock_run.assert_called_once()
    
    @patch('builds.docker_utils.subprocess.run')
    def test_get_container_status(self, mock_run):
        """Test getting container status."""
        from builds.docker_utils import get_container_status
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="running\n"
        )
        
        status = get_container_status("abc123")
        self.assertEqual(status, "running")
    
    @patch('builds.docker_utils.subprocess.run')
    def test_start_container_success(self, mock_run):
        """Test starting a container."""
        from builds.docker_utils import start_container
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123def456\n"
        )
        
        container_id, host_port = start_container(
            image_tag="test:latest",
            container_port=8080,
            host_port=9000
        )
        
        self.assertEqual(container_id, "abc123def456")
        self.assertEqual(host_port, 9000)
    
    @patch('builds.docker_utils.subprocess.run')
    def test_stop_container_success(self, mock_run):
        """Test stopping a container."""
        from builds.docker_utils import stop_container
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123\n"
        )
        
        result = stop_container("abc123")
        self.assertTrue(result)


class DockerfileConfigurationTest(TestCase):
    """Tests for Dockerfile configuration functionality."""
    
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
    
    def test_build_dockerfile_fields_default(self):
        """Test that Dockerfile fields have correct defaults."""
        build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="pending"
        )
        self.assertEqual(build.dockerfile_source, 'generated')
        self.assertIn('FROM python', build.dockerfile_content)
        self.assertEqual(build.dockerfile_path, 'Dockerfile')
    
    def test_build_with_custom_dockerfile_content(self):
        """Test creating a build with custom Dockerfile content."""
        custom_dockerfile = "FROM node:18\nWORKDIR /app\nCOPY . .\nCMD ['npm', 'start']"
        build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="pending",
            dockerfile_source='custom',
            dockerfile_content=custom_dockerfile
        )
        self.assertEqual(build.dockerfile_source, 'custom')
        self.assertEqual(build.dockerfile_content, custom_dockerfile)
    
    def test_build_with_repo_file_dockerfile(self):
        """Test creating a build using a file from the repo as Dockerfile."""
        build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="pending",
            dockerfile_source='repo_file',
            dockerfile_path='docker/Dockerfile.prod'
        )
        self.assertEqual(build.dockerfile_source, 'repo_file')
        self.assertEqual(build.dockerfile_path, 'docker/Dockerfile.prod')
    
    @patch('builds.views.threading.Thread')
    def test_create_build_with_dockerfile_config(self, mock_thread):
        """Test creating a build with Dockerfile configuration via POST."""
        url = reverse('build_create', args=[self.repo.id, self.commit.id])
        
        custom_dockerfile = "FROM nginx:alpine\nCOPY . /usr/share/nginx/html"
        response = self.client.post(url, {
            'dockerfile_source': 'custom',
            'dockerfile_content': custom_dockerfile,
            'container_port': '80'
        })
        
        # Should redirect to build detail
        self.assertEqual(response.status_code, 302)
        
        # Build should be created with custom Dockerfile
        build = Build.objects.filter(repository=self.repo, commit=self.commit).first()
        self.assertIsNotNone(build)
        self.assertEqual(build.dockerfile_source, 'custom')
        self.assertEqual(build.dockerfile_content, custom_dockerfile)
        self.assertEqual(build.container_port, 80)


class FileListAPITest(TestCase):
    """Tests for file listing API."""
    
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
    
    def test_list_files_url_resolves(self):
        """Test list files URL resolves correctly."""
        url = reverse('list_commit_files', args=[1, 1])
        self.assertEqual(url, '/builds/api/files/1/1/')
    
    def test_get_file_content_url_resolves(self):
        """Test get file content URL resolves correctly."""
        url = reverse('get_commit_file_content', args=[1, 1])
        self.assertEqual(url, '/builds/api/file-content/1/1/')
    
    def test_get_file_content_missing_path(self):
        """Test get file content returns error when path is missing."""
        url = reverse('get_commit_file_content', args=[self.repo.id, self.commit.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'File path is required')


class DockerfileTemplatesTest(TestCase):
    """Tests for Dockerfile templates functionality."""
    
    def setUp(self):
        self.client = Client()
        
        # Create and login a test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.login(username='testuser', password='testpass')
    
    def test_get_dockerfile_templates(self):
        """Test that templates are loaded from the templates directory."""
        from builds.models import get_dockerfile_templates
        
        templates = get_dockerfile_templates()
        
        # Should have several templates
        self.assertGreater(len(templates), 0)
        
        # Check for expected templates
        self.assertIn('Python', templates)
        self.assertIn('Django', templates)
        self.assertIn('Flask', templates)
        self.assertIn('FastAPI', templates)
        self.assertIn('Node.js', templates)
        self.assertIn('React', templates)
        self.assertIn('Go', templates)
    
    def test_get_template_choices(self):
        """Test that template choices are generated correctly."""
        from builds.models import get_template_choices
        
        choices = get_template_choices()
        
        # Should be a list of tuples
        self.assertIsInstance(choices, list)
        self.assertGreater(len(choices), 0)
        
        # Each choice should be a tuple of (name, name)
        for choice in choices:
            self.assertIsInstance(choice, tuple)
            self.assertEqual(len(choice), 2)
            self.assertEqual(choice[0], choice[1])
    
    def test_get_default_template(self):
        """Test that default template is Python."""
        from builds.models import get_default_template
        
        default = get_default_template()
        
        # Should contain Python-related content
        self.assertIn('python', default.lower())
    
    def test_template_api_url_resolves(self):
        """Test template API URL resolves correctly."""
        url = reverse('get_dockerfile_template', args=['Python'])
        self.assertEqual(url, '/builds/api/templates/Python/')
    
    def test_template_api_returns_content(self):
        """Test template API returns template content."""
        url = reverse('get_dockerfile_template', args=['Python'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['name'], 'Python')
        self.assertIn('python', data['content'].lower())
    
    def test_template_api_invalid_template(self):
        """Test template API returns error for invalid template."""
        url = reverse('get_dockerfile_template', args=['InvalidTemplate'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('not found', data['error'])
    
    def test_django_template_content(self):
        """Test Django template has correct content."""
        from builds.models import get_dockerfile_templates
        
        templates = get_dockerfile_templates()
        django_template = templates.get('Django', '')
        
        # Vérifier que le template contient les éléments essentiels
        self.assertIn('django', django_template.lower())
        self.assertIn('runserver', django_template.lower())  # Utilise runserver pour dev
        self.assertIn('configure_csrf', django_template.lower())  # Script de configuration CSRF
        self.assertIn('entrypoint.sh', django_template.lower())  # Utilise un entrypoint
    
    def test_flask_template_content(self):
        """Test Flask template has correct content."""
        from builds.models import get_dockerfile_templates
        
        templates = get_dockerfile_templates()
        flask_template = templates.get('Flask', '')
        
        self.assertIn('flask', flask_template.lower())
        self.assertIn('gunicorn', flask_template.lower())
    
    def test_nodejs_template_content(self):
        """Test Node.js template has correct content."""
        from builds.models import get_dockerfile_templates
        
        templates = get_dockerfile_templates()
        nodejs_template = templates.get('Node.js', '')
        
        self.assertIn('node', nodejs_template.lower())
        self.assertIn('npm', nodejs_template.lower())


class PortMappingTest(TestCase):
    """Tests for container port mapping functionality."""
    
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
    
    def test_container_url_with_custom_port(self):
        """Test container URL is generated correctly with custom port."""
        build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success",
            container_port=3000,
            host_port=8888,
            container_status="running"
        )
        self.assertEqual(build.container_url, "http://localhost:8888")
    
    def test_container_url_with_default_port(self):
        """Test container URL with default container port."""
        build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success",
            container_port=8080,
            host_port=49152,
            container_status="running"
        )
        self.assertEqual(build.container_url, "http://localhost:49152")
    
    def test_container_url_no_host_port(self):
        """Test container URL is empty when no host port assigned."""
        build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success",
            container_status="running",
            host_port=None
        )
        self.assertEqual(build.container_url, "")
    
    def test_port_mapping_different_ports(self):
        """Test port mapping with container port different from host port."""
        build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success",
            container_port=80,  # Container runs on port 80
            host_port=32768,    # Mapped to host port 32768
            container_status="running"
        )
        # Container URL should use host port
        self.assertEqual(build.container_url, "http://localhost:32768")
        # Container port should be the internal port
        self.assertEqual(build.container_port, 80)
    
    @patch('builds.views.threading.Thread')
    def test_create_build_with_custom_container_port(self, mock_thread):
        """Test creating a build with custom container port."""
        url = reverse('build_create', args=[self.repo.id, self.commit.id])
        
        response = self.client.post(url, {
            'container_port': '3000',
            'dockerfile_source': 'generated',
            'dockerfile_content': 'FROM node:18\nEXPOSE 3000'
        })
        
        self.assertEqual(response.status_code, 302)
        
        build = Build.objects.get(repository=self.repo, commit=self.commit)
        self.assertEqual(build.container_port, 3000)


class DockerUtilsExtendedTest(TestCase):
    """Extended tests for Docker utilities."""
    
    @patch('builds.docker_utils.subprocess.run')
    def test_start_container_port_retry(self, mock_run):
        """Test container start retries on port conflict."""
        from builds.docker_utils import start_container
        
        # First call fails with port conflict, second succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="port is already allocated"),
            MagicMock(returncode=0, stdout="container123\n")
        ]
        
        container_id, host_port = start_container(
            image_tag="test:latest",
            container_port=8080,
            host_port=9000
        )
        
        self.assertEqual(container_id, "container123")
        # Should have been called twice due to retry
        self.assertEqual(mock_run.call_count, 2)
    
    @patch('builds.docker_utils.subprocess.run')
    def test_start_container_docker_error(self, mock_run):
        """Test container start handles Docker errors."""
        from builds.docker_utils import start_container, DockerError
        
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Image not found"
        )
        
        with self.assertRaises(DockerError) as context:
            start_container(
                image_tag="nonexistent:latest",
                container_port=8080,
                host_port=9000
            )
        
        self.assertIn("Failed to start container", str(context.exception))
    
    @patch('builds.docker_utils.subprocess.run')
    def test_remove_container_success(self, mock_run):
        """Test removing a container."""
        from builds.docker_utils import remove_container
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123\n"
        )
        
        result = remove_container("abc123", force=True)
        self.assertTrue(result)
        
        # Verify force flag was passed
        call_args = mock_run.call_args[0][0]
        self.assertIn('-f', call_args)
    
    @patch('builds.docker_utils.subprocess.run')
    def test_load_image_from_tar(self, mock_run):
        """Test loading Docker image from tar file."""
        from builds.docker_utils import load_image_from_tar
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Loaded image: myapp:v1.0\n"
        )
        
        image_tag = load_image_from_tar("/tmp/test.tar")
        self.assertEqual(image_tag, "myapp:v1.0")
    
    @patch('builds.docker_utils.socket.socket')
    def test_find_available_port_all_in_use(self, mock_socket):
        """Test finding available port when all ports are in use."""
        from builds.docker_utils import find_available_port, DockerError
        
        # Create a mock socket that always raises OSError on bind
        mock_sock_instance = MagicMock()
        mock_sock_instance.bind.side_effect = OSError("Address already in use")
        mock_socket.return_value.__enter__.return_value = mock_sock_instance
        
        with self.assertRaises(DockerError) as context:
            find_available_port(start_port=49000, max_attempts=5)
        
        self.assertIn("No available port found", str(context.exception))


class ContainerLogsAPITest(TestCase):
    """Tests for container logs API."""
    
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
        self.build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success",
            image_tag="test-repo:abc123de",
            container_id="abc123container",
            container_status="running",
            host_port=32768
        )
    
    @patch('builds.views.get_container_logs')
    @patch('builds.views.get_container_status')
    def test_get_logs_success(self, mock_status, mock_logs):
        """Test getting container logs successfully."""
        mock_logs.return_value = "2025-01-01T00:00:00 Log line 1\n2025-01-01T00:00:01 Log line 2"
        mock_status.return_value = "running"
        
        url = reverse('container_logs', args=[self.build.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn("Log line 1", data['logs'])
        self.assertEqual(data['status'], 'running')
    
    @patch('builds.views.get_container_logs')
    @patch('builds.views.get_container_status')
    def test_get_logs_with_tail_parameter(self, mock_status, mock_logs):
        """Test getting container logs with tail parameter."""
        mock_logs.return_value = "Last 50 lines"
        mock_status.return_value = "running"
        
        url = reverse('container_logs', args=[self.build.id])
        response = self.client.get(url, {'tail': '50'})
        
        self.assertEqual(response.status_code, 200)
        mock_logs.assert_called_once_with(self.build.container_id, tail=50)
    
    @patch('builds.views.get_container_logs')
    @patch('builds.views.get_container_status')
    def test_get_logs_invalid_tail_defaults_to_200(self, mock_status, mock_logs):
        """Test that invalid tail parameter defaults to 200."""
        mock_logs.return_value = "Logs"
        mock_status.return_value = "running"
        
        url = reverse('container_logs', args=[self.build.id])
        response = self.client.get(url, {'tail': 'invalid'})
        
        self.assertEqual(response.status_code, 200)
        mock_logs.assert_called_once_with(self.build.container_id, tail=200)
    
    @patch('builds.views.get_container_logs')
    @patch('builds.views.get_container_status')
    def test_get_logs_updates_container_status_when_exited(self, mock_status, mock_logs):
        """Test that container status is updated when container exits."""
        mock_logs.return_value = "Final logs"
        mock_status.return_value = "exited"
        
        url = reverse('container_logs', args=[self.build.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Refresh build from database
        self.build.refresh_from_db()
        self.assertEqual(self.build.container_status, 'stopped')


class PortValidationTest(TestCase):
    """Tests for port validation helper."""
    
    def test_valid_port_string(self):
        """Test validation of valid port as string."""
        from builds.views import _validate_container_port
        
        self.assertEqual(_validate_container_port('8080'), 8080)
        self.assertEqual(_validate_container_port('3000'), 3000)
        self.assertEqual(_validate_container_port('443'), 443)
    
    def test_valid_port_integer(self):
        """Test validation of valid port as integer."""
        from builds.views import _validate_container_port
        
        self.assertEqual(_validate_container_port(8080), 8080)
        self.assertEqual(_validate_container_port(80), 80)
    
    def test_invalid_port_out_of_range(self):
        """Test validation of out-of-range ports."""
        from builds.views import _validate_container_port
        
        # Too low
        self.assertEqual(_validate_container_port(0), 8080)
        self.assertEqual(_validate_container_port(-1), 8080)
        
        # Too high
        self.assertEqual(_validate_container_port(65536), 8080)
        self.assertEqual(_validate_container_port(100000), 8080)
    
    def test_invalid_port_non_numeric(self):
        """Test validation of non-numeric port values."""
        from builds.views import _validate_container_port
        
        self.assertEqual(_validate_container_port('invalid'), 8080)
        self.assertEqual(_validate_container_port('abc'), 8080)
        self.assertEqual(_validate_container_port(None), 8080)
        self.assertEqual(_validate_container_port(''), 8080)
    
    def test_custom_default_port(self):
        """Test validation with custom default port."""
        from builds.views import _validate_container_port
        
        self.assertEqual(_validate_container_port('invalid', default=3000), 3000)
        self.assertEqual(_validate_container_port(None, default=80), 80)


class ContainerControlViewsExtendedTest(TestCase):
    """Extended tests for container control views."""
    
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
        self.build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success",
            image_tag="test-repo:abc123de"
        )
    
    def test_start_container_already_running(self):
        """Test starting container when one is already running."""
        self.build.container_status = 'running'
        self.build.container_id = 'existing123'
        self.build.save()
        
        url = reverse('start_build_container', args=[self.build.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)
        
        # Container status should remain unchanged
        self.build.refresh_from_db()
        self.assertEqual(self.build.container_status, 'running')
    
    @patch('builds.views.start_container')
    @patch('builds.views.load_image_from_tar')
    @patch('os.path.exists')
    def test_start_container_success(self, mock_exists, mock_load, mock_start):
        """Test starting a container successfully."""
        mock_exists.return_value = False
        mock_start.return_value = ("newcontainer123", 49152)
        
        url = reverse('start_build_container', args=[self.build.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)
        
        # Container info should be saved
        self.build.refresh_from_db()
        self.assertEqual(self.build.container_id, "newcontainer123")
        self.assertEqual(self.build.host_port, 49152)
        self.assertEqual(self.build.container_status, 'running')
    
    @patch('builds.views.start_container')
    def test_start_container_docker_error(self, mock_start):
        """Test starting container with Docker error."""
        from builds.docker_utils import DockerError
        mock_start.side_effect = DockerError("Connection refused")
        
        url = reverse('start_build_container', args=[self.build.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)
        
        # Container status should be error
        self.build.refresh_from_db()
        self.assertEqual(self.build.container_status, 'error')
    
    @patch('builds.views.stop_container')
    @patch('builds.views.remove_container')
    def test_stop_container_success(self, mock_remove, mock_stop):
        """Test stopping a container successfully."""
        self.build.container_id = 'running123'
        self.build.container_status = 'running'
        self.build.host_port = 32768
        self.build.save()
        
        mock_stop.return_value = True
        mock_remove.return_value = True
        
        url = reverse('stop_build_container', args=[self.build.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)
        
        # Container info should be cleared
        self.build.refresh_from_db()
        self.assertEqual(self.build.container_id, '')
        self.assertIsNone(self.build.host_port)
        self.assertEqual(self.build.container_status, 'stopped')
    
    @patch('builds.views.stop_container')
    def test_stop_container_docker_error(self, mock_stop):
        """Test stopping container with Docker error."""
        from builds.docker_utils import DockerError
        
        self.build.container_id = 'running123'
        self.build.container_status = 'running'
        self.build.save()
        
        mock_stop.side_effect = DockerError("Timeout")
        
        url = reverse('stop_build_container', args=[self.build.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)
        
        # Container info should remain unchanged
        self.build.refresh_from_db()
        self.assertEqual(self.build.container_id, 'running123')


class BuildDetailViewExtendedTest(TestCase):
    """Extended tests for build detail view with container info."""
    
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
    
    def test_build_detail_shows_container_url(self):
        """Test that build detail shows container URL when running."""
        build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success",
            container_status="running",
            container_id="abc123",
            host_port=32768,
            container_port=8080
        )
        
        url = reverse('build_detail', args=[build.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "http://localhost:32768")
        self.assertContains(response, "Application URL")
    
    def test_build_detail_shows_port_mapping(self):
        """Test that build detail shows port mapping info."""
        build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name="main",
            status="success",
            container_status="running",
            container_id="abc123",
            host_port=49000,
            container_port=3000
        )
        
        url = reverse('build_detail', args=[build.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should show both container port and host port
        self.assertContains(response, "3000")
        self.assertContains(response, "49000")


class BuildListSortingTest(TestCase):
    """Tests for build list sorting - alphabetically by repository name with active builds first."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.url = reverse('build_list')
    
    def test_builds_sorted_alphabetically_by_repository_name(self):
        """Test that builds are sorted alphabetically by repository name."""
        # Create repos in non-alphabetical order
        repo_zebra = GitRepository.objects.create(name="zebra-repo", url="https://github.com/test/zebra.git")
        repo_alpha = GitRepository.objects.create(name="alpha-repo", url="https://github.com/test/alpha.git")
        repo_beta = GitRepository.objects.create(name="beta-repo", url="https://github.com/test/beta.git")
        
        # Create commits for each repo
        commit_zebra = Commit.objects.create(
            repository=repo_zebra, sha="abc123", message="Test",
            author="Test", author_email="test@example.com", committed_at=timezone.now()
        )
        commit_alpha = Commit.objects.create(
            repository=repo_alpha, sha="def456", message="Test",
            author="Test", author_email="test@example.com", committed_at=timezone.now()
        )
        commit_beta = Commit.objects.create(
            repository=repo_beta, sha="ghi789", message="Test",
            author="Test", author_email="test@example.com", committed_at=timezone.now()
        )
        
        # Create builds in different order
        Build.objects.create(repository=repo_zebra, commit=commit_zebra, branch_name="main", status="success")
        Build.objects.create(repository=repo_alpha, commit=commit_alpha, branch_name="main", status="success")
        Build.objects.create(repository=repo_beta, commit=commit_beta, branch_name="main", status="success")
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        # Get builds from context
        builds = list(response.context['builds'])
        
        # Check they are sorted alphabetically by repository name
        repo_names = [build.repository.name for build in builds]
        self.assertEqual(repo_names, ['alpha-repo', 'beta-repo', 'zebra-repo'])
    
    def test_active_builds_sorted_first(self):
        """Test that active (running/pending) builds appear before completed builds, then alphabetically."""
        # Create repos in different order
        repo_alpha = GitRepository.objects.create(name="alpha-repo", url="https://github.com/test/alpha.git")
        repo_beta = GitRepository.objects.create(name="beta-repo", url="https://github.com/test/beta.git")
        repo_gamma = GitRepository.objects.create(name="gamma-repo", url="https://github.com/test/gamma.git")
        
        # Create commits
        commit_alpha = Commit.objects.create(
            repository=repo_alpha, sha="abc123", message="Test",
            author="Test", author_email="test@example.com", committed_at=timezone.now()
        )
        commit_beta = Commit.objects.create(
            repository=repo_beta, sha="def456", message="Test",
            author="Test", author_email="test@example.com", committed_at=timezone.now()
        )
        commit_gamma = Commit.objects.create(
            repository=repo_gamma, sha="ghi789", message="Test",
            author="Test", author_email="test@example.com", committed_at=timezone.now()
        )
        
        # Create builds: alpha=success, beta=running, gamma=pending
        Build.objects.create(repository=repo_alpha, commit=commit_alpha, branch_name="main", status="success")
        Build.objects.create(repository=repo_beta, commit=commit_beta, branch_name="main", status="running")
        Build.objects.create(repository=repo_gamma, commit=commit_gamma, branch_name="main", status="pending")
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        # Get builds from context
        builds = list(response.context['builds'])
        
        # Active builds (pending, running) should come first, sorted alphabetically,
        # then completed builds, sorted alphabetically
        expected_order = ['beta-repo', 'gamma-repo', 'alpha-repo']
        repo_names = [build.repository.name for build in builds]
        self.assertEqual(repo_names, expected_order)


class ContainerListSortingTest(TestCase):
    """Tests for container list sorting - running containers first, then alphabetically by repository name."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.url = reverse('container_list')
    
    def test_containers_sorted_alphabetically_by_repository_name(self):
        """Test that containers are sorted alphabetically by repository name."""
        # Create repos in non-alphabetical order
        repo_zebra = GitRepository.objects.create(name="zebra-repo", url="https://github.com/test/zebra.git")
        repo_alpha = GitRepository.objects.create(name="alpha-repo", url="https://github.com/test/alpha.git")
        repo_beta = GitRepository.objects.create(name="beta-repo", url="https://github.com/test/beta.git")
        
        # Create commits
        commit_zebra = Commit.objects.create(
            repository=repo_zebra, sha="abc123", message="Test",
            author="Test", author_email="test@example.com", committed_at=timezone.now()
        )
        commit_alpha = Commit.objects.create(
            repository=repo_alpha, sha="def456", message="Test",
            author="Test", author_email="test@example.com", committed_at=timezone.now()
        )
        commit_beta = Commit.objects.create(
            repository=repo_beta, sha="ghi789", message="Test",
            author="Test", author_email="test@example.com", committed_at=timezone.now()
        )
        
        # Create successful builds (containers)
        Build.objects.create(
            repository=repo_zebra, commit=commit_zebra, branch_name="main",
            status="success", container_status="stopped"
        )
        Build.objects.create(
            repository=repo_alpha, commit=commit_alpha, branch_name="main",
            status="success", container_status="stopped"
        )
        Build.objects.create(
            repository=repo_beta, commit=commit_beta, branch_name="main",
            status="success", container_status="stopped"
        )
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        # Get builds from context
        builds = list(response.context['builds'])
        
        # Check they are sorted alphabetically by repository name
        repo_names = [build.repository.name for build in builds]
        self.assertEqual(repo_names, ['alpha-repo', 'beta-repo', 'zebra-repo'])
    
    def test_running_containers_sorted_first(self):
        """Test that running containers appear before stopped containers, then alphabetically."""
        # Create repos
        repo_alpha = GitRepository.objects.create(name="alpha-repo", url="https://github.com/test/alpha.git")
        repo_beta = GitRepository.objects.create(name="beta-repo", url="https://github.com/test/beta.git")
        repo_gamma = GitRepository.objects.create(name="gamma-repo", url="https://github.com/test/gamma.git")
        
        # Create commits
        commit_alpha = Commit.objects.create(
            repository=repo_alpha, sha="abc123", message="Test",
            author="Test", author_email="test@example.com", committed_at=timezone.now()
        )
        commit_beta = Commit.objects.create(
            repository=repo_beta, sha="def456", message="Test",
            author="Test", author_email="test@example.com", committed_at=timezone.now()
        )
        commit_gamma = Commit.objects.create(
            repository=repo_gamma, sha="ghi789", message="Test",
            author="Test", author_email="test@example.com", committed_at=timezone.now()
        )
        
        # Create builds: alpha=stopped, beta=running, gamma=running
        Build.objects.create(
            repository=repo_alpha, commit=commit_alpha, branch_name="main",
            status="success", container_status="stopped"
        )
        Build.objects.create(
            repository=repo_beta, commit=commit_beta, branch_name="main",
            status="success", container_status="running", host_port=8080, container_id="abc123"
        )
        Build.objects.create(
            repository=repo_gamma, commit=commit_gamma, branch_name="main",
            status="success", container_status="running", host_port=8081, container_id="def456"
        )
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        # Get builds from context
        builds = list(response.context['builds'])
        
        # Running containers should come first (alphabetically), then stopped (alphabetically)
        expected_order = ['beta-repo', 'gamma-repo', 'alpha-repo']
        repo_names = [build.repository.name for build in builds]
        self.assertEqual(repo_names, expected_order)
