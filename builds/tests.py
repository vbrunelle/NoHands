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
        
        self.assertIn('gunicorn', django_template.lower())
        self.assertIn('django', django_template.lower())
    
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
