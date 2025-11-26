"""
Middleware for NoHands project.
"""
from django.shortcuts import redirect, render
from django.contrib.auth.models import User
from django.http import HttpResponseBadRequest
from django.conf import settings
from django.db.utils import DatabaseError, OperationalError
from allauth.socialaccount.models import SocialApp
import logging

logger = logging.getLogger(__name__)


class InitialSetupMiddleware:
    """
    Middleware to enforce initial setup via GitHub OAuth.
    
    If no users exist in the system (fresh install), all requests will be redirected
    to the initial setup page where the first user must connect via GitHub.
    The first user to connect becomes a superuser (admin).
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Paths that are always accessible even without users
        # Using string paths instead of reverse() to avoid circular import issues
        self.exempt_paths = [
            '/repositories/initial-setup/',  # Initial setup page
            '/accounts/',  # Allow all allauth URLs
            '/admin/',  # Allow admin access (for createsuperuser)
            '/static/',  # Allow static files
            '/api/',  # Allow API access (DRF will handle authentication)
        ]
    
    def __call__(self, request):
        # Check if any users exist
        # Wrap in try/except to handle cases where database isn't ready
        try:
            has_users = User.objects.exists()
        except (DatabaseError, OperationalError):
            # If database is not available, allow the request through
            # This ensures the server can start even if DB is not ready yet
            return self.get_response(request)
        
        # If no users exist and the request is not to an exempt path
        if not has_users:
            current_path = request.path
            
            # Check if current path is exempt
            is_exempt = any(current_path.startswith(path) for path in self.exempt_paths)
            
            if not is_exempt:
                # Redirect to initial setup page
                return redirect('/repositories/initial-setup/')
        
        response = self.get_response(request)
        return response


class SocialAppErrorMiddleware:
    """
    Middleware to catch SocialApp.DoesNotExist errors and show a friendly error page.
    
    When OAuth is not configured, this middleware catches the exception and shows
    setup instructions instead of a 500 error.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except (SocialApp.DoesNotExist, ValueError) as e:
            # OAuth not configured - check if it's about missing app
            if isinstance(e, ValueError) and 'missing: app' in str(e):
                context = {
                    'error': 'OAuth not configured',
                    'error_message': 'GitHub OAuth is not configured. Please contact your administrator.',
                }
                return render(request, 'socialaccount/authentication_error.html', context, status=500)
            # Re-raise if it's a different error
            raise
    
    def process_exception(self, request, exception):
        """
        Process exceptions raised during request processing.
        """
        if isinstance(exception, SocialApp.DoesNotExist):
            context = {
                'error': 'OAuth not configured',
                'error_message': 'GitHub OAuth is not configured. Please contact your administrator.',
            }
            return render(request, 'socialaccount/authentication_error.html', context, status=500)
        elif isinstance(exception, ValueError) and 'missing: app' in str(exception):
            context = {
                'error': 'OAuth not configured',
                'error_message': 'GitHub OAuth is not configured. Please contact your administrator.',
            }
            return render(request, 'socialaccount/authentication_error.html', context, status=500)
        return None


class DynamicAllowedHostsMiddleware:
    """
    Middleware to dynamically manage allowed hosts based on application state.
    
    Behavior:
    - During first start (no users exist): Any host is allowed to facilitate initial setup.
      The host from the first setup request is automatically added to the allowed hosts list.
    - After setup (users exist): Only hosts in the AllowedHost database table are allowed.
      If a request comes from a disallowed host, a 400 Bad Request is returned.
    
    This middleware should be placed early in the middleware stack to validate hosts
    before other middleware runs.
    
    Note: Django's ALLOWED_HOSTS is set to ['*'] in settings to allow all requests through
    to this middleware. The actual host validation is handled here.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Import here once instead of on every request
        from projects.models import AllowedHost
        self.AllowedHost = AllowedHost
    
    def __call__(self, request):
        # Get the host from the request (includes port if present)
        host = request.get_host()
        
        # Check if any users exist (i.e., setup is complete)
        # Wrap in try/except to handle cases where database isn't ready
        try:
            has_users = User.objects.exists()
        except (DatabaseError, OperationalError):
            # If database is not available (e.g., during startup), allow all hosts
            # This ensures the server can start even if DB is not ready yet
            return self.get_response(request)
        
        if not has_users:
            # During initial setup, allow any host
            # The host will be added to allowed hosts during the setup process
            return self.get_response(request)
        
        # After setup, check if the host is in the allowed hosts list
        # First check database allowed hosts
        try:
            db_hosts = self.AllowedHost.get_all_active_hosts()
        except (DatabaseError, OperationalError):
            # If database is not available, use empty list
            db_hosts = []
        
        # Also check DJANGO_ALLOWED_HOSTS_FROM_ENV (from environment variable)
        env_hosts = getattr(settings, 'DJANGO_ALLOWED_HOSTS_FROM_ENV', [])
        
        # Combine both lists, filtering out empty strings
        all_allowed_hosts = [h for h in (db_hosts + env_hosts) if h]
        
        # If no hosts are configured at all, allow all (but log a warning)
        if not all_allowed_hosts:
            logger.warning(
                "No allowed hosts configured. Consider adding hosts via admin panel."
            )
            return self.get_response(request)
        
        # Check if the host is allowed
        # Support wildcard matching (e.g., '*' allows all, '.example.com' allows subdomains)
        if self._is_host_allowed(host, all_allowed_hosts):
            return self.get_response(request)
        
        # Host not allowed - return 400 Bad Request
        logger.warning(f"Blocked request from disallowed host: {host}")
        return HttpResponseBadRequest(
            f"Invalid HTTP_HOST header: '{host}'. "
            f"You may need to add '{host}' to your allowed hosts in the admin panel."
        )
    
    def _is_host_allowed(self, host, allowed_hosts):
        """Check if a host matches any of the allowed host patterns."""
        # Remove port from host for matching
        host_without_port = host.split(':')[0]
        
        for pattern in allowed_hosts:
            if pattern == '*':
                # Wildcard matches everything
                return True
            elif pattern.startswith('.'):
                # Subdomain wildcard (e.g., '.example.com' matches 'sub.example.com' and 'example.com')
                # Must match either the exact domain or a proper subdomain
                domain = pattern[1:]  # Remove leading dot
                if host_without_port == domain or host_without_port.endswith('.' + domain):
                    return True
            else:
                # Exact match (with or without port)
                if host == pattern or host_without_port == pattern:
                    return True
        
        return False
