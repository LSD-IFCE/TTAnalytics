from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import ensure_profile_for_user

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Garante perfil para usuários novos e salva perfis existentes."""
    profile = ensure_profile_for_user(instance)
    profile.save()