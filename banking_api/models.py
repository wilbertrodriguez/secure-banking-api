from django.db import models, transaction
from django.contrib.auth import get_user_model
import logging
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from decimal import Decimal
from django.db.models import F

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
        """
        Completes the transaction, deducts the sender's balance and adds to the receiver's balance.
        This method ensures atomicity and handles failures if the sender has insufficient funds.
        """
        try:
            sender_profile = self.sender.profile
            receiver_profile = self.receiver.profile

            # Log the transaction before processing
            logger.info(f"Before transaction: Sender balance = {sender_profile.balance}, Receiver balance = {receiver_profile.balance}")

            with transaction.atomic():
                # Check if the sender has enough balance
                if sender_profile.balance >= self.amount:
                    # Update balances atomically using F expressions to prevent race conditions
                    sender_profile.balance = F('balance') - self.amount
                    receiver_profile.balance = F('balance') + self.amount

                    # Save the updated profiles
                    sender_profile.save(update_fields=['balance'])
                    receiver_profile.save(update_fields=['balance'])

                    # Mark the transaction as completed
                    self.status = 'completed'
                    self.save()

                    # Log the successful transaction
                    logger.info(f"Transaction from {self.sender.username} to {self.receiver.username} completed successfully.")
                else:
                    self.fail_transaction("Insufficient funds")
        except Exception as e:
            self.fail_transaction(str(e))  # In case of failure, mark the transaction as failed
            logger.error(f"Transaction error: {str(e)}")

    def fail_transaction(self, reason):
        """Marks the transaction as failed and logs the reason."""
        self.status = 'failed'
        self.save()

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
