from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """
    Custom permission to grant access only to Admin users.
    """

    def has_permission(self, request, view):
        return request.user.groups.filter(name='Admin').exists()
