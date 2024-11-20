from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from banking_api.models import UserProfile
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    try:
        if created:
            # If a new User is created, create or get the associated UserProfile
            profile, created = UserProfile.objects.get_or_create(user=instance)
            if created:
                if profile.balance is None:
                    profile.balance = 0.00
                    profile.save()
                logger.info(f"Profile created for {instance.username} with initial balance of {profile.balance}")
            else:
                logger.info(f"Profile already exists for {instance.username}")
        else:
            try:
                profile = UserProfile.objects.get(user=instance)
                logger.info(f"User profile exists for {instance.username}, no update needed")
            except UserProfile.DoesNotExist:
                logger.warning(f"User profile does not exist for {instance.username}")
    except Exception as e:
        logger.error(f"Error creating or saving profile for {instance.username}: {str(e)}")
