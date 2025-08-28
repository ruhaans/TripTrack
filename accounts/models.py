#accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings


class User(AbstractUser):
    """
    Custom user model that:
    - Enforces unique, indexed email
    - Normalizes email casing/whitespace on save
    - Keeps username for compatibility with Django admin/templates
    """

    email = models.EmailField(unique=True, db_index=True)
    email_verified = models.BooleanField(default=False)
    

    # When creating a superuser via createsuperuser, Django will prompt for these:
    # (username is already required by AbstractUser)
    REQUIRED_FIELDS = ["email"]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        # Prefer username when present; fall back to email for clarity
        return self.username or self.email


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    first_name = models.CharField(max_length=50, blank=True)
    last_name  = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)   # store digits only (no +91)
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Profile({self.user.username or self.user.email})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)