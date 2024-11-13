from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import create_roles

@receiver(post_migrate)
def create_default_roles(sender, **kwargs):
    create_roles()
