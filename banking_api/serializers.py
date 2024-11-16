from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Transaction, UserProfile
from django.db import transaction


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'email']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
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
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def create(self, validated_data):
        sender = validated_data['sender']
        receiver = validated_data['receiver']
        amount = validated_data['amount']

        sender_profile = sender.userprofile
        receiver_profile = receiver.userprofile

        if sender_profile.balance < amount:
            raise serializers.ValidationError("Insufficient balance for transaction.")

        # Use atomic block to ensure both profile updates and transaction creation happen atomically
        with transaction.atomic():
            transaction = Transaction.objects.create(
                sender=sender,
                receiver=receiver,
                amount=amount,
                status='pending'
            )
            sender_profile.balance -= amount
            receiver_profile.balance += amount
            sender_profile.save()
            receiver_profile.save()

        return transaction
