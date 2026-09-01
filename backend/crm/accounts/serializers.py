from rest_framework import serializers
from accounts.models import CustomUser, Role
from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ["user_id", "username", "email", "phone_number", "password"]
        read_only_fields = ["user_id"]

    def create(self, validated_data):
        employee_role = Role.objects.filter(rolename="Employee").first()

        user = CustomUser.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            phone_number=validated_data["phone_number"],
            password=validated_data["password"],
            role=employee_role,
        )
        # GitLab-style invite: new users must change temp password on first login
        user.must_change_password = True
        user.save(update_fields=["must_change_password"])

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class LogOutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()

    def validate_refresh_token(self, value):
        if not value:
            raise serializers.ValidationError("Refresh token is required.")
        return value


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True, validators=[validate_password]
    )


class ProfileSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(
        source="role.rolename", read_only=True, default=None
    )

    class Meta:
        model = CustomUser
        fields = [
            "user_id",
            "username",
            "email",
            "phone_number",
            "role",
            "role_name",
            "must_change_password",
            "created_at",
            "updated_at",
        ]


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(), many=True, required=False
    )

    class Meta:
        model = Role
        fields = "__all__"
        read_only_fields = ["role_id", "created_at", "updated_at"]


class RoleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["role_id", "rolename", "description", "permissions"]


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "content_type"]
        read_only_fields = ["id"]


# ==========================================================
# FORGOT / RESET PASSWORD SERIALIZERS (new - existing code untouched)
# ==========================================================


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(
        write_only=True, validators=[validate_password]
    )
