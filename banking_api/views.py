from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import RegisterSerializer
from django.contrib.auth.models import User
from rest_framework.permissions import BasePermission

class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Check if the 'User' group exists
            try:
                user_group = Group.objects.get(name='User')
                user.groups.add(user_group)
            except Group.DoesNotExist:
                return Response({"message": "Group 'User' does not exist"}, status=status.HTTP_400_BAD_REQUEST)
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