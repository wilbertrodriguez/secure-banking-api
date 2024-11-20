from django.db import models
from django.contrib.auth import get_user_model
import logging
from django.db.models import F
from decimal import Decimal
from django.db import transaction

logger = logging.getLogger(__name__)

User = get_user_model()

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username}'s profile"

    def save(self, *args, **kwargs):
        # Log when balance is updated
        if self.pk:
            logger.info(f"Updating profile for user {self.user.username} with new balance {self.balance}")
        else:
            logger.info(f"Creating profile for user {self.user.username} with initial balance {self.balance}")
        super().save(*args, **kwargs)


class Transaction(models.Model):
    sender = models.ForeignKey(User, related_name='sent_transactions', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_transactions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')],
        default='pending'
    )

    def __str__(self):
        return f"Transaction from {self.sender.username} to {self.receiver.username} for {self.amount}"

    @classmethod
    def create_transaction(cls, sender, receiver, amount):
        """
        Handles transaction creation and balance updates for sender and receiver.
        Ensures that balances are checked and updated atomically.
        """
        logger.debug(f"Creating transaction from {sender.username} to {receiver.username} for amount {amount}")

        try:
            sender_profile = sender.profile
            receiver_profile = receiver.profile
        except UserProfile.DoesNotExist:
            logger.error("One or both users do not have profiles.")
            raise ValueError("One or both users do not have profiles.")

        if sender_profile.balance < amount:
            logger.error(f"Insufficient balance for sender {sender.username}.")
            raise ValueError("Insufficient balance for sender.")

        # Use a transaction to update the profiles atomically
        with transaction.atomic():
            # Deduct from sender and add to receiver
            sender_profile.balance -= amount
            receiver_profile.balance += amount

            # Save profiles
            sender_profile.save()
            receiver_profile.save()

            # Log the successful balance update
            logger.info(f"Transaction complete. {sender.username}'s new balance: {sender_profile.balance}, {receiver.username}'s new balance: {receiver_profile.balance}")

            # Create the transaction record
            transaction_instance = cls.objects.create(
                sender=sender,
                receiver=receiver,
                amount=amount,
                status='pending'  # initially set to pending
            )

            return transaction_instance
        
    def complete_transaction(self):
        # Check if the transaction is still in pending status
        if self.status != 'pending':
            logger.warning(f"Transaction {self.id} is not pending, it is already {self.status}.")
            return False
        
        # Change status to 'completed'
        self.status = 'completed'
        self.save()

        # Log the status change
        logger.info(f"Transaction {self.id} from {self.sender.username} to {self.receiver.username} marked as completed.")

        return True
