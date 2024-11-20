from decimal import Decimal, InvalidOperation
from django.contrib.auth.models import Group, User
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction as db_transaction
from django.db.models import F, Q
from .serializers import RegisterSerializer, TransactionSerializer
from .models import Transaction, UserProfile
import logging

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
        serializer = TransactionSerializer(data=request.data)
        print(serializer)
        if serializer.is_valid():
            transaction = serializer.save()
            logger.info(f"Transaction created successfully for {transaction.sender} to {transaction.receiver}")
            return Response({
                "status": "success",
                "data": {
                    "message": "Transaction successful",
                    "transaction": serializer.data
                }
            }, status=status.HTTP_201_CREATED)

        logger.warning("Transaction creation failed due to validation errors.")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



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
