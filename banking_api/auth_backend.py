from django.contrib.auth.models import User
from django.contrib.auth.backends import BaseBackend
from django.core.exceptions import ObjectDoesNotExist

class EmailBackend(BaseBackend):
    """
    Custom authentication backend that allows login using email instead of username.
    """

    def authenticate(self, request, email=None, password=None, **kwargs):
        """
        Authenticate the user based on the provided email and password.
        """
        try:
            # Look for the user by email address
            user = User.objects.get(email=email)
            # Check if the password is correct
            if user.check_password(password):
                return user
            else:
                return None
        except ObjectDoesNotExist:
            return None