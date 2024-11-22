from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Transaction, UserProfile
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
import logging

logger = logging.getLogger(__name__)

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[MinLengthValidator(8)])  # Enforcing a minimum length for password

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def validate_email(self, value):
        # Check if the email is already in use
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        # Add more password validations (e.g., password strength)
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("Password must contain at least one digit.")
        if not any(char.isalpha() for char in value):
            raise serializers.ValidationError("Password must contain at least one letter.")
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
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate(self, attrs):
        sender = attrs.get('sender')
        receiver = attrs.get('receiver')
        amount = attrs.get('amount')

        logger.debug(f"Validating transaction - sender: {sender}, receiver: {receiver}, amount: {amount}")

        if sender == receiver:
            raise serializers.ValidationError("You cannot send funds to yourself.")

        sender_profile = getattr(sender, 'profile', None)
        receiver_profile = getattr(receiver, 'profile', None)

        logger.debug(f"Sender profile: {sender_profile}, Receiver profile: {receiver_profile}")

        if not sender_profile:
            raise serializers.ValidationError("The sender must have an associated profile.")
        if not receiver_profile:
            raise serializers.ValidationError("The receiver must have an associated profile.")

        if sender_profile.balance < amount:
            raise serializers.ValidationError("You do not have enough balance to complete this transaction.")

        return attrs

    def create(self, validated_data):
        sender = validated_data['sender']
        receiver = validated_data['receiver']
        amount = validated_data['amount']

        # Log the initiation of the transaction
        logger.debug(f"Creating transaction from {sender.username} to {receiver.username} for amount {amount}")

        # Delegate the transaction creation to the model
        try:
            transaction_instance = Transaction.create_transaction(sender, receiver, amount)
        except ValueError as e:
            logger.error(f"Error creating transaction: {e}")
            raise serializers.ValidationError(str(e))
    
        transaction_instance.complete_transaction()

        return transaction_instance
