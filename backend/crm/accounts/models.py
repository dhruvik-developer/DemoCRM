from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import CustomUserManager
from uuid import uuid4
from django.contrib.auth.models import Permission
from django.core.validators import RegexValidator


# Create your models here.


class Role(models.Model):
    role_id = models.AutoField(primary_key=True, editable=False)
    rolename = models.CharField(max_length=13, unique=True, blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.rolename


class CustomUser(AbstractUser):
    user_id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    username = models.CharField(max_length=100)
    email = models.EmailField(unique=True, blank=False, null=False)
    phone_number = models.CharField(
        max_length=10,
        unique=True,
        blank=False,
        null=False,
        validators=[
            RegexValidator(
                regex=r"^\d{10}$", message="Phone number must be exactly 10 digits."
            )
        ],
    )
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, blank=True, null=True)
    must_change_password = models.BooleanField(
        default=False,
        help_text="True when the user must change password on next login (first login after admin creation).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # passowrd field is coming from AbstractUser

    objects = CustomUserManager()  # Use the custom user manager

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class PasswordResetOTP(models.Model):
    """One-time OTP code for password reset. Only the SHA-256 hash is stored."""

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="password_reset_otps"
    )
    otp_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "password_reset_otp"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_used", "expires_at"]),
        ]

    def __str__(self):
        return f"OTP for {self.user.email} (used={self.is_used})"
