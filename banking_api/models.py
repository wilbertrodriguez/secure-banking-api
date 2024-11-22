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
    otp = models.CharField(max_length=6, blank=True, null=True)  # Store OTP
    otp_expiration = models.DateTimeField(null=True, blank=True)  # Store expiration time

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
        logger.debug(f"Attempting transaction: Sender: {sender.username}, Receiver: {receiver.username}, Amount: {amount}")

        # Ensure the amount is a Decimal for precise calculations
        if not isinstance(amount, Decimal):
            try:
                amount = Decimal(str(amount))
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid amount provided: {amount}")
                raise ValueError("Amount must be a valid number.") from e

        try:
            sender_profile = sender.profile
            receiver_profile = receiver.profile
        except UserProfile.DoesNotExist as e:
            logger.error(f"Profile retrieval error: {e}")
            raise ValueError("One or both users do not have profiles.") from e

        if sender_profile.balance < amount:
            logger.error(f"Insufficient balance for sender {sender.username}. Current balance: {sender_profile.balance}")
            raise ValueError("Insufficient balance for sender.")

        logger.info(f"Initiating transaction: {sender.username} -> {receiver.username} | Amount: {amount}")

        # Perform the transaction atomically
        with transaction.atomic():
            # Update balances
            sender_profile.balance -= amount
            receiver_profile.balance += amount

            # Save updates
            sender_profile.save()
            receiver_profile.save()

            # Log updated balances
            logger.info(f"Updated balances: Sender {sender.username}: {sender_profile.balance}, Receiver {receiver.username}: {receiver_profile.balance}")

            # Create transaction record
            transaction_instance = cls.objects.create(
                sender=sender,
                receiver=receiver,
                amount=amount,
                status='pending'  # Transaction status can later be updated to 'completed'
            )

            logger.info(f"Transaction record created: {transaction_instance.id}")
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
