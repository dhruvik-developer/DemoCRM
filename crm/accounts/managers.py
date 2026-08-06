from django.contrib.auth.models import BaseUserManager
from django.apps import apps

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

        # Assign Admin role automatically
        admin_role = Role.objects.get(rolename="Admin")
        extra_fields["role"] = admin_role


        return self.create_user(email, username, password, **extra_fields)