"""
Tests for GitHub OAuth setup and configuration.
"""
from django.test import TestCase, Client
from django.contrib.sites.models import Site
from django.core.management import call_command
from allauth.socialaccount.models import SocialApp
from io import StringIO
import os


class GitHubOAuthSetupTest(TestCase):
    """Test cases for GitHub OAuth setup."""
    
    def test_setup_command_without_credentials(self):
        """Test setup command fails gracefully without credentials."""
        # Clear environment variables
        os.environ.pop('GITHUB_CLIENT_ID', None)
        os.environ.pop('GITHUB_CLIENT_SECRET', None)
        
        out = StringIO()
        call_command('setup_github_oauth', stdout=out)
        output = out.getvalue()
        
        self.assertIn('GitHub OAuth credentials not provided', output)
        self.assertIn('https://github.com/settings/developers', output)
    
    def test_setup_command_with_credentials(self):
        """Test setup command creates social app with credentials."""
        out = StringIO()
        call_command(
            'setup_github_oauth',
            '--client-id', 'test_client_id',
            '--client-secret', 'test_client_secret',
            '--site-domain', 'testserver',
            stdout=out
        )
        output = out.getvalue()
        
        # Check success message
        self.assertIn('GitHub OAuth app created successfully', output)
        
        # Verify site was created/updated
        site = Site.objects.get(pk=1)
        self.assertEqual(site.domain, 'testserver')
        self.assertEqual(site.name, 'NoHands')
        
        # Verify social app was created
        social_app = SocialApp.objects.get(provider='github')
        self.assertEqual(social_app.name, 'GitHub')
        self.assertEqual(social_app.client_id, 'test_client_id')
        self.assertEqual(social_app.secret, 'test_client_secret')
        self.assertIn(site, social_app.sites.all())
    
    def test_setup_command_updates_existing_app(self):
        """Test setup command updates existing social app."""
        # Create initial app
        site = Site.objects.get_or_create(pk=1)[0]
        social_app = SocialApp.objects.create(
            provider='github',
            name='GitHub',
            client_id='old_client_id',
            secret='old_secret'
        )
        social_app.sites.add(site)
        
        # Run setup with new credentials
        out = StringIO()
        call_command(
            'setup_github_oauth',
            '--client-id', 'new_client_id',
            '--client-secret', 'new_client_secret',
            stdout=out
        )
        output = out.getvalue()
        
        # Check update message
        self.assertIn('GitHub OAuth app updated successfully', output)
        
        # Verify app was updated
        social_app.refresh_from_db()
        self.assertEqual(social_app.client_id, 'new_client_id')
        self.assertEqual(social_app.secret, 'new_client_secret')
    
    def test_setup_command_with_env_variables(self):
        """Test setup command uses environment variables."""
        # Set environment variables
        os.environ['GITHUB_CLIENT_ID'] = 'env_client_id'
        os.environ['GITHUB_CLIENT_SECRET'] = 'env_secret'
        
        try:
            out = StringIO()
            call_command('setup_github_oauth', stdout=out)
            
            # Verify social app was created with env vars
            social_app = SocialApp.objects.get(provider='github')
            self.assertEqual(social_app.client_id, 'env_client_id')
            self.assertEqual(social_app.secret, 'env_secret')
        finally:
            # Cleanup
            os.environ.pop('GITHUB_CLIENT_ID', None)
            os.environ.pop('GITHUB_CLIENT_SECRET', None)


class GitHubLoginPageTest(TestCase):
    """Test cases for GitHub login page."""
    
    def setUp(self):
        self.client = Client()
        # Setup OAuth app
        site = Site.objects.get_or_create(pk=1, defaults={'domain': 'testserver', 'name': 'Test'})[0]
        social_app = SocialApp.objects.create(
            provider='github',
            name='GitHub',
            client_id='test_client_id',
            secret='test_client_secret'
        )
        social_app.sites.add(site)
    
    def test_github_login_page_accessible(self):
        """Test that GitHub login page is accessible."""
        response = self.client.get('/accounts/github/login/')
        self.assertEqual(response.status_code, 200)
    
    def test_github_login_page_uses_custom_template(self):
        """Test that custom template is used."""
        response = self.client.get('/accounts/github/login/')
        self.assertTemplateUsed(response, 'socialaccount/login.html')
        self.assertContains(response, 'Connect with GitHub')
        self.assertContains(response, 'ti-brand-github')  # Tabler icon
    
    def test_github_login_page_styling(self):
        """Test that page uses Tabler.io styling."""
        response = self.client.get('/accounts/github/login/')
        # Check for Tabler CSS classes
        self.assertContains(response, 'card card-md')
        self.assertContains(response, 'btn btn-primary')
        self.assertContains(response, 'ti ti-rocket')
    
    def test_github_login_without_oauth_app_configured(self):
        """Test error handling when OAuth app is not configured."""
        from allauth.socialaccount.models import SocialApp as AllauthSocialApp
        
        # Delete the social app
        AllauthSocialApp.objects.all().delete()
        
        # Should show a friendly error page instead of raising an exception
        response = self.client.get('/accounts/github/login/')
        
        # Should return 500 with error page
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, 'GitHub OAuth Not Configured', status_code=500)
        self.assertContains(response, 'setup_github_oauth', status_code=500)
