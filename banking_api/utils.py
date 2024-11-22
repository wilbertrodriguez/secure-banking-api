import random
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta
from .models import UserProfile
from django.utils.timezone import now
import logging

logger = logging.getLogger(__name__)

def generate_otp():
    otp = random.randint(100000, 999999)
    logger.info(f"Generated OTP: {otp}")
    return otp

def send_otp_email(user_email, otp):
    subject = "Your OTP Code"
    message = f"Your OTP code is {otp}. It will expire in 10 minutes."
    from_email = settings.DEFAULT_FROM_EMAIL

    try:
        send_mail(subject, message, from_email, [user_email])  # Send OTP email only once
        logger.info(f"OTP email sent to {user_email}")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {user_email}: {str(e)}")
        raise

def store_otp(user, otp):
    profile, created = UserProfile.objects.get_or_create(user=user)
    profile.otp = otp
    profile.otp_expiration = now() + timedelta(minutes=10)
    profile.save()
    profile.refresh_from_db()
    logger.info(f"Stored OTP for user {user.username}")