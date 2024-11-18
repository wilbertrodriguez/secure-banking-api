from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Transaction, UserProfile
from django.db import transaction


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'email']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password']
        )
        UserProfile.objects.get_or_create(user=user)  # Ensure profile is created
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
        """Validate sender, receiver, and transaction conditions."""
        sender = attrs.get('sender')
        receiver = attrs.get('receiver')
        amount = attrs.get('amount')

        # Check that sender is not the receiver
        if sender == receiver:
            raise serializers.ValidationError("You cannot send funds to yourself.")

        # Safely retrieve user profiles
        sender_profile = sender.profile if hasattr(sender, 'profile') else None
        receiver_profile = receiver.profile if hasattr(receiver, 'profile') else None

        if not sender_profile or not receiver_profile:
            raise serializers.ValidationError("Both sender and receiver must have associated profiles.")

        # Check if the sender has enough balance
        if sender_profile.balance < amount:
            raise serializers.ValidationError("You do not have enough balance to complete this transaction.")

        return attrs

    def create(self, validated_data):
        """Create the transaction and update user balances."""
        sender = validated_data['sender']
        receiver = validated_data['receiver']
        amount = validated_data['amount']

        # Create the transaction record with 'pending' status initially
        transaction = Transaction.objects.create(
            sender=sender,
            receiver=receiver,
            amount=amount,
            status='pending'  # Pending until balances are updated
        )

        # Call the model's method to process the transaction
        transaction.complete_transaction()

        return transaction
