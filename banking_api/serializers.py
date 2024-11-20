from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Transaction, UserProfile
from django.db import transaction


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

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
    print("serial transactionserial ", sender, receiver, amount)

    class Meta:
        model = Transaction
        fields = ['id', 'sender', 'receiver', 'amount', 'date', 'status']
        read_only_fields = ['id', 'date', 'status']

    def validate_amount(self, value):
        print("serial validate_amount ", value)
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate(self, attrs):
        print("serial validate attrs ", attrs)
        sender = attrs.get('sender')
        receiver = attrs.get('receiver')
        amount = attrs.get('amount')
        print("serial validate ", sender, receiver, amount)
    

        if sender == receiver:
            raise serializers.ValidationError("You cannot send funds to yourself.")

        # Retrieve user profiles if they exist
        #sender_profile = getattr(sender, 'profile')
        #receiver_profile = getattr(receiver, 'profile')
        sender_profile = UserProfile.objects.get(user=sender)
        receiver_profile = UserProfile.objects.get(user=receiver)

        print("serial validate1 sender ", sender_profile.user.id)
        print("serial validate1 receiver", receiver_profile.user.id)

        if not sender_profile:
            raise serializers.ValidationError("The sender must have an associated profile.")
        if not receiver_profile:
            raise serializers.ValidationError("The receiver must have an associated profile.")

        # Check if sender has enough balance
        if sender_profile.balance < amount:
            print("serial validate2 sender ", sender_profile.balance)
            print("serial validate2 receiver", receiver_profile.balance)
            raise serializers.ValidationError("You do not have enough balance to complete this transaction.")

        return attrs

    def create(self, validated_data):
        sender = validated_data['sender']
        receiver = validated_data['receiver']
        amount = validated_data['amount']

        # Create and complete the transaction using the model's method
        transaction = Transaction.objects.create(
            sender=sender,
            receiver=receiver,
            amount=amount,
            status='pending'
        )
        transaction.complete_transaction()  # Ensure the logic is in the model

        return transaction
