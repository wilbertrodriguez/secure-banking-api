from django.db import models
from django.contrib.auth import get_user_model
import logging
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from decimal import Decimal
from django.db.models import F

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
