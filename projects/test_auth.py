"""
Tests for authentication and initial setup functionality.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from allauth.socialaccount.models import SocialAccount


class InitialSetupTestCase(TestCase):
    """Test cases for initial setup functionality."""
    
    def setUp(self):
        self.client = Client()
    
    def test_initial_setup_shown_when_no_users(self):
        """Test that initial setup page is shown when no users exist."""
        # Ensure no users exist
        User.objects.all().delete()
        
        # Try to access any page
        response = self.client.get(reverse('repository_list'))
        
        # Should redirect to initial setup
        self.assertRedirects(response, reverse('initial_setup'))
    
    def test_initial_setup_redirects_when_users_exist(self):
        """Test that initial setup redirects to main page when users exist."""
        # Create a user
        User.objects.create_user(username='testuser', password='testpass')
        
        # Access initial setup page
        response = self.client.get(reverse('initial_setup'), follow=False)
        
        # Should redirect to repository list (which then may require login)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('repository_list'))
    
    def test_admin_panel_accessible_without_users(self):
        """Test that admin panel is accessible even when no users exist."""
        # Ensure no users exist
        User.objects.all().delete()
        
        # Try to access admin
        response = self.client.get('/admin/')
        
        # Should redirect to admin login, not initial setup
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)


class AuthenticationTestCase(TestCase):
    """Test cases for authentication requirements."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
    
    def test_repository_list_requires_login(self):
        """Test that repository list requires authentication."""
        response = self.client.get(reverse('repository_list'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/github/login/', response.url)
    
    def test_build_list_requires_login(self):
        """Test that build list requires authentication."""
        response = self.client.get(reverse('build_list'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/github/login/', response.url)
    
    def test_authenticated_user_can_access(self):
        """Test that authenticated users can access protected pages."""
        # Login
        self.client.login(username='testuser', password='testpass')
        
        # Access repository list
        response = self.client.get(reverse('repository_list'))
        self.assertEqual(response.status_code, 200)
        
        # Access build list
        response = self.client.get(reverse('build_list'))
        self.assertEqual(response.status_code, 200)


class FirstUserAdminTestCase(TestCase):
    """Test cases for first user becoming admin."""
    
    def test_first_github_user_becomes_admin(self):
        """Test that the first GitHub user becomes a superuser."""
        # Create a user
        user = User.objects.create_user(
            username='firstuser',
            email='first@example.com',
            password='testpass'
        )
        
        # Simulate GitHub account connection
        social_account = SocialAccount.objects.create(
            user=user,
            provider='github',
            uid='12345',
            extra_data={}
        )
        
        # Refresh user from database
        user.refresh_from_db()
        
        # User should be superuser
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
    
    def test_second_github_user_not_admin(self):
        """Test that the second GitHub user does not become admin."""
        # Create first user (will be admin)
        first_user = User.objects.create_user(
            username='firstuser',
            email='first@example.com',
            password='testpass'
        )
        SocialAccount.objects.create(
            user=first_user,
            provider='github',
            uid='12345',
            extra_data={}
        )
        
        # Create second user
        second_user = User.objects.create_user(
            username='seconduser',
            email='second@example.com',
            password='testpass'
        )
        SocialAccount.objects.create(
            user=second_user,
            provider='github',
            uid='67890',
            extra_data={}
        )
        
        # Refresh second user from database
        second_user.refresh_from_db()
        
        # Second user should not be superuser
        self.assertFalse(second_user.is_staff)
        self.assertFalse(second_user.is_superuser)


class APIAuthenticationTestCase(TestCase):
    """Test cases for API authentication."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
    
    def test_api_requires_authentication(self):
        """Test that API endpoints require authentication."""
        response = self.client.get('/api/repositories/', 
                                   HTTP_ACCEPT='application/json')
        
        # Should return 403 Forbidden
        self.assertEqual(response.status_code, 403)
    
    def test_authenticated_api_access(self):
        """Test that authenticated users can access API."""
        # Login
        self.client.login(username='testuser', password='testpass')
        
        # Access API
        response = self.client.get('/api/repositories/',
                                   HTTP_ACCEPT='application/json')
        
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)
