"""
Middleware for NoHands project.
"""
from django.shortcuts import redirect
from django.contrib.auth.models import User


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
