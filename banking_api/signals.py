from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile
import logging

logger = logging.getLogger(__name__)

# This creates a profile for each new user
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Create a new user profile and associate it with the user
        UserProfile.objects.create(user=instance)
        logger.info(f"Profile created for {instance.username}")

# This saves the user profile whenever the user instance is saved
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, created, **kwargs):
    if created:  # Only save the profile if the user is created, to avoid unnecessary saving
        # Ensure the profile is created and exists
        if not hasattr(instance, 'profile'):
            # If the profile doesn't exist, create it
            UserProfile.objects.create(user=instance)
            logger.info(f"Profile created for {instance.username}")
        else:
            # If the profile exists, save it
            instance.profile.save()
            logger.info(f"Profile saved for {instance.username}")
