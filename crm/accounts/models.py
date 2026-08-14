from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import CustomUserManager
from uuid import uuid4
from django.contrib.auth.models import Permission 


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
    phone_number = models.CharField(max_length=10, unique=True, blank=False, null=False)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # passowrd field is coming from AbstractUser 
    
    objects = CustomUserManager()  # Use the custom user manager

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email 