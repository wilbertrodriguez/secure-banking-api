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
            # Only create the profile if it doesn't exist already
            profile, created = UserProfile.objects.get_or_create(user=instance)
            
            if created:
                # Initialize the balance if it doesn't exist
                if profile.balance is None:
                    profile.balance = 0.00  # Set default balance
                    profile.save()
                logger.info(f"Profile created for {instance.username} with initial balance of {profile.balance}")
            else:
                logger.warning(f"Profile already exists for {instance.username}")
        else:
            # This case is triggered when an existing User object is updated
            try:
                profile = UserProfile.objects.get(user=instance)
                profile.save()  # Save the profile to reflect any changes (e.g., balance changes)
                logger.info(f"User profile updated for {instance.username}")
            except UserProfile.DoesNotExist:
                logger.warning(f"User profile does not exist for {instance.username}, but no new profile created.")
                
    except Exception as e:
        logger.error(f"Error creating or saving profile for {instance.username}: {str(e)}")