"""
Tests for middleware functionality.
"""
from django.test import TestCase, Client, RequestFactory, override_settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.http import HttpResponse
from allauth.socialaccount.models import SocialApp

from nohands_project.middleware import InitialSetupMiddleware, SocialAppErrorMiddleware, DynamicAllowedHostsMiddleware
from projects.models import AllowedHost


class InitialSetupMiddlewareTest(TestCase):
    """Test cases for InitialSetupMiddleware."""
    
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        
    def test_redirects_to_setup_when_no_users(self):
        """Test that requests are redirected to initial setup when no users exist."""
        User.objects.all().delete()
        
        response = self.client.get('/repositories/')
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/repositories/initial-setup/')
    
    def test_allows_access_when_users_exist(self):
        """Test that requests pass through when users exist."""
        User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        
        response = self.client.get('/repositories/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_admin_is_exempt(self):
        """Test that admin panel is accessible without users."""
        User.objects.all().delete()
        
        response = self.client.get('/admin/')
        
        # Should redirect to admin login, not initial setup
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)
    
    def test_accounts_is_exempt(self):
        """Test that accounts URLs are accessible without users."""
        User.objects.all().delete()
        
        response = self.client.get('/accounts/login/')
        
        # Should be accessible (200) or redirect within accounts
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotEqual(response.url, '/repositories/initial-setup/')
    
    def test_static_is_exempt(self):
        """Test that static files are accessible without users."""
        User.objects.all().delete()
        
        # Static URLs should not redirect to initial setup
        # (they might 404 if file doesn't exist, but should not redirect)
        response = self.client.get('/static/test.css')
        
        # Static files middleware handles this - not redirected to setup
        self.assertNotEqual(response.status_code, 302)
    
    def test_api_is_exempt(self):
        """Test that API is accessible without users (DRF handles auth)."""
        User.objects.all().delete()
        
        response = self.client.get('/api/repositories/')
        
        # API should return 403 (permission denied) not redirect to setup
        self.assertEqual(response.status_code, 403)
    
    def test_initial_setup_page_accessible_without_users(self):
        """Test that initial setup page itself is accessible without users."""
        User.objects.all().delete()
        
        response = self.client.get('/repositories/initial-setup/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_builds_redirect_when_no_users(self):
        """Test that builds page redirects to setup when no users."""
        User.objects.all().delete()
        
        response = self.client.get('/builds/')
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/repositories/initial-setup/')


class SocialAppErrorMiddlewareTest(TestCase):
    """Test cases for SocialAppErrorMiddleware."""
    
    def setUp(self):
        self.client = Client()
        # Create a user so we don't hit InitialSetupMiddleware
        User.objects.create_user(username='testuser', password='testpass')
    
    def test_shows_error_page_when_oauth_not_configured(self):
        """Test that friendly error page is shown when OAuth is not configured."""
        # Ensure no SocialApp exists
        SocialApp.objects.all().delete()
        
        response = self.client.get('/accounts/github/login/')
        
        # Should show error page with 500 status
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, 'GitHub OAuth Not Configured', status_code=500)
    
    def test_normal_response_when_oauth_configured(self):
        """Test that normal response is returned when OAuth is configured."""
        # Create OAuth configuration
        site = Site.objects.get_or_create(pk=1, defaults={'domain': 'testserver', 'name': 'Test'})[0]
        social_app = SocialApp.objects.create(
            provider='github',
            name='GitHub',
            client_id='test_id',
            secret='test_secret'
        )
        social_app.sites.add(site)
        
        response = self.client.get('/accounts/github/login/')
        
        # Should return normal response (200)
        self.assertEqual(response.status_code, 200)
    
    def test_error_page_contains_setup_instructions(self):
        """Test that error page contains setup instructions."""
        SocialApp.objects.all().delete()
        
        response = self.client.get('/accounts/github/login/')
        
        # Should contain helpful information
        self.assertContains(response, 'setup_github_oauth', status_code=500)
        self.assertContains(response, 'github.com/settings/developers', status_code=500)


class MiddlewareIntegrationTest(TestCase):
    """Integration tests for middleware stack."""
    
    def setUp(self):
        self.client = Client()
    
    def test_full_flow_no_users_no_oauth(self):
        """Test full flow when no users and no OAuth configured."""
        User.objects.all().delete()
        SocialApp.objects.all().delete()
        
        # Access root should redirect to initial setup
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/repositories/initial-setup/')
        
        # Initial setup should be accessible and show OAuth form
        response = self.client.get('/repositories/initial-setup/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create a GitHub OAuth Application')
    
    def test_full_flow_no_users_with_oauth(self):
        """Test full flow when no users but OAuth is configured."""
        User.objects.all().delete()
        
        # Configure OAuth
        site = Site.objects.get_or_create(pk=1, defaults={'domain': 'testserver', 'name': 'Test'})[0]
        social_app = SocialApp.objects.create(
            provider='github',
            name='GitHub',
            client_id='test_id',
            secret='test_secret'
        )
        social_app.sites.add(site)
        
        # Access root should redirect to initial setup
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/repositories/initial-setup/')
        
        # Initial setup should show Connect button
        response = self.client.get('/repositories/initial-setup/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Connect with GitHub')
    
    def test_full_flow_with_users(self):
        """Test full flow when users exist."""
        user = User.objects.create_user(username='testuser', password='testpass')
        
        # Access root without login should redirect to repositories
        # which then redirects to login
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/repositories/')
        
        # Following the redirect should then redirect to login
        response = self.client.get('/repositories/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/github/login/', response.url)
        
        # Login and access
        self.client.login(username='testuser', password='testpass')
        response = self.client.get('/repositories/')
        self.assertEqual(response.status_code, 200)


class DynamicAllowedHostsMiddlewareTest(TestCase):
    """Test cases for DynamicAllowedHostsMiddleware."""
    
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        # Clear any existing allowed hosts
        AllowedHost.objects.all().delete()
    
    def test_allows_any_host_when_no_users(self):
        """Test that any host is allowed when no users exist (initial setup)."""
        User.objects.all().delete()
        
        # Should be accessible regardless of host
        response = self.client.get('/repositories/initial-setup/')
        self.assertEqual(response.status_code, 200)
    
    def test_allows_all_hosts_when_no_hosts_configured(self):
        """Test that all hosts are allowed when no hosts are configured."""
        # Create a user (so setup is complete)
        User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        
        # Without any allowed hosts configured, requests should still work
        response = self.client.get('/repositories/')
        self.assertEqual(response.status_code, 200)
    
    @override_settings(DJANGO_ALLOWED_HOSTS_FROM_ENV=[])
    def test_allows_configured_host_from_database(self):
        """Test that requests are allowed for hosts in the database."""
        # Create a user (so setup is complete)
        User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        
        # Add the test server host to allowed hosts
        AllowedHost.objects.create(hostname='testserver', is_active=True)
        
        # Request should succeed
        response = self.client.get('/repositories/')
        self.assertEqual(response.status_code, 200)
    
    @override_settings(DJANGO_ALLOWED_HOSTS_FROM_ENV=[])
    def test_blocks_disallowed_host(self):
        """Test that requests from disallowed hosts are blocked."""
        # Create a user (so setup is complete)
        User.objects.create_user(username='testuser', password='testpass')
        
        # Add a different host to allowed hosts (not 'testserver')
        AllowedHost.objects.create(hostname='allowed.example.com', is_active=True)
        
        # Request from testserver should be blocked
        response = self.client.get('/repositories/')
        self.assertEqual(response.status_code, 400)
        self.assertIn('testserver', response.content.decode())
    
    @override_settings(DJANGO_ALLOWED_HOSTS_FROM_ENV=[])
    def test_inactive_hosts_are_not_allowed(self):
        """Test that inactive hosts are not allowed."""
        # Create a user (so setup is complete)
        User.objects.create_user(username='testuser', password='testpass')
        
        # Add host but mark it as inactive
        AllowedHost.objects.create(hostname='testserver', is_active=False)
        # Also add an active but different host
        AllowedHost.objects.create(hostname='other.example.com', is_active=True)
        
        # Request should be blocked because testserver is inactive
        response = self.client.get('/repositories/')
        self.assertEqual(response.status_code, 400)
    
    @override_settings(DJANGO_ALLOWED_HOSTS_FROM_ENV=['testserver'])
    def test_env_allowed_hosts_combined_with_database(self):
        """Test that DJANGO_ALLOWED_HOSTS_FROM_ENV from settings are combined with database hosts."""
        # Create a user (so setup is complete)
        User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        
        # testserver is in Django settings, so request should work
        # even without database entry
        response = self.client.get('/repositories/')
        self.assertEqual(response.status_code, 200)
    
    @override_settings(DJANGO_ALLOWED_HOSTS_FROM_ENV=[])
    def test_wildcard_host_allows_all(self):
        """Test that wildcard '*' host allows any host."""
        # Create a user (so setup is complete)
        User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        
        # Add wildcard host
        AllowedHost.objects.create(hostname='*', is_active=True)
        
        # Request should succeed
        response = self.client.get('/repositories/')
        self.assertEqual(response.status_code, 200)


class HostMatchingTest(TestCase):
    """Test cases for host matching logic in DynamicAllowedHostsMiddleware."""
    
    def test_subdomain_wildcard_matching(self):
        """Test that subdomain wildcards match correctly."""
        middleware = DynamicAllowedHostsMiddleware(lambda r: None)
        
        # .example.com should match sub.example.com and example.com
        self.assertTrue(middleware._is_host_allowed('sub.example.com', ['.example.com']))
        self.assertTrue(middleware._is_host_allowed('example.com', ['.example.com']))
        self.assertTrue(middleware._is_host_allowed('deep.sub.example.com', ['.example.com']))
        
        # .example.com should NOT match badexample.com
        self.assertFalse(middleware._is_host_allowed('badexample.com', ['.example.com']))
        self.assertFalse(middleware._is_host_allowed('notexample.com', ['.example.com']))
    
    def test_exact_host_matching(self):
        """Test that exact hosts match correctly."""
        middleware = DynamicAllowedHostsMiddleware(lambda r: None)
        
        self.assertTrue(middleware._is_host_allowed('example.com', ['example.com']))
        self.assertTrue(middleware._is_host_allowed('example.com:8000', ['example.com']))
        self.assertFalse(middleware._is_host_allowed('other.com', ['example.com']))
    
    def test_wildcard_matching(self):
        """Test that wildcard * matches everything."""
        middleware = DynamicAllowedHostsMiddleware(lambda r: None)
        
        self.assertTrue(middleware._is_host_allowed('anything.com', ['*']))
        self.assertTrue(middleware._is_host_allowed('localhost:8000', ['*']))


class AllowedHostModelTest(TestCase):
    """Test cases for AllowedHost model."""
    
    def setUp(self):
        AllowedHost.objects.all().delete()
    
    def test_get_all_active_hosts(self):
        """Test getting all active hosts."""
        AllowedHost.objects.create(hostname='host1.com', is_active=True)
        AllowedHost.objects.create(hostname='host2.com', is_active=True)
        AllowedHost.objects.create(hostname='host3.com', is_active=False)
        
        active_hosts = AllowedHost.get_all_active_hosts()
        self.assertEqual(len(active_hosts), 2)
        self.assertIn('host1.com', active_hosts)
        self.assertIn('host2.com', active_hosts)
        self.assertNotIn('host3.com', active_hosts)
    
    def test_is_host_allowed(self):
        """Test checking if a host is allowed."""
        AllowedHost.objects.create(hostname='allowed.com', is_active=True)
        AllowedHost.objects.create(hostname='inactive.com', is_active=False)
        
        self.assertTrue(AllowedHost.is_host_allowed('allowed.com'))
        self.assertFalse(AllowedHost.is_host_allowed('inactive.com'))
        self.assertFalse(AllowedHost.is_host_allowed('unknown.com'))
    
    def test_add_host_creates_new(self):
        """Test adding a new host."""
        host, created = AllowedHost.add_host('new.example.com')
        
        self.assertTrue(created)
        self.assertEqual(host.hostname, 'new.example.com')
        self.assertTrue(host.is_active)
    
    def test_add_host_returns_existing(self):
        """Test that add_host returns existing host without duplicating."""
        AllowedHost.objects.create(hostname='existing.com', is_active=True)
        
        host, created = AllowedHost.add_host('existing.com')
        
        self.assertFalse(created)
        self.assertEqual(host.hostname, 'existing.com')
        self.assertEqual(AllowedHost.objects.filter(hostname='existing.com').count(), 1)
    
    def test_str_representation(self):
        """Test string representation."""
        active_host = AllowedHost.objects.create(hostname='active.com', is_active=True)
        inactive_host = AllowedHost.objects.create(hostname='inactive.com', is_active=False)
        
        self.assertIn('active.com', str(active_host))
        self.assertIn('active', str(active_host))
        self.assertIn('inactive.com', str(inactive_host))
        self.assertIn('inactive', str(inactive_host))


class InitialSetupUnknownHostTest(TestCase):
    """
    Test cases for the initial setup scenario when accessing from an unknown external host.
    
    This test reproduces the issue where accessing NoHands from a remote machine (e.g., machine.local:8000)
    before initial setup causes a DisallowedHost error instead of showing the setup page.
    
    Relevant issue: "Still checking to see if current host is in the allowed host before
    the first initialization of the NoHands server"
    """
    
    def setUp(self):
        # Ensure no users exist to simulate fresh installation
        User.objects.all().delete()
        # Clear any allowed hosts
        AllowedHost.objects.all().delete()
    
    def test_unknown_external_host_allowed_during_initial_setup(self):
        """
        Test that an unknown external host (e.g., machine.local:8000) is allowed
        when accessing the server before initial setup.
        
        This simulates the issue where:
        1. User starts NoHands on a remote machine (e.g., ceos.home)
        2. User tries to access the initial setup page from another machine
        3. Request should succeed and show setup page, not raise DisallowedHost
        """
        client = Client()
        
        # Simulate accessing from an external unknown host
        response = client.get('/', HTTP_HOST='machine.local:8000')
        
        # Should redirect to initial setup, not raise DisallowedHost
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/repositories/initial-setup/')
    
    def test_unknown_host_can_access_initial_setup_page(self):
        """
        Test that the initial setup page itself is accessible from an unknown host
        when no users exist (fresh installation).
        """
        client = Client()
        
        # Access setup page from an unknown external host
        response = client.get('/repositories/initial-setup/', HTTP_HOST='ceos.home:8000')
        
        # Should return 200, not DisallowedHost error
        self.assertEqual(response.status_code, 200)
    
    def test_various_unknown_hosts_allowed_during_initial_setup(self):
        """
        Test various types of unknown hosts during initial setup.
        
        Tests hosts like:
        - Local network hostnames (e.g., myserver.local)
        - IP addresses with ports
        - Domain names
        - Hostnames with hyphens
        """
        client = Client()
        unknown_hosts = [
            'myserver.local:8000',
            '192.168.1.100:8000',
            'unknown-server.home:8000',
            'test-machine:8000',
            'my-host.domain.com:8000',
        ]
        
        for host in unknown_hosts:
            response = client.get('/', HTTP_HOST=host)
            self.assertEqual(
                response.status_code, 
                302, 
                f"Host '{host}' should redirect to setup, got status {response.status_code}"
            )
            self.assertEqual(
                response.url,
                '/repositories/initial-setup/',
                f"Host '{host}' should redirect to /repositories/initial-setup/"
            )
    
    def test_accounts_paths_accessible_from_unknown_host_during_setup(self):
        """
        Test that OAuth/accounts paths are accessible from unknown hosts during initial setup.
        This is necessary for the GitHub OAuth flow to work during first setup.
        """
        client = Client()
        
        # Access accounts paths from unknown host
        response = client.get('/accounts/login/', HTTP_HOST='remote.server:8000')
        
        # Should be accessible (200 or redirect within accounts), not DisallowedHost
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            # Should not redirect to initial setup (accounts is exempt)
            self.assertNotEqual(response.url, '/repositories/initial-setup/')
    
    def test_api_accessible_from_unknown_host_during_setup(self):
        """
        Test that API paths return proper authentication error (not DisallowedHost)
        when accessed from unknown host during initial setup.
        """
        client = Client()
        
        response = client.get('/api/repositories/', HTTP_HOST='external.machine:8000')
        
        # Should return 403 (permission denied), not DisallowedHost error
        self.assertEqual(response.status_code, 403)


class DatabaseUnavailableMiddlewareTest(TestCase):
    """
    Test cases for middleware behavior when database is unavailable.
    
    The middleware should gracefully handle cases where the database
    is not yet available (e.g., during startup, before migrations).
    """
    
    def test_middleware_handles_allowedhost_query_exception(self):
        """
        Test that middleware gracefully handles exceptions when querying AllowedHost.
        
        When AllowedHost.get_all_active_hosts() fails, the middleware should
        fall back to environment-based allowed hosts or allow all.
        """
        from unittest.mock import patch
        from django.db.utils import OperationalError
        
        # Create a user so we pass the initial setup check
        User.objects.create_user(username='testuser', password='testpass')
        
        client = Client()
        
        # Mock AllowedHost.get_all_active_hosts() to raise a database exception
        with patch('projects.models.AllowedHost.get_all_active_hosts') as mock_get_hosts:
            mock_get_hosts.side_effect = OperationalError("Database unavailable")
            
            with self.settings(DJANGO_ALLOWED_HOSTS_FROM_ENV=['testserver']):
                # Should use env hosts and allow the request
                client.login(username='testuser', password='testpass')
                response = client.get('/repositories/')
                
                # Should return 200 since testserver is in env hosts
                self.assertEqual(response.status_code, 200)
