"""
Tests for the container proxy functionality.
"""
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime, timezone
import requests

from builds.models import Build
from builds.views import proxy_to_container
from builds.docker_utils import start_container
from projects.models import GitRepository, Commit


def create_mock_response(status_code=200, content=b'', headers=None, cookies=None):
    """Helper function to create a properly configured mock response."""
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.content = content
    mock_response.headers = headers or {'content-type': 'text/html; charset=utf-8'}
    mock_response.cookies = cookies or []  # Empty list by default
    mock_response.iter_content = lambda chunk_size: [content]
    return mock_response


class ProxyURLRewritingTests(TestCase):
    """Test that URLs are correctly rewritten in proxied responses."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = Client()
        self.client.login(username='testuser', password='testpass')
        
        # Create test data
        self.repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git',
            user=self.user
        )
        self.commit = Commit.objects.create(
            repository=self.repo,
            sha='abc123',
            message='test commit',
            author='Test Author',
            author_email='test@example.com',
            committed_at=datetime.now(timezone.utc)
        )
        self.build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name='main',
            container_port=8000,
            container_status='running',
            container_id='test123',
            host_port=9000,
            status='success'
        )
    
    @patch('builds.views.requests.get')
    def test_absolute_urls_rewritten_in_html(self, mock_get):
        """Test that absolute URLs are rewritten in HTML responses."""
        # Mock response with absolute URLs
        html_content = b'''
        <html>
            <a href="http://localhost:9000/page">Link</a>
            <a href="http://127.0.0.1:9000/admin/">Admin</a>
        </html>
        '''
        mock_get.return_value = create_mock_response(content=html_content)
        
        response = self.client.get(f'/builds/{self.build.id}/fwd/')
        
        # Check that URLs are rewritten
        content = response.content.decode('utf-8')
        self.assertIn(f'/builds/{self.build.id}/fwd/page', content)
        self.assertIn(f'/builds/{self.build.id}/fwd/admin/', content)
        self.assertNotIn('http://localhost:9000/', content)
    
    @patch('builds.views.requests.get')
    def test_relative_urls_rewritten_in_html(self, mock_get):
        """Test that relative URLs are rewritten in HTML responses."""
        html_content = b'''
        <html>
            <a href="/login/">Login</a>
            <form action="/submit/">
            <img src="/static/logo.png">
        </html>
        '''
        mock_get.return_value = create_mock_response(content=html_content)
        
        response = self.client.get(f'/builds/{self.build.id}/fwd/')
        
        content = response.content.decode('utf-8')
        self.assertIn(f'/builds/{self.build.id}/fwd/login/', content)
        self.assertIn(f'/builds/{self.build.id}/fwd/submit/', content)
        self.assertIn(f'/builds/{self.build.id}/fwd/static/logo.png', content)
    
    @patch('builds.views.requests.get')
    def test_redirect_location_rewritten(self, mock_get):
        """Test that redirect Location headers are rewritten."""
        headers = {
            'content-type': 'text/html',
            'location': '/admin/login/'
        }
        mock_get.return_value = create_mock_response(
            status_code=302,
            content=b'',
            headers=headers
        )
        
        response = self.client.get(f'/builds/{self.build.id}/fwd/')
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f'/builds/{self.build.id}/fwd/admin/login/')


class ProxyCookieHandlingTests(TestCase):
    """Test that cookies are correctly filtered and handled."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        self.repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git',
            user=self.user
        )
        self.commit = Commit.objects.create(
            repository=self.repo,
            sha='abc123',
            message='test commit',
            author='Test Author',
            author_email='test@example.com',
            committed_at=datetime.now(timezone.utc)
        )
        self.build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name='main',
            container_port=8000,
            container_status='running',
            container_id='test123',
            host_port=9000,
            status='success'
        )
    
    @patch('builds.views.requests.get')
    def test_nohands_cookies_filtered_out(self, mock_get):
        """Test that NoHands cookies are not forwarded to container."""
        mock_get.return_value = create_mock_response(
            status_code=200,
            content=b'test',
            headers={'content-type': 'text/plain'}
        )
        
        # Create request with NoHands cookies
        request = self.factory.get('/')
        request.user = self.user
        request.COOKIES = {
            'nohands_sessionid': 'nohands123',
            'nohands_csrftoken': 'csrf456',
            'sessionid': 'app789',  # App cookie should be forwarded
        }
        request.META['HTTP_COOKIE'] = 'nohands_sessionid=nohands123; nohands_csrftoken=csrf456; sessionid=app789'
        
        response = proxy_to_container(request, self.build.id, '')
        
        # Check that requests.get was called with filtered cookies
        call_args = mock_get.call_args
        headers = call_args[1]['headers']
        
        # NoHands cookies should not be in the forwarded cookies
        if 'Cookie' in headers:
            self.assertNotIn('nohands_sessionid', headers['Cookie'])
            self.assertNotIn('nohands_csrftoken', headers['Cookie'])
            # App cookie should be present
            self.assertIn('sessionid=app789', headers['Cookie'])


class ProxyCSRFHeaderTests(TestCase):
    """Test that CSRF headers are correctly set for container."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        self.repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git',
            user=self.user
        )
        self.commit = Commit.objects.create(
            repository=self.repo,
            sha='abc123',
            message='test commit',
            author='Test Author',
            author_email='test@example.com',
            committed_at=datetime.now(timezone.utc)
        )
        self.build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name='main',
            container_port=8000,
            container_status='running',
            container_id='test123',
            host_port=9000,
            status='success'
        )
    
    @patch('builds.views.requests.post')
    def test_csrf_headers_set_for_post(self, mock_post):
        """Test that Origin and Referer headers are set for POST requests."""
        mock_post.return_value = create_mock_response(
            status_code=200,
            content=b'test',
            headers={'content-type': 'text/plain'}
        )
        
        request = self.factory.post('/')
        request.user = self.user
        
        response = proxy_to_container(request, self.build.id, 'submit/')
        
        # Check headers
        call_args = mock_post.call_args
        headers = call_args[1]['headers']
        
        self.assertEqual(headers['Host'], f'127.0.0.1:{self.build.host_port}')
        # Le Referer doit inclure le path complet maintenant
        self.assertEqual(headers['Referer'], f'http://127.0.0.1:{self.build.host_port}/submit/')
        self.assertEqual(headers['Origin'], f'http://127.0.0.1:{self.build.host_port}')


class ContainerStartEnvVarsTests(TestCase):
    """Test that environment variables are correctly passed to containers."""
    
    @patch('builds.docker_utils.subprocess.run')
    def test_env_vars_passed_to_docker_run(self, mock_run):
        """Test that env_vars parameter results in -e flags in docker run."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="container123\n",
            stderr=""
        )
        
        env_vars = {
            'CSRF_TRUSTED_ORIGINS': 'http://localhost:8000',
            'DEBUG': 'True'
        }
        
        container_id, port = start_container(
            image_tag='test:latest',
            container_port=8000,
            env_vars=env_vars
        )
        
        # Check that docker run command includes -e flags
        call_args = mock_run.call_args[0][0]
        self.assertIn('-e', call_args)
        self.assertIn('CSRF_TRUSTED_ORIGINS=http://localhost:8000', call_args)
        self.assertIn('DEBUG=True', call_args)
    
    @patch('builds.docker_utils.subprocess.run')
    def test_no_env_vars_works(self, mock_run):
        """Test that container starts without env_vars parameter."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="container123\n",
            stderr=""
        )
        
        container_id, port = start_container(
            image_tag='test:latest',
            container_port=8000
        )
        
        self.assertEqual(container_id, 'container123')


class ProxyAuthenticationTests(TestCase):
    """Test that proxy requires authentication."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        self.repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git',
            user=self.user
        )
        self.commit = Commit.objects.create(
            repository=self.repo,
            sha='abc123',
            message='test commit',
            author='Test Author',
            author_email='test@example.com',
            committed_at=datetime.now(timezone.utc)
        )
        self.build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name='main',
            container_port=8000,
            container_status='running',
            container_id='test123',
            host_port=9000,
            status='success'
        )
    
    def test_proxy_requires_login(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(f'/builds/{self.build.id}/fwd/')
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/github/login/', response.url)
    
    @patch('builds.views.requests.get')
    def test_authenticated_user_can_access_proxy(self, mock_get):
        """Test that authenticated users can access the proxy."""
        mock_get.return_value = create_mock_response(
            status_code=200,
            content=b'test',
            headers={'content-type': 'text/plain'}
        )
        
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(f'/builds/{self.build.id}/fwd/')
        
        self.assertEqual(response.status_code, 200)
