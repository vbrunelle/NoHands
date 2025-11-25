"""
Tests for middleware functionality.
"""
from django.test import TestCase, Client, RequestFactory, override_settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.http import HttpResponse
from allauth.socialaccount.models import SocialApp

from nohands_project.middleware import InitialSetupMiddleware, SocialAppErrorMiddleware


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
        self.assertContains(response, 'Configure GitHub OAuth')
    
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
