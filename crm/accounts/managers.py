from django.contrib.auth.models import BaseUserManager
from django.apps import apps
from django.contrib.auth.models import Permission


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        Role = apps.get_model("accounts", "Role")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        user = self.create_user(
            email=email, username=username, password=password, **extra_fields
        )

        # Assign Admin role automatically, creating if it doesn't exist
        admin_role, _ = Role.objects.get_or_create(rolename="Admin")

        user.role = admin_role
        user.save(using=self._db)

        admin_role.permissions.set(Permission.objects.all())

        return user
