from django.contrib.auth.models import AbstractUser
from django.db import models


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
