"""
Tests for Django settings configuration.

These tests verify that the NoHands settings properly handle environment variables
and follow Django best practices.
"""

import os
import unittest
from unittest import mock


class SecretKeyTest(unittest.TestCase):
    """Tests for SECRET_KEY configuration."""
    
    def test_secret_key_uses_default_when_env_not_set(self):
        """Test that SECRET_KEY uses default when DJANGO_SECRET_KEY is not set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            # Remove DJANGO_SECRET_KEY if it exists
            os.environ.pop('DJANGO_SECRET_KEY', None)
            
            # Re-import settings to get fresh values
            from importlib import reload
            import nohands_project.settings as settings_module
            reload(settings_module)
            
            self.assertTrue(
                settings_module.SECRET_KEY,
                "SECRET_KEY should have a default value when DJANGO_SECRET_KEY is not set"
            )
            self.assertNotEqual(
                settings_module.SECRET_KEY,
                '',
                "SECRET_KEY should not be empty when DJANGO_SECRET_KEY is not set"
            )
    
    def test_secret_key_uses_default_when_env_is_empty_string(self):
        """Test that SECRET_KEY uses default when DJANGO_SECRET_KEY is empty string.
        
        This is a critical test for Docker deployments where the environment variable
        might be set to an empty string (e.g., DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY:-}).
        """
        with mock.patch.dict(os.environ, {'DJANGO_SECRET_KEY': ''}, clear=False):
            # Re-import settings to get fresh values
            from importlib import reload
            import nohands_project.settings as settings_module
            reload(settings_module)
            
            self.assertTrue(
                settings_module.SECRET_KEY,
                "SECRET_KEY should have a default value when DJANGO_SECRET_KEY is empty"
            )
            self.assertNotEqual(
                settings_module.SECRET_KEY,
                '',
                "SECRET_KEY should not be empty when DJANGO_SECRET_KEY is empty string"
            )
    
    def test_secret_key_uses_custom_value_when_env_is_set(self):
        """Test that SECRET_KEY uses custom value when DJANGO_SECRET_KEY is set."""
        custom_key = 'my-custom-secret-key-for-testing-123'
        with mock.patch.dict(os.environ, {'DJANGO_SECRET_KEY': custom_key}, clear=False):
            # Re-import settings to get fresh values
            from importlib import reload
            import nohands_project.settings as settings_module
            reload(settings_module)
            
            self.assertEqual(
                settings_module.SECRET_KEY,
                custom_key,
                "SECRET_KEY should use the DJANGO_SECRET_KEY environment variable value"
            )


class AllAuthSettingsTest(unittest.TestCase):
    """Tests for django-allauth configuration."""
    
    def test_allauth_uses_modern_login_methods_setting(self):
        """Test that allauth uses ACCOUNT_LOGIN_METHODS instead of deprecated setting."""
        from importlib import reload
        import nohands_project.settings as settings_module
        reload(settings_module)
        
        # Check that the modern setting is present
        self.assertTrue(
            hasattr(settings_module, 'ACCOUNT_LOGIN_METHODS'),
            "Settings should define ACCOUNT_LOGIN_METHODS (modern allauth setting)"
        )
        
        # Check that deprecated setting is not present
        self.assertFalse(
            hasattr(settings_module, 'ACCOUNT_AUTHENTICATION_METHOD'),
            "Settings should NOT define deprecated ACCOUNT_AUTHENTICATION_METHOD"
        )
    
    def test_allauth_uses_modern_signup_fields_setting(self):
        """Test that allauth uses ACCOUNT_SIGNUP_FIELDS instead of deprecated setting."""
        from importlib import reload
        import nohands_project.settings as settings_module
        reload(settings_module)
        
        # Check that the modern setting is present
        self.assertTrue(
            hasattr(settings_module, 'ACCOUNT_SIGNUP_FIELDS'),
            "Settings should define ACCOUNT_SIGNUP_FIELDS (modern allauth setting)"
        )
        
        # Check that deprecated setting is not present
        self.assertFalse(
            hasattr(settings_module, 'ACCOUNT_EMAIL_REQUIRED'),
            "Settings should NOT define deprecated ACCOUNT_EMAIL_REQUIRED"
        )


if __name__ == '__main__':
    unittest.main()
