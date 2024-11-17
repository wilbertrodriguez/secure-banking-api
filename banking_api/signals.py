from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile
import logging
from django.db import transaction

logger = logging.getLogger(__name__)

# This creates or saves a profile for each new user
@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    try:
        with transaction.atomic():
            if created:
                UserProfile.objects.get_or_create(user=instance)
                logger.info(f"Profile created for {instance.username}")
            else:
                logger.info(f"Profile saved for {instance.username}")
    except Exception as e:
        logger.error(f"Error creating or saving profile for {instance.username}: {str(e)}")
