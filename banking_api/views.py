from decimal import Decimal, InvalidOperation
from django.contrib.auth.models import Group, User
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from rest_framework.response import Response
from django.conf import settings
from django.core.mail import send_mail
from banking_api.utils import send_otp_email
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from django.db import transaction as db_transaction
from django.db.models import F, Q
from .serializers import RegisterSerializer, TransactionSerializer
from .models import Transaction, UserProfile
import logging, random
from rest_framework.decorators import action
from rest_framework.decorators import permission_classes
from django.utils.timezone import now
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta
from .utils import generate_otp, send_otp_email, store_otp
logger = logging.getLogger(__name__)
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone


class RegisterView(APIView):
    def post(self, request):
        """
        Registers a new user, adds them to the 'User' group, generates and sends an OTP, and returns a success message.
        """
        email = request.data.get("email")
        
        # Check if a user with the provided email already exists
        if User.objects.filter(email=email).exists():
            logger.warning(f"User with email {email} already exists.")
            return Response({"error": "A user with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate and create user if email doesn't exist
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Save the user
                user = serializer.save()

                # Add user to the 'User' group
                user_group, created = Group.objects.get_or_create(name='User')
                user.groups.add(user_group)
                
                # Generate OTP, send it via email, and store it in the user's profile
                otp = generate_otp()
                send_otp_email(user.email, otp)
                store_otp(user, otp)
                
                # Log successful registration
                logger.info(f"User {user.username} registered and added to 'User' group.")
                
                # Return the response with a success message and inform the user to verify OTP
                return Response({
                    "message": "User registered successfully. Check your email for the OTP to verify your account.",
                    "user": {"username": user.username, "email": user.email}
                }, status=status.HTTP_201_CREATED)
            
            except Exception as e:
                logger.error(f"Error during user registration: {str(e)}")
                return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Log validation errors
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

class VerifyOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Verifies the OTP entered by the user.
        """
        otp = request.data.get("otp")
        user = request.user  # Authenticated via JWT or session

        if not otp:
            logger.warning(f"OTP missing for user {user.username}")
            return Response({"error": "OTP is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the user's profile
        try:
            profile = user.profile  # Assuming OneToOneField with related_name='profile'
        except AttributeError:
            logger.error(f"Profile not found for user {user.username}")
            return Response({"error": "Profile not found."}, status=status.HTTP_400_BAD_REQUEST)


        # Validate the OTP
        if profile.otp == otp:
            if now() < profile.otp_expiration:
                # OTP is valid
                logger.info(f"OTP verified successfully for user {user.username}")
                profile.otp = None  # Clear OTP
                profile.otp_expiration = None  # Clear expiration
                profile.save()
                return Response({"message": "OTP verified successfully!"}, status=status.HTTP_200_OK)
            else:
                logger.warning(f"OTP expired for user {user.username}")
                return Response({"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            logger.info(f"Invalid OTP entered for user {user.username}")
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)
        

class LoginView(APIView):
    def post(self, request):
        """
        Handles login with multi-factor authentication (MFA).
        If MFA is enabled, it sends an OTP for verification.
        """
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({"error": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Authenticate user using email
        try:
            user = authenticate(request, email=email, password=password)
        except Exception as e:
            return Response({"error": "Authentication failed."}, status=status.HTTP_400_BAD_REQUEST)

        if not user:
            return Response({"error": "Invalid email or password."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if MFA is enabled
        try:
            user_profile = user.profile
            if user_profile.mfa_enabled:
                if user_profile.otp and now() < user_profile.otp_expiration:
                    # OTP already exists and is valid, send it again
                    send_otp_email(user.email, user_profile.otp)  # Send the existing OTP
                else:
                    otp = generate_otp()  # Generate new OTP if none exists or expired
                    send_otp_email(user.email, otp)  # Send new OTP
                    store_otp(user, otp)  # Store new OTP in the profile
                
                return Response({
                    "message": "Login successful. Check your email for the OTP to complete the login process.",
                    "mfa_required": True,
                }, status=status.HTTP_200_OK)
            
            # If no MFA is required, generate token
            token = RefreshToken.for_user(user)
            return Response({
                "message": "Login successful.",
                "access_token": str(token.access_token),
                "refresh_token": str(token),
            }, status=status.HTTP_200_OK)
        
        except UserProfile.DoesNotExist:
            return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)

class VerifyLoginOTPView(APIView):
    def post(self, request):
        """
        Verifies OTP for completing the login process.
        """
        otp = request.data.get("otp")
        user = request.user  # Authenticated via JWT or session

        if not otp:
            logger.warning(f"OTP missing for user {user.username}")
            return Response({"error": "OTP is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the user profile
        try:
            profile = user.profile  # Ensure profile exists
        except UserProfile.DoesNotExist:
            logger.error(f"Profile not found for user {user.username}")
            return Response({"error": "Profile not found."}, status=status.HTTP_400_BAD_REQUEST)
        # Check if the OTP matches and if it's not expired
        if profile.otp == otp:
            if timezone.now() < profile.otp_expiration:
                # OTP valid, proceed to login
                profile.otp = None  # Clear OTP after successful verification
                profile.otp_expiration = None  # Clear expiration
                profile.save()

                # Generate new JWT token
                token = RefreshToken.for_user(user)
                logger.info(f"User {user.username} successfully verified OTP and logged in.")
                return Response({
                    "message": "OTP verified successfully!",
                    "access_token": str(token.access_token),
                    "refresh_token": str(token),
                }, status=status.HTTP_200_OK)
            else:
                logger.warning(f"OTP expired for user {user.username}")
                return Response({"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            logger.info(f"Invalid OTP entered for user {user.username}")
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)
            