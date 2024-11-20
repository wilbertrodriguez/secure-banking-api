from decimal import Decimal, InvalidOperation
from django.contrib.auth.models import Group, User
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from django.db import transaction as db_transaction
from django.db.models import F, Q
from .serializers import RegisterSerializer, TransactionSerializer
from .models import Transaction, UserProfile
import logging
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
logger = logging.getLogger(__name__)

class RegisterView(APIView):
    def post(self, request):
        """
        Registers a new user, adds them to the 'User' group, and returns a success message.
        """
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user_group, created = Group.objects.get_or_create(name='User')
            user.groups.add(user_group)
            logger.info(f"User {user.username} registered and added to 'User' group.")
            return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)
        
        logger.warning("User registration failed due to validation errors.")
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
        """
        Endpoint for admins only.
        """
        return Response({"message": "Welcome, Admin!"}, status=status.HTTP_200_OK)


class AccountInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Retrieves the account information for the authenticated user.
        """
        if request.user.groups.filter(name='User').exists():
            return Response({"message": f"Welcome, {request.user.username}!"})
        return Response({"message": "Unauthorized access"}, status=403)

class TransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles the creation of a transaction between users and performs the necessary checks.
        """
        serializer = TransactionSerializer(data=request.data)

        if serializer.is_valid():
            # Save the transaction first
            transaction = serializer.save()

            # Try to complete the transaction and update the transaction status
            try:
                #transaction.complete_transaction()
                logger.info(f"Transaction completed successfully for {transaction.sender} to {transaction.receiver}")
                return Response({
                    "status": "success",
                    "data": {
                        "message": "Transaction successful",
                        "transaction": TransactionSerializer(transaction).data
                    }
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Transaction failed: {str(e)}")
                return Response({
                    "status": "failed",
                    "message": f"Transaction failed: {str(e)}"
                }, status=status.HTTP_400_BAD_REQUEST)

        # Log validation errors if serializer is invalid
        logger.warning(f"Transaction creation failed due to validation errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, transaction_id=None):
        """
        Retrieve a specific transaction by ID
        """
        if transaction_id:
            transaction = get_object_or_404(Transaction, id=transaction_id)
            return Response({
                'transaction': TransactionSerializer(transaction).data
            })
        else:
            transactions = Transaction.objects.filter(Q(sender=request.user) | Q(receiver=request.user))
            serializer = TransactionSerializer(transactions, many=True)
            return Response(serializer.data)
        
    def patch(self, request, transaction_id):
        """
        Partially update an existing transaction (only if not completed)
        """
        transaction = get_object_or_404(Transaction, id=transaction_id)
        print(transaction.status)

        # Prevent updates to completed transactions
        if transaction.status == 'completed':
            return Response({'error': 'Cannot update a completed transaction'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure that the status field cannot be modified unless explicitly desired
        if 'status' in request.data:
            return Response({'error': 'Cannot change the status of the transaction'}, status=status.HTTP_400_BAD_REQUEST)

        # Serialize and update the transaction with new data
        serializer = TransactionSerializer(transaction, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": "success",
                "data": serializer.data  # This includes the updated fields like amount
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, transaction_id):
        """
        Delete a transaction (only if not completed)
        """
        transaction = get_object_or_404(Transaction, id=transaction_id)

        if transaction.status == 'completed':
            return Response({'error': 'Cannot delete a completed transaction'}, status=status.HTTP_400_BAD_REQUEST)

        transaction.delete()
        return Response({"message": "Transaction deleted successfully"}, status=status.HTTP_204_NO_CONTENT)



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

class BalanceCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Retrieves the account balance for the authenticated user.
        """
        user = request.user
        try:
            user_profile = UserProfile.objects.get(user=user)
            return Response({
                'balance': str(user_profile.balance)
            })
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)
            