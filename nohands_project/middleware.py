"""
Middleware for NoHands project.
"""
from django.shortcuts import redirect, render
from django.contrib.auth.models import User
from allauth.socialaccount.models import SocialApp


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
        has_users = User.objects.exists()
        
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
