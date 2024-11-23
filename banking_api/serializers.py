from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Transaction, UserProfile
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, EmailValidator
from django.contrib.auth import password_validation
from django.utils.html import strip_tags
import re
import logging

logger = logging.getLogger(__name__)

# Custom function to sanitize input (e.g., strip HTML tags or special characters)
def sanitize_input(value):
    # Removing any HTML tags to prevent XSS attacks
    return strip_tags(value)

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[MinLengthValidator(8)])  # Enforcing a minimum length for password

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def validate_username(self, value):
        # Sanitize username to remove any special characters or HTML tags
        value = sanitize_input(value)

        # Ensure the username only contains alphanumeric characters and underscores
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise serializers.ValidationError("Username can only contain letters, numbers, and underscores.")
        
        # Check if the username is already in use
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        
        return value

    def validate_email(self, value):
        # Sanitize email to prevent malicious input (e.g., HTML)
        value = sanitize_input(value)

        # Validate proper email format
        email_validator = EmailValidator()
        try:
            email_validator(value)
        except ValidationError:
            raise serializers.ValidationError("Enter a valid email address.")
        
        # Check if the email is already in use
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        
        return value

    def validate_password(self, value):
        # Sanitize password input
        value = sanitize_input(value)

        # Check if the password is strong enough
        try:
            password_validation.validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        # Custom password strength check: Must include at least one letter and one number
        if not re.search(r'[A-Za-z]', value):
            raise serializers.ValidationError("Password must contain at least one letter.")
        if not re.search(r'\d', value):
            raise serializers.ValidationError("Password must contain at least one number.")

        return value

    def create(self, validated_data):
        # Create user with hashed password
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password']
        )
        # Create UserProfile or ensure it exists
        UserProfile.objects.get_or_create(user=user)
        return user


class TransactionSerializer(serializers.ModelSerializer):
    sender = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    receiver = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = Transaction
        fields = ['id', 'sender', 'receiver', 'amount', 'date', 'status']
        read_only_fields = ['id', 'date', 'status']

    def validate_amount(self, value):
        """Validate that the transaction amount is greater than zero."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate(self, attrs):
        """Ensure that the transaction is valid (e.g., sender and receiver are different, sufficient balance)."""
        sender = attrs.get('sender')
        receiver = attrs.get('receiver')
        amount = attrs.get('amount')

        logger.debug(f"Validating transaction - sender: {sender}, receiver: {receiver}, amount: {amount}")

        # Prevent users from sending funds to themselves
        if sender == receiver:
            raise serializers.ValidationError("You cannot send funds to yourself.")

        # Retrieve user profiles for sender and receiver
        sender_profile = sender.profile if hasattr(sender, 'profile') else None
        receiver_profile = receiver.profile if hasattr(receiver, 'profile') else None

        logger.debug(f"Sender profile: {sender_profile}, Receiver profile: {receiver_profile}")

        # Ensure both sender and receiver have associated profiles
        if not sender_profile:
            raise serializers.ValidationError("The sender must have an associated profile.")
        if not receiver_profile:
            raise serializers.ValidationError("The receiver must have an associated profile.")

        # Ensure the sender has enough balance
        if sender_profile.balance < amount:
            raise serializers.ValidationError("You do not have enough balance to complete this transaction.")

        return attrs

    def create(self, validated_data):
        """Create the transaction instance and complete the transaction process."""
        sender = validated_data['sender']
        receiver = validated_data['receiver']
        amount = validated_data['amount']

        # Log the initiation of the transaction
        logger.debug(f"Creating transaction from {sender.username} to {receiver.username} for amount {amount}")

        try:
            # Create the transaction using a custom method on the model
            transaction_instance = Transaction.create_transaction(sender, receiver, amount)
        except ValueError as e:
            logger.error(f"Error creating transaction: {e} - Sender: {sender.username}, Receiver: {receiver.username}, Amount: {amount}")
            raise serializers.ValidationError(str(e))
        
        # Complete the transaction (e.g., update balances, finalize transaction status)
        transaction_instance.complete_transaction()

        # Log the completion of the transaction
        logger.debug(f"Transaction completed: {transaction_instance.id} - Amount: {amount} - Status: {transaction_instance.status}")

        return transaction_instance
