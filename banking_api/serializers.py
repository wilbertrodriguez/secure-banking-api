from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Transaction, UserProfile
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

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
        #status = validated_data.get('status', 'pending')

        try:
            sender_profile = UserProfile.objects.get(user=sender)
            receiver_profile = UserProfile.objects.get(user=receiver)
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError("One or both users do not have associated profiles.")

        logger.debug(f"Before transaction - Sender balance: {sender_profile.balance}")
        logger.debug(f"Before transaction - Receiver balance: {receiver_profile.balance}")

        # Use a database transaction to ensure atomicity
        with transaction.atomic():
            # Check balance before deducting
            if sender_profile.balance < amount:
                raise serializers.ValidationError("Insufficient balance for the sender.")
            
            # Deduct balance from sender and add to receiver
            sender_profile.balance -= amount
            sender_profile.save()
            receiver_profile.balance += amount
            receiver_profile.save()
            print(sender_profile.balance)
            print(receiver_profile.balance)

            # Create the transaction and mark it as completed
            transaction_inst = Transaction.objects.create(
                sender=sender,
                receiver=receiver,
                amount=amount,
                status='completed'
                #status=status  # Marking status as 'completed'
            )
            print(transaction_inst)

            logger.debug(f"After transaction - Sender balance: {sender_profile.balance}")
            logger.debug(f"After transaction - Receiver balance: {receiver_profile.balance}")

            # After atomic block, check if changes were applied
            updated_sender_profile = UserProfile.objects.get(user=sender)
            updated_receiver_profile = UserProfile.objects.get(user=receiver)

            logger.debug(f"Updated Sender balance: {updated_sender_profile.balance}")
            logger.debug(f"Updated Receiver balance: {updated_receiver_profile.balance}")


            return transaction_inst