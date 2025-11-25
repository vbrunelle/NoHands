"""
Signal handlers for the projects app.
"""
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from allauth.socialaccount.models import SocialAccount
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=SocialAccount)
def make_first_github_user_admin(sender, instance, created, **kwargs):
    """
    Signal handler to make the first GitHub user a superuser.
    
    When a new GitHub social account is created, check if this is the first user
    in the system. If so, promote them to superuser (admin).
    
    Uses atomic transaction to prevent race conditions.
    """
    if created and instance.provider == 'github':
        user = instance.user
        
        # Use atomic transaction to prevent race conditions
        with transaction.atomic():
            # Lock the User table to prevent concurrent modifications
            user_count = User.objects.select_for_update().count()
            
            if user_count == 1:
                # This is the first user, make them a superuser
                user.is_staff = True
                user.is_superuser = True
                user.save()
                
                logger.info(f"First GitHub user {user.username} has been promoted to superuser")
