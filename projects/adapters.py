"""
Custom adapters for allauth social authentication.
"""
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse


class NoHandsSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter to provide better error handling.
    """
    
    def get_app(self, request, provider, client_id=None):
        """
        Override to provide friendly error when SocialApp is not configured.
        """
        try:
            return super().get_app(request, provider, client_id=client_id)
        except SocialApp.DoesNotExist:
            # Return None to trigger authentication_error handling
            return None
    
    def authentication_error(
        self,
        request,
        provider_id,
        error=None,
        exception=None,
        extra_context=None,
    ):
        """
        Handle authentication errors with a friendly message.
        """
        # Check if this is a missing SocialApp error
        try:
            SocialApp.objects.get(provider=provider_id)
        except SocialApp.DoesNotExist:
            # OAuth not configured - show setup instructions
            context = {
                'error': 'OAuth not configured',
                'error_message': f'{provider_id.title()} OAuth is not configured. Please contact your administrator.',
                'provider': provider_id,
            }
            return render(request, 'socialaccount/authentication_error.html', context)
        
        # For other errors, use default handling
        return super().authentication_error(
            request, provider_id, error=error, exception=exception, extra_context=extra_context
        )
