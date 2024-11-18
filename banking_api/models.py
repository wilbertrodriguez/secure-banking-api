from django.db import models
from django.contrib.auth import get_user_model
from django.db import transaction
import logging
from django.contrib.auth.models import Group
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

User = get_user_model()

class Transaction(models.Model):
    sender = models.ForeignKey(User, related_name='sent_transactions', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_transactions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')],
        default='pending'
    )

    def __str__(self):
        return f"Transaction from {self.sender.username} to {self.receiver.username} for {self.amount}"

    def complete_transaction(self):
        """Method to complete a transaction (set status to 'completed')."""
        try:
            sender_profile = self.sender.userprofile
            receiver_profile = self.receiver.userprofile

            # Logging for debugging before the transaction
            logger.info(f"Before transaction: Sender balance = {sender_profile.balance}, Receiver balance = {receiver_profile.balance}")

            # Start atomic block
            with transaction.atomic():
                if sender_profile.balance >= self.amount:  # Check if sender has enough balance
                    self.status = 'completed'
                    sender_profile.balance -= self.amount  # Deduct the amount from sender's balance
                    receiver_profile.balance += self.amount  # Add the amount to receiver's balance

                    # Save the updated profiles and transaction
                    sender_profile.save()
                    receiver_profile.save()
                    self.save()

                    # Logging for debugging after the transaction
                    logger.info(f"Transaction from {self.sender.username} to {self.receiver.username} completed successfully.")
                    logger.info(f"After transaction: Sender balance = {sender_profile.balance}, Receiver balance = {receiver_profile.balance}")
                else:
                    self.fail_transaction("Insufficient funds")  # Fail the transaction if insufficient funds

        except Exception as e:
            self.fail_transaction(str(e))  # Handle any exception during the transaction process
            logger.error(f"Transaction error: {str(e)}")

    def fail_transaction(self, reason):
        """Method to fail a transaction (set status to 'failed' and log the reason)."""
        self.status = 'failed'
        self.save()

        # Log the failure reason for auditing purposes
        logger.error(f"Transaction from {self.sender.username} to {self.receiver.username} failed: {reason}")


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username}'s profile"

    def save(self, *args, **kwargs):
        # Ensure profile is only created once
        if not self.pk:
            # Check if the user already has a profile
            if not UserProfile.objects.filter(user=self.user).exists():
                super().save(*args, **kwargs)
                logger.info(f"Profile for user {self.user.username} created with initial balance.")
            else:
                logger.info(f"Profile for user {self.user.username} already exists.")
        else:
            super().save(*args, **kwargs)

def create_roles():
    """
    Create the default roles/groups in the system if they don't exist.
    """
    roles = ['User', 'Admin']
    for role in roles:
        Group.objects.get_or_create(name=role)
    logger.info("Default roles created.")
