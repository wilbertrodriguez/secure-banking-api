from cryptography.fernet import Fernet
from django.conf import settings

cipher = Fernet(settings.SECURITY_KEY)

def encrypt_data(data):
    return cipher.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data):
    return cipher.decrypt(encrypted_data.encode()).decode()