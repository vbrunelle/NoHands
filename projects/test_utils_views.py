"""
Tests for utility functions and views.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.conf import settings
from django.urls import reverse
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from unittest.mock import patch, MagicMock
import os

from projects.views import (
    read_env_values,
    write_env_values,
    setup_github_oauth,
    get_env_file_path,
)


class EnvFileUtilsTest(TestCase):
    """Test cases for .env file utility functions."""
    
    def setUp(self):
        self.env_file_path = get_env_file_path()
        self.env_backup = None
        if self.env_file_path.exists():
            with open(self.env_file_path, 'r') as f:
                self.env_backup = f.read()
            os.remove(self.env_file_path)
        # Clear environment variables
        self.old_client_id = os.environ.pop('GITHUB_CLIENT_ID', None)
        self.old_client_secret = os.environ.pop('GITHUB_CLIENT_SECRET', None)
    
    def tearDown(self):
        # Restore .env file
        if self.env_backup is not None:
            with open(self.env_file_path, 'w') as f:
                f.write(self.env_backup)
        elif self.env_file_path.exists():
            os.remove(self.env_file_path)
        # Restore environment variables
        if self.old_client_id:
            os.environ['GITHUB_CLIENT_ID'] = self.old_client_id
        if self.old_client_secret:
            os.environ['GITHUB_CLIENT_SECRET'] = self.old_client_secret
    
    def test_read_env_values_no_file(self):
        """Test reading env values when no file exists."""
        values = read_env_values()
        
        self.assertEqual(values['client_id'], '')
        self.assertEqual(values['client_secret'], '')
    
    def test_read_env_values_from_file(self):
        """Test reading env values from .env file."""
        with open(self.env_file_path, 'w') as f:
            f.write('GITHUB_CLIENT_ID="test_client_id"\n')
            f.write('GITHUB_CLIENT_SECRET="test_secret"\n')
        
        values = read_env_values()
        
        self.assertEqual(values['client_id'], 'test_client_id')
        self.assertEqual(values['client_secret'], 'test_secret')
    
    def test_read_env_values_from_environment(self):
        """Test reading env values from environment variables."""
        os.environ['GITHUB_CLIENT_ID'] = 'env_client_id'
        os.environ['GITHUB_CLIENT_SECRET'] = 'env_secret'
        
        values = read_env_values()
        
        self.assertEqual(values['client_id'], 'env_client_id')
        self.assertEqual(values['client_secret'], 'env_secret')
    
    def test_read_env_values_file_takes_precedence(self):
        """Test that .env file values take precedence over environment."""
        os.environ['GITHUB_CLIENT_ID'] = 'env_client_id'
        os.environ['GITHUB_CLIENT_SECRET'] = 'env_secret'
        
        with open(self.env_file_path, 'w') as f:
            f.write('GITHUB_CLIENT_ID="file_client_id"\n')
            f.write('GITHUB_CLIENT_SECRET="file_secret"\n')
        
        values = read_env_values()
        
        self.assertEqual(values['client_id'], 'file_client_id')
        self.assertEqual(values['client_secret'], 'file_secret')
    
    def test_read_env_values_handles_quotes(self):
        """Test reading env values with different quote styles."""
        with open(self.env_file_path, 'w') as f:
            f.write("GITHUB_CLIENT_ID='single_quoted'\n")
            f.write('GITHUB_CLIENT_SECRET=no_quotes\n')
        
        values = read_env_values()
        
        self.assertEqual(values['client_id'], 'single_quoted')
        self.assertEqual(values['client_secret'], 'no_quotes')
    
    def test_read_env_values_ignores_comments(self):
        """Test that comments in .env file are ignored."""
        with open(self.env_file_path, 'w') as f:
            f.write('# This is a comment\n')
            f.write('GITHUB_CLIENT_ID="test_id"\n')
            f.write('# GITHUB_CLIENT_SECRET="commented_out"\n')
            f.write('GITHUB_CLIENT_SECRET="real_secret"\n')
        
        values = read_env_values()
        
        self.assertEqual(values['client_id'], 'test_id')
        self.assertEqual(values['client_secret'], 'real_secret')
    
    def test_write_env_values_creates_file(self):
        """Test writing env values creates new file."""
        result = write_env_values('new_client_id', 'new_secret')
        
        self.assertTrue(result)
        self.assertTrue(self.env_file_path.exists())
        
        with open(self.env_file_path, 'r') as f:
            content = f.read()
        
        self.assertIn('GITHUB_CLIENT_ID="new_client_id"', content)
        self.assertIn('GITHUB_CLIENT_SECRET="new_secret"', content)
    
    def test_write_env_values_updates_existing(self):
        """Test writing env values updates existing file."""
        with open(self.env_file_path, 'w') as f:
            f.write('OTHER_VAR="keep_me"\n')
            f.write('GITHUB_CLIENT_ID="old_id"\n')
            f.write('GITHUB_CLIENT_SECRET="old_secret"\n')
        
        result = write_env_values('new_id', 'new_secret')
        
        self.assertTrue(result)
        
        with open(self.env_file_path, 'r') as f:
            content = f.read()
        
        self.assertIn('OTHER_VAR="keep_me"', content)
        self.assertIn('GITHUB_CLIENT_ID="new_id"', content)
        self.assertIn('GITHUB_CLIENT_SECRET="new_secret"', content)
        self.assertNotIn('old_id', content)
        self.assertNotIn('old_secret', content)
    
    def test_write_env_values_sets_permissions(self):
        """Test that .env file is created with restricted permissions."""
        write_env_values('test_id', 'test_secret')
        
        if os.name != 'nt':  # Skip on Windows
            import stat
            mode = os.stat(self.env_file_path).st_mode
            # Owner should have read/write, no one else should have access
            self.assertTrue(mode & stat.S_IRUSR)
            self.assertTrue(mode & stat.S_IWUSR)
            self.assertFalse(mode & stat.S_IRGRP)
            self.assertFalse(mode & stat.S_IROTH)


class SetupGitHubOAuthFunctionTest(TestCase):
    """Test cases for setup_github_oauth function."""
    
    def setUp(self):
        Site.objects.get_or_create(pk=1, defaults={'domain': 'testserver', 'name': 'Test'})
    
    def test_creates_social_app(self):
        """Test that function creates SocialApp."""
        result = setup_github_oauth('test_id', 'test_secret')
        
        self.assertTrue(result)
        
        social_app = SocialApp.objects.get(provider='github')
        self.assertEqual(social_app.client_id, 'test_id')
        self.assertEqual(social_app.secret, 'test_secret')
    
    def test_updates_existing_social_app(self):
        """Test that function updates existing SocialApp."""
        site = Site.objects.get(pk=1)
        SocialApp.objects.create(
            provider='github',
            name='GitHub',
            client_id='old_id',
            secret='old_secret'
        )
        
        result = setup_github_oauth('new_id', 'new_secret')
        
        self.assertTrue(result)
        
        social_app = SocialApp.objects.get(provider='github')
        self.assertEqual(social_app.client_id, 'new_id')
        self.assertEqual(social_app.secret, 'new_secret')
    
    def test_associates_site_with_social_app(self):
        """Test that function associates Site with SocialApp."""
        result = setup_github_oauth('test_id', 'test_secret')
        
        self.assertTrue(result)
        
        site = Site.objects.get(pk=1)
        social_app = SocialApp.objects.get(provider='github')
        self.assertIn(site, social_app.sites.all())
    
    def test_updates_site_domain(self):
        """Test that function can update site domain."""
        result = setup_github_oauth('test_id', 'test_secret', site_domain='example.com')
        
        self.assertTrue(result)
        
        site = Site.objects.get(pk=1)
        self.assertEqual(site.domain, 'example.com')


class InitialSetupViewTest(TestCase):
    """Test cases for initial_setup view."""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('initial_setup')
        Site.objects.get_or_create(pk=1, defaults={'domain': 'testserver', 'name': 'Test'})
        self.env_file_path = get_env_file_path()
        if self.env_file_path.exists():
            os.remove(self.env_file_path)
    
    def tearDown(self):
        if self.env_file_path.exists():
            os.remove(self.env_file_path)
    
    def _clean_state(self):
        User.objects.all().delete()
        SocialApp.objects.all().delete()
    
    def test_get_shows_form_when_oauth_not_configured(self):
        """Test GET request shows OAuth form when not configured."""
        self._clean_state()
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Configure GitHub OAuth')
        self.assertContains(response, 'client_id')
        self.assertContains(response, 'client_secret')
    
    def test_get_shows_connect_when_oauth_configured(self):
        """Test GET request shows Connect button when OAuth is configured."""
        self._clean_state()
        
        site = Site.objects.get(pk=1)
        social_app = SocialApp.objects.create(
            provider='github',
            name='GitHub',
            client_id='test_id',
            secret='test_secret'
        )
        social_app.sites.add(site)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Connect with GitHub')
        self.assertNotContains(response, 'Step 1: Configure GitHub OAuth')
    
    def test_redirects_when_users_exist(self):
        """Test that view redirects when users exist."""
        User.objects.create_user(username='testuser', password='testpass')
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('repository_list'))
    
    def test_post_creates_oauth_config(self):
        """Test POST request creates OAuth configuration."""
        self._clean_state()
        
        response = self.client.post(self.url, {
            'client_id': 'form_client_id',
            'client_secret': 'form_client_secret',
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'configured successfully')
        
        social_app = SocialApp.objects.get(provider='github')
        self.assertEqual(social_app.client_id, 'form_client_id')
    
    def test_post_with_empty_fields_shows_error(self):
        """Test POST with empty fields shows error."""
        self._clean_state()
        
        response = self.client.post(self.url, {
            'client_id': '',
            'client_secret': '',
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'required')
        self.assertFalse(SocialApp.objects.filter(provider='github').exists())
    
    def test_post_saves_to_env_file(self):
        """Test POST with save_to_env saves to .env file."""
        self._clean_state()
        
        response = self.client.post(self.url, {
            'client_id': 'env_client_id',
            'client_secret': 'env_client_secret',
            'save_to_env': 'on',
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.env_file_path.exists())
        
        with open(self.env_file_path, 'r') as f:
            content = f.read()
        
        self.assertIn('env_client_id', content)


class RepositoryListViewExtendedTest(TestCase):
    """Extended tests for repository list view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.url = reverse('repository_list')
        Site.objects.get_or_create(pk=1, defaults={'domain': 'testserver', 'name': 'Test'})
    
    def test_requires_authentication(self):
        """Test that view requires authentication."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/github/login/', response.url)
    
    def test_shows_available_github_repos_with_token(self):
        """Test that available GitHub repos are shown when user has token."""
        self.client.login(username='testuser', password='testpass')
        
        # Create social account and token
        from allauth.socialaccount.models import SocialAccount, SocialToken
        
        social_account = SocialAccount.objects.create(
            user=self.user,
            provider='github',
            uid='12345'
        )
        
        # Mock GitHub API
        with patch('projects.views.Github') as mock_github:
            mock_repo = MagicMock()
            mock_repo.id = 123
            mock_repo.name = 'test-repo'
            mock_repo.full_name = 'testuser/test-repo'
            mock_repo.description = 'Test'
            mock_repo.clone_url = 'https://github.com/test/test.git'
            mock_repo.default_branch = 'main'
            mock_repo.private = False
            
            mock_user = MagicMock()
            mock_user.get_repos.return_value.__getitem__ = MagicMock(return_value=[mock_repo])
            
            mock_github_instance = MagicMock()
            mock_github_instance.get_user.return_value = mock_user
            mock_github.return_value = mock_github_instance
            
            # Create token
            SocialToken.objects.create(
                account=social_account,
                token='fake_token'
            )
            
            response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)


class SignalHandlerExtendedTest(TestCase):
    """Extended tests for signal handlers."""
    
    def test_first_user_becomes_superuser(self):
        """Test that first GitHub user becomes superuser."""
        user = User.objects.create_user(
            username='firstuser',
            password='testpass'
        )
        
        SocialAccount.objects.create(
            user=user,
            provider='github',
            uid='12345'
        )
        
        user.refresh_from_db()
        
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
    
    def test_second_user_not_superuser(self):
        """Test that second GitHub user does not become superuser."""
        first_user = User.objects.create_user(
            username='firstuser',
            password='testpass'
        )
        SocialAccount.objects.create(
            user=first_user,
            provider='github',
            uid='11111'
        )
        
        second_user = User.objects.create_user(
            username='seconduser',
            password='testpass'
        )
        SocialAccount.objects.create(
            user=second_user,
            provider='github',
            uid='22222'
        )
        
        second_user.refresh_from_db()
        
        self.assertFalse(second_user.is_superuser)
        self.assertFalse(second_user.is_staff)
    
    def test_non_github_provider_ignored(self):
        """Test that non-GitHub providers don't trigger admin promotion."""
        User.objects.all().delete()
        
        user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        
        # Create non-GitHub social account
        SocialAccount.objects.create(
            user=user,
            provider='google',  # Not GitHub
            uid='12345'
        )
        
        user.refresh_from_db()
        
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
    
    def test_existing_users_count_matters(self):
        """Test that existing users count is checked correctly."""
        # Create an existing user (not via GitHub)
        User.objects.create_user(username='existinguser', password='testpass')
        
        # Create new user via GitHub
        new_user = User.objects.create_user(username='newuser', password='testpass')
        SocialAccount.objects.create(
            user=new_user,
            provider='github',
            uid='12345'
        )
        
        new_user.refresh_from_db()
        
        # New user should NOT be superuser since there were already users
        self.assertFalse(new_user.is_superuser)
