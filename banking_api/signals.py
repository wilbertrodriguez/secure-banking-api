from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    try:
        if created:
            # Only create the profile if it doesn't exist already
            profile, created = UserProfile.objects.get_or_create(user=instance)
            if created:
                logger.info(f"Profile created for {instance.username}")
            else:
                logger.warning(f"Profile already exists for {instance.username}")
        else:
            # This case is triggered when an existing User object is updated
            logger.info(f"User profile saved for {instance.username}")
    except Exception as e:
        logger.error(f"Error creating or saving profile for {instance.username}: {str(e)}")