from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Role, PasswordResetOTP


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("role_id", "rolename", "created_at", "updated_at")
    search_fields = ("rolename",)
    filter_horizontal = ("permissions",)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "user_id",
        "email",
        "username",
        "phone_number",
        "role",
        "is_staff",
        "is_active",
        "created_at",
    )
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("email", "username", "phone_number")
    ordering = ("email",)
    readonly_fields = ("user_id", "created_at", "updated_at")
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("username", "phone_number", "role")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login",)}),
        ("Metadata", {"fields": ("user_id", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "phone_number",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "created_at",
        "expires_at",
        "is_used",
        "attempts",
    )
    list_filter = ("is_used",)
    search_fields = ("user__email",)
    readonly_fields = ("otp_hash", "created_at", "expires_at")
