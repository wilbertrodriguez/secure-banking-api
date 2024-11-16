from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth.models import Group, User
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction as db_transaction
from django.db.models import F, Q
from .serializers import RegisterSerializer, TransactionSerializer
from .models import Transaction, UserProfile

class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Check if the 'User' group exists, or create it
            user_group, created = Group.objects.get_or_create(name='User')
            user.groups.add(user_group)
            return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IsAdmin(BasePermission):
    """
    Custom permission to only allow admins to access certain endpoints.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff  # Checks if the user is an admin (staff member)


class AdminOnlyView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        return Response({"message": "Welcome, Admin!"}, status=status.HTTP_200_OK)


class AccountInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.groups.filter(name='User').exists():
            return Response({"message": f"Welcome, {request.user.username}!"})
        return Response({"message": "Unauthorized access"}, status=403)


class TransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sender = request.user
        receiver_id = request.data.get('receiver_id')
        amount = request.data.get('amount')

        # Validate input
        if not receiver_id or not amount or float(amount) <= 0:
            return Response({"error": "Invalid receiver or amount"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return Response({"error": "Receiver does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if sender == receiver:
            return Response({"error": "Sender and receiver cannot be the same"}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the sender has a profile and valid balance
        try:
            sender_profile = sender.profile
        except UserProfile.DoesNotExist:
            return Response({"error": "Sender profile not found. Please create a profile."}, status=status.HTTP_400_BAD_REQUEST)

        # Handle the transaction in an atomic block to ensure integrity
        try:
            with db_transaction.atomic():
                # Check if sender has sufficient balance
                if sender_profile.balance < float(amount):
                    return Response({"error": "Insufficient balance"}, status=status.HTTP_400_BAD_REQUEST)

                # Update balances atomically
                sender_profile.balance = F('balance') - float(amount)
                receiver_profile = receiver.profile
                receiver_profile.balance = F('balance') + float(amount)
               
                # Save the updated profiles
                sender_profile.save()
                receiver_profile.save()

                # Create the transaction record
                transaction_data = {
                    "sender": sender.id,
                    "receiver": receiver.id,
                    "amount": amount,
                    "status": "completed"
                }
                serializer = TransactionSerializer(data=transaction_data)
                if serializer.is_valid():
                    serializer.save()  # Save the transaction record
                    return Response({"message": "Transaction successful", "transaction": serializer.data}, status=status.HTTP_201_CREATED)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Rollback changes if any exception occurs
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TransactionHistoryPagination(PageNumberPagination):
    page_size = 10  # Adjust the page size as needed
    page_size_query_param = 'page_size'
    max_page_size = 100


class TransactionHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get the transaction history for the authenticated user.
        """
        user = request.user
        transactions = Transaction.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).select_related('sender', 'receiver').order_by('-date')

        # Apply pagination
        paginator = TransactionHistoryPagination()
        paginated_transactions = paginator.paginate_queryset(transactions, request)

        serializer = TransactionSerializer(paginated_transactions, many=True)
        return paginator.get_paginated_response(serializer.data)
