import logging
from pathlib import Path

from django.db import transaction


from .models import CustomUser, Role
from .serializers import (
    PermissionSerializer,
    ProfileSerializer,
    RefreshTokenSerializer,
    RegisterSerializer,
    LoginSerializer,
    LogOutSerializer,
    ChangePasswordSerializer,
    RoleListSerializer,
    RoleSerializer,
)
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken  # type: ignore
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Permission
from .permissions import HasDynamicPermission
from rest_framework_simplejwt.exceptions import TokenError
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.utils import timezone

from .models import PasswordResetOTP
from .serializers import ForgotPasswordSerializer, ResetPasswordSerializer
from .tasks import send_password_reset_otp_email

import os
from dotenv import load_dotenv

from .rate_limiter import is_locked, record_failure, reset, unlock as limiter_unlock


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR.parent / ".env")

OTP_LENGTH = int(os.getenv("OTP_LENGTH", "6"))
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "5"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "3"))


logger = logging.getLogger(__name__)


# Create your views here.
class RegisterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Register a new user (Admin/Manager only)",
        description="Create a new user account. Only Admin and Manager roles can register employees. The new user is assigned the Employee role and must change password on first login. Authentication required.",
        tags=["Accounts"],
        operation_id="register_create",
        request=RegisterSerializer,
        responses={
            201: inline_serializer(
                "RegisterSuccessResponse",
                fields={
                    "user_id": serializers.UUIDField(),
                    "username": serializers.CharField(),
                    "email": serializers.EmailField(),
                    "message": serializers.CharField(),
                },
            ),
            400: inline_serializer(
                "RegisterErrorResponse",
                fields={"error": serializers.CharField()},
            ),
            401: inline_serializer(
                "RegisterUnauthorizedResponse",
                fields={"detail": serializers.CharField()},
            ),
            403: inline_serializer(
                "RegisterForbiddenResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request):
        # Only Admin and Manager (and superuser) can register new employees
        if request.user.is_superuser:
            pass
        elif request.user.role is None or request.user.role.rolename not in [
            "Admin",
            "Manager",
        ]:
            logger.warning(
                "Unauthorized register attempt by user %s with role %s",
                getattr(request.user, "user_id", request.user),
                getattr(getattr(request.user, "role", None), "rolename", None),
            )
            return Response(
                {"error": "Only Admin and Manager can register new employees."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RegisterSerializer(data=request.data)
        # breakpoint()

        if serializer.is_valid():
            try:
                serializer.save()
                logger.info(
                    "User registered successfully: %s (ID: %s) by %s",
                    serializer.data["email"],
                    serializer.data["user_id"],
                    getattr(request.user, "email", "unknown"),
                )
                return Response(
                    {
                        "user_id": serializer.data["user_id"],
                        "username": serializer.data["username"],
                        "email": serializer.data["email"],
                        "message": "User registered successfully",
                    },
                    status=status.HTTP_201_CREATED,
                )

            except Exception as e:
                logger.exception("Failed user registration attempt")
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Log in and obtain JWT tokens",
        description="Authenticate with email and password. Returns access and refresh tokens. Includes must_change_password flag when the user must change password on first login.",
        tags=["Accounts"],
        operation_id="login_create",
        request=LoginSerializer,
        responses={
            200: inline_serializer(
                "LoginSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "refresh_token": serializers.CharField(),
                    "access_token": serializers.CharField(),
                    "must_change_password": serializers.BooleanField(),
                },
            ),
            401: inline_serializer(
                "LoginUnauthorizedResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data["email"]
            password = serializer.validated_data["password"]

            # ---- Login rate limiting --------------------------------------
            lock = is_locked(email)
            if lock.get("blocked"):
                if lock.get("reason") == "permanent":
                    return Response(
                        {
                            "error": "Account locked due to repeated failed login attempts.",
                            "code": "account_locked",
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
                retry_after = lock.get("retry_after", 0)
                minutes = max(1, round(retry_after / 60))
                return Response(
                    {
                        "error": (
                            "Too many failed login attempts. "
                            f"Please try again in {minutes} minute(s)."
                        ),
                        "code": "login_cooldown",
                        "retry_after": retry_after,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                user = None

            credentials_ok = (
                user is not None and user.is_active and user.check_password(password)
            )

            if not credentials_ok:
                result = record_failure(email)
                logger.warning(
                    "Failed login attempt for email: %s (remaining=%s)",
                    email,
                    result.get("remaining_attempts"),
                )
                if result.get("blocked"):
                    if result.get("reason") == "permanent":
                        return Response(
                            {
                                "error": "Account locked due to repeated failed login attempts.",
                                "code": "account_locked",
                            },
                            status=status.HTTP_403_FORBIDDEN,
                        )
                    retry_after = result.get("retry_after", 0)
                    minutes = max(1, round(retry_after / 60))
                    return Response(
                        {
                            "error": (
                                "Too many failed login attempts. "
                                f"Please try again in {minutes} minute(s)."
                            ),
                            "code": "login_cooldown",
                            "retry_after": retry_after,
                        },
                        status=status.HTTP_429_TOO_MANY_REQUESTS,
                    )
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # Reset rate-limit state on success
            reset(email)

            try:
                refresh = RefreshToken.for_user(user)
                # Add must_change_password to both refresh and access tokens for client-side detection
                refresh["must_change_password"] = bool(user.must_change_password)
                refresh.access_token["must_change_password"] = bool(
                    user.must_change_password
                )
            except Exception:
                logger.exception("Token generation failed for user %s", user.user_id)
                return Response(
                    {"error": "Failed to generate tokens. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            logger.info("User %s logged in successfully", user.user_id)

            return Response(
                {
                    "message": "Login successful",
                    "refresh_token": str(refresh),
                    "access_token": str(refresh.access_token),
                    "must_change_password": bool(user.must_change_password),
                }
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    permission_name = "logout"

    @extend_schema(
        summary="Log out and blacklist refresh token",
        description="Blacklist the given refresh token. Requires authentication.",
        tags=["Accounts"],
        operation_id="logout_create",
        request=LogOutSerializer,
        responses={
            200: inline_serializer(
                "LogoutSuccessResponse",
                fields={"message": serializers.CharField()},
            ),
            400: inline_serializer(
                "LogoutErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request):
        serializer = LogOutSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        refresh_token = serializer.validated_data["refresh_token"]

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {"message": f"Logout successful for {request.user.username}"},
                status=status.HTTP_200_OK,
            )

        except TokenError as e:
            if "blacklisted" in str(e).lower():
                return Response(
                    {"message": "You are already logged out."},
                    status=status.HTTP_200_OK,
                )

            return Response(
                {"error": "Invalid or expired refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception:
            logger.exception("Logout failed for user %s", request.user)
            return Response(
                {"error": "Logout failed. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RefreshTokenAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Refresh access token",
        description="Exchange a valid refresh token for a new access token.",
        tags=["Accounts"],
        operation_id="token_refresh_create",
        request=RefreshTokenSerializer,
        responses={
            200: inline_serializer(
                "RefreshTokenSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "access_token": serializers.CharField(),
                },
            ),
            400: inline_serializer(
                "RefreshTokenErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)

        if serializer.is_valid():
            refresh_token = serializer.validated_data["refresh_token"]

            try:
                token = RefreshToken(refresh_token)
                new_access_token = str(token.access_token)

                return Response(
                    {
                        "message": "Access token refreshed successfully",
                        "access_token": new_access_token,
                    },
                    status=status.HTTP_200_OK,
                )

            except Exception:
                return Response(
                    {"error": "Invalid refresh token"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change password",
        description="Change the authenticated user's password. Requires old_password and new_password.",
        tags=["Accounts"],
        operation_id="change_password_create",
        request=ChangePasswordSerializer,
        responses={
            200: inline_serializer(
                "ChangePasswordSuccessResponse",
                fields={"message": serializers.CharField()},
            ),
            400: inline_serializer(
                "ChangePasswordErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            old_password = serializer.validated_data["old_password"]
            new_password = serializer.validated_data["new_password"]

            user = request.user

            if not user.check_password(old_password):
                return Response(
                    {"error": "Old password is incorrect."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                user.set_password(new_password)
                # Clear forced password change flag — user has now set their own password
                if getattr(user, "must_change_password", False):
                    user.must_change_password = False
                user.save()
            except Exception:
                logger.exception("Password change failed for user %s", request.user)
                return Response(
                    {"error": "Failed to change password. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {"message": "Password changed successfully."}, status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="View user profile",
        description="Retrieve profile details of a user by UUID. Requires Admin/Manager role to view other users' profiles.",
        tags=["Accounts"],
        operation_id="profile_retrieve",
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="User UUID",
            ),
        ],
        responses={
            200: inline_serializer(
                "ProfileSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "profile": ProfileSerializer(),
                },
            ),
            403: inline_serializer(
                "ProfileForbiddenResponse",
                fields={"error": serializers.CharField()},
            ),
            404: inline_serializer(
                "ProfileNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def get(self, request, user_id):
        if request.user.user_id != user_id:
            if request.user.role is None or request.user.role.rolename not in [
                "Admin",
                "Manager",
            ]:
                return Response(
                    {"error": "Only Admin and Manager can view other profiles."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        user = get_object_or_404(CustomUser, user_id=user_id)

        serializer = ProfileSerializer(user)

        return Response(
            {"message": "Profile retrieved successfully.", "profile": serializer.data},
            status=status.HTTP_200_OK,
        )


class RoleListCreateAPIView(APIView):
    permission_classes = [HasDynamicPermission]
    permission_names = {
        "GET": "view_role",
        "POST": "add_role",
    }

    @extend_schema(
        summary="List all roles",
        description="Retrieve a list of all roles.",
        tags=["Accounts"],
        operation_id="role_list",
        responses={
            200: inline_serializer(
                "RoleListSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "roles": RoleListSerializer(many=True),
                },
            ),
            403: inline_serializer(
                "RoleListForbiddenResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def get(self, request):
        if request.user.role is None:
            return Response(
                {"error": "Role is not assigned."}, status=status.HTTP_403_FORBIDDEN
            )

        if request.user.role.rolename not in ["Admin", "Manager"]:
            return Response(
                {"error": "Only Admin and Manager can view roles."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            roles = Role.objects.prefetch_related("permissions").order_by("role_id")
            serializer = RoleListSerializer(roles, many=True)
        except Exception:
            logger.exception("Failed to retrieve roles")
            return Response(
                {"error": "Failed to retrieve roles. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "Roles retrieved successfully.", "roles": serializer.data},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Create a role",
        description="Create a new role.",
        tags=["Accounts"],
        operation_id="role_create",
        request=RoleSerializer,
        responses={
            201: inline_serializer(
                "RoleCreateSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "role": RoleSerializer(),
                },
            ),
            400: RoleSerializer,
        },
    )
    def post(self, request):
        serializer = RoleSerializer(data=request.data)

        if serializer.is_valid():
            try:
                serializer.save()
            except Exception:
                logger.exception(
                    "Failed to create role %s", request.data.get("rolename")
                )
                return Response(
                    {"error": "Failed to create role. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {"message": "Role created successfully.", "role": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RoleDetailAPIView(APIView):
    permission_classes = [HasDynamicPermission]
    permission_names = {
        "PUT": "change_role",
        "PATCH": "change_role",
        "DELETE": "delete_role",
    }

    @extend_schema(
        summary="Update a role",
        description="Update an existing role.",
        tags=["Accounts"],
        operation_id="role_update",
        parameters=[
            OpenApiParameter(
                name="role_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Role ID",
            ),
        ],
        request=RoleSerializer,
        responses={
            200: inline_serializer(
                "RoleUpdateSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "role": RoleSerializer(),
                },
            ),
            400: RoleSerializer,
            403: inline_serializer(
                "RoleUpdateForbiddenResponse",
                fields={"error": serializers.CharField()},
            ),
            404: inline_serializer(
                "RoleUpdateNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def put(self, request, role_id):
        role = get_object_or_404(Role, role_id=role_id)

        if role.rolename == "Admin":
            return Response(
                {"error": "Admin role cannot be updated."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RoleSerializer(role, data=request.data, partial=True)

        if serializer.is_valid():
            try:
                serializer.save()
            except Exception:
                logger.exception("Failed to update role %s", role.rolename)
                return Response(
                    {"error": "Failed to update role. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {"message": "Role updated successfully.", "role": serializer.data},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Sync permissions for a role",
        description="Sync permissions for a role — checked = granted, unchecked = removed. Send full desired permission id set; backend will set exactly that set (add + subtract).",
        tags=["Accounts"],
        operation_id="role_patch_permissions",
        parameters=[
            OpenApiParameter(
                name="role_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Role ID",
            ),
        ],
        request=inline_serializer(
            "RolePermissionPatchRequest",
            fields={
                "permissions": serializers.ListField(
                    child=serializers.IntegerField(), allow_empty=True
                ),
            },
        ),
        responses={
            200: inline_serializer(
                "RolePermissionPatchSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "role": RoleSerializer(),
                },
            ),
            400: inline_serializer(
                "RolePermissionPatchBadRequestResponse",
                fields={
                    "error": serializers.CharField(),
                },
            ),
            403: inline_serializer(
                "RolePermissionPatchForbiddenResponse",
                fields={
                    "error": serializers.CharField(),
                },
            ),
            404: inline_serializer(
                "RolePermissionPatchNotFoundResponse",
                fields={
                    "detail": serializers.CharField(),
                },
            ),
        },
    )
    def patch(self, request, role_id):
        role = get_object_or_404(Role, role_id=role_id)

        if role.rolename == "Admin":
            return Response(
                {"error": "Admin role cannot be updated."},
                status=status.HTTP_403_FORBIDDEN,
            )

        permission_ids = request.data.get("permissions")

        if permission_ids is None:
            return Response(
                {"error": "permissions is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(permission_ids, list):
            return Response(
                {"error": "permissions must be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        permissions = (
            Permission.objects.filter(id__in=permission_ids) if permission_ids else []
        )

        if permissions.count() != len(set(permission_ids)):
            return Response(
                {"error": "One or more permission IDs are invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # set() syncs exactly — adds checked, removes unchecked
            role.permissions.set(permissions)
        except Exception as e:
            logger.exception("Failed to sync permissions for role %s", role.rolename)
            return Response(
                {"error": "Failed to sync permissions. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": "Permissions synced successfully.",
                "role": RoleSerializer(role).data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Delete a role",
        description="Delete a role.",
        tags=["Accounts"],
        operation_id="role_delete",
        parameters=[
            OpenApiParameter(
                name="role_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Role ID",
            ),
        ],
        responses={
            200: inline_serializer(
                "RoleDeleteSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "role": serializers.CharField(),
                },
            ),
            403: inline_serializer(
                "RoleDeleteForbiddenResponse",
                fields={"error": serializers.CharField()},
            ),
            404: inline_serializer(
                "RoleDeleteNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def delete(self, request, role_id):
        role = get_object_or_404(Role, role_id=role_id)

        if role.rolename in ["Admin", "Manager", "Employee"]:
            return Response(
                {"error": "Default roles cannot be deleted."},
                status=status.HTTP_403_FORBIDDEN,
            )

        role_name = role.rolename

        try:
            role.delete()
        except Exception:
            logger.exception("Failed to delete role %s", role_name)
            return Response(
                {"error": "Failed to delete role. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "Role deleted successfully.", "role": role_name},
            status=status.HTTP_200_OK,
        )


class AssignRoleAPIView(APIView):
    permission_classes = [HasDynamicPermission]
    permission_name = "assign_role"

    @extend_schema(
        summary="Assign a role to a user",
        description="Assign a role to a user by their UUID. Requires assign_role permission.",
        tags=["Accounts"],
        operation_id="assign_role_update",
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="User UUID",
            ),
        ],
        request=inline_serializer(
            "AssignRoleRequest",
            fields={
                "role_id": serializers.IntegerField(help_text="Role ID to assign"),
            },
        ),
        responses={
            200: inline_serializer(
                "AssignRoleSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "user": serializers.CharField(),
                    "role": serializers.CharField(),
                },
            ),
            400: inline_serializer(
                "AssignRoleErrorResponse",
                fields={"error": serializers.CharField()},
            ),
            403: inline_serializer(
                "AssignRoleForbiddenResponse",
                fields={"error": serializers.CharField()},
            ),
            404: inline_serializer(
                "AssignRoleNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def put(self, request, user_id):
        user = get_object_or_404(CustomUser, user_id=user_id)

        if user.role and user.role.rolename == "Admin":
            return Response(
                {"error": "Admin role cannot be changed."},
                status=status.HTTP_403_FORBIDDEN,
            )

        role_id = request.data.get("role_id")

        if not role_id:
            return Response(
                {"error": "role_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        role = get_object_or_404(Role, role_id=role_id)

        user.role = role

        try:
            user.save()
            from Notification.notification_utils import trigger_notification_event
            from Notification.models import NotificationEventType

            trigger_notification_event(
                event_type=NotificationEventType.ROLE_CHANGED,
                recipient=user,
                context={
                    "user_name": user.get_full_name() or user.username,
                    "role_name": role.rolename,
                },
            )
        except Exception:
            logger.exception("Failed to assign role to user %s", user.username)
            return Response(
                {"error": "Failed to assign role. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": "Role assigned successfully.",
                "user": user.username,
                "role": role.rolename,
            },
            status=status.HTTP_200_OK,
        )


class PermissionListCreateAPIView(APIView):
    permission_classes = [HasDynamicPermission]
    permission_names = {
        "GET": "view_permission",
        "POST": "add_permission",
    }

    @extend_schema(
        summary="List all permissions",
        description="Retrieve a list of all Django permissions.",
        tags=["Accounts"],
        operation_id="permission_list",
        responses={
            200: inline_serializer(
                "PermissionListSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "permissions": PermissionSerializer(many=True),
                },
            )
        },
    )
    def get(self, request):
        permissions = Permission.objects.all().order_by("id")
        serializer = PermissionSerializer(permissions, many=True)

        return Response(
            {
                "message": "Permissions retrieved successfully.",
                "permissions": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Create a permission",
        description="Create a new permission. Requires add_permission permission.",
        tags=["Accounts"],
        operation_id="permission_create",
        request=PermissionSerializer,
        responses={
            201: inline_serializer(
                "PermissionCreateSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "permission": PermissionSerializer(),
                },
            ),
            400: PermissionSerializer,
        },
    )
    def post(self, request):
        serializer = PermissionSerializer(data=request.data)

        if serializer.is_valid():
            try:
                serializer.save()
            except Exception:
                logger.exception(
                    "Failed to create permission %s", request.data.get("codename")
                )
                return Response(
                    {"error": "Failed to create permission. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {
                    "message": "Permission created successfully.",
                    "permission": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PermissionDetailAPIView(APIView):
    permission_classes = [HasDynamicPermission]
    permission_names = {
        "PUT": "change_permission",
        "DELETE": "delete_permission",
    }

    @extend_schema(
        summary="Update a permission",
        description="Update an existing permission. Requires change_permission permission.",
        tags=["Accounts"],
        operation_id="permission_update",
        request=PermissionSerializer,
        parameters=[
            OpenApiParameter(
                name="permission_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Permission ID",
            ),
        ],
        responses={
            200: inline_serializer(
                "PermissionUpdateSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "permission": PermissionSerializer(),
                },
            ),
            400: PermissionSerializer,
            404: inline_serializer(
                "PermissionNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def put(self, request, permission_id):
        permission = get_object_or_404(Permission, id=permission_id)

        serializer = PermissionSerializer(permission, data=request.data, partial=True)

        if serializer.is_valid():
            try:
                serializer.save()
            except Exception:
                logger.exception("Failed to update permission %s", permission.codename)
                return Response(
                    {"error": "Failed to update permission. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {
                    "message": "Permission updated successfully.",
                    "permission": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Delete a permission",
        description="Delete a permission. Requires delete_permission permission.",
        tags=["Accounts"],
        operation_id="permission_delete",
        parameters=[
            OpenApiParameter(
                name="permission_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Permission ID",
            ),
        ],
        responses={
            200: inline_serializer(
                "PermissionDeleteSuccessResponse",
                fields={"message": serializers.CharField()},
            ),
            404: inline_serializer(
                "PermissionDeleteNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def delete(self, request, permission_id):
        permission = get_object_or_404(Permission, id=permission_id)

        try:
            permission.delete()
        except Exception:
            logger.exception("Failed to delete permission %s", permission.codename)
            return Response(
                {"error": "Failed to delete permission. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "Permission deleted successfully."}, status=status.HTTP_200_OK
        )


# ==========================================================
# FORGOT / RESET PASSWORD VIEWS
# ==========================================================


def _hash_otp(otp):
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Request a password reset OTP",
        description="Send a 6-digit one-time password (OTP) to the given email address. The OTP expires in "
        + str(OTP_EXPIRY_MINUTES)
        + " minutes and allows up to "
        + str(OTP_MAX_ATTEMPTS)
        + " verification attempts. Always returns 200 to avoid revealing whether the email exists. No authentication required.",
        tags=["Accounts"],
        operation_id="forgot_password_create",
        request=ForgotPasswordSerializer,
        responses={
            200: inline_serializer(
                "ForgotPasswordSuccessResponse",
                fields={"message": serializers.CharField()},
            ),
            400: inline_serializer(
                "ForgotPasswordErrorResponse",
                fields={"error": serializers.CharField()},
            ),
            500: inline_serializer(
                "ForgotPasswordServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]

        try:
            user = CustomUser.objects.filter(email=email).first()

            if not user or not user.is_active:
                logger.warning(
                    "Password reset requested for unknown/inactive email: %s",
                    email,
                )

                return Response(
                    {"error": "No user is registered with this email."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            otp = "".join(str(secrets.randbelow(10)) for _ in range(OTP_LENGTH))

            with transaction.atomic():
                PasswordResetOTP.objects.filter(
                    user=user,
                    is_used=False,
                ).update(is_used=True)

                PasswordResetOTP.objects.create(
                    user=user,
                    otp_hash=_hash_otp(otp),
                    expires_at=timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES),
                )

            send_password_reset_otp_email.delay(user.pk, otp)

            logger.info(
                "Password reset OTP sent to user %s",
                user.user_id,
            )

            return Response(
                {"message": ("Password reset OTP sent successfully " "to your email.")},
                status=status.HTTP_200_OK,
            )

        except Exception:
            logger.exception("Failed to process forgot-password request")

            return Response(
                {"error": ("Failed to send reset OTP. " "Please try again.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Reset password with OTP",
        description="Set a new password using the 6-digit OTP received via email. The OTP expires in "
        + str(OTP_EXPIRY_MINUTES)
        + " minutes, allows up to "
        + str(OTP_MAX_ATTEMPTS)
        + " attempts and becomes invalid after a successful reset. No authentication required.",
        tags=["Accounts"],
        operation_id="reset_password_create",
        request=ResetPasswordSerializer,
        responses={
            200: inline_serializer(
                "ResetPasswordSuccessResponse",
                fields={"message": serializers.CharField()},
            ),
            400: inline_serializer(
                "ResetPasswordErrorResponse",
                fields={"error": serializers.CharField()},
            ),
            500: inline_serializer(
                "ResetPasswordServerErrorResponse",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]
        new_password = serializer.validated_data["new_password"]

        user = CustomUser.objects.filter(email=email).first()

        if not user:
            return Response(
                {"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            otp_record = (
                PasswordResetOTP.objects.select_for_update()
                .filter(user=user, is_used=False, expires_at__gt=timezone.now())
                .first()
            )

        if not otp_record:
            return Response(
                {"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST
            )

        if otp_record.attempts >= OTP_MAX_ATTEMPTS:
            otp_record.is_used = True
            otp_record.save(update_fields=["is_used"])
            return Response(
                {"error": "Too many invalid attempts. Please request a new OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not hmac.compare_digest(otp_record.otp_hash, _hash_otp(otp)):
            otp_record.attempts += 1
            otp_record.save(update_fields=["attempts"])
            remaining = OTP_MAX_ATTEMPTS - otp_record.attempts
            if remaining <= 0:
                otp_record.is_used = True
                otp_record.save(update_fields=["is_used"])
                return Response(
                    {"error": "Too many invalid attempts. Please request a new OTP."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"error": f"Invalid or expired OTP. {remaining} attempt(s) remaining."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user.set_password(new_password)
            if getattr(user, "must_change_password", False):
                user.must_change_password = False
            user.save()

            otp_record.is_used = True
            otp_record.save(update_fields=["is_used"])
        except Exception:
            logger.exception("Password reset failed for user %s", user.user_id)
            return Response(
                {"error": "Failed to reset password. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info("Password reset successfully for user %s", user.user_id)

        return Response(
            {"message": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )


class UserListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List active users/employees",
        description="Retrieve a list of all active users/employees for assignment dropdowns.",
        tags=["Accounts"],
        operation_id="user_list",
    )
    def get(self, request):
        users = (
            CustomUser.objects.select_related("role")
            .filter(is_active=True)
            .order_by("username")
        )
        data = [
            {
                "user_id": str(u.user_id),
                "id": str(u.user_id),
                "username": u.username,
                "email": u.email,
                "full_name": u.get_full_name() or u.username,
                "role": u.role.rolename if u.role else None,
                "role_id": u.role.role_id if u.role else None,
            }
            for u in users
        ]
        return Response(
            {
                "message": "Users retrieved successfully.",
                "users": data,
                "results": data,
            },
            status=status.HTTP_200_OK,
        )


class UnlockUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Unlock a locked user account",
        description="Clears the login rate-limit lock for a user. Only Admin and Manager can unlock accounts. Requires authentication.",
        tags=["Accounts"],
        operation_id="unlock_user_update",
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="User UUID",
            ),
        ],
        responses={
            200: inline_serializer(
                "UnlockUserSuccessResponse",
                fields={"message": serializers.CharField()},
            ),
            403: inline_serializer(
                "UnlockUserForbiddenResponse",
                fields={"error": serializers.CharField()},
            ),
            404: inline_serializer(
                "UnlockUserNotFoundResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def post(self, request, user_id):
        if request.user.is_superuser:
            pass
        elif request.user.role is None or request.user.role.rolename not in [
            "Admin",
            "Manager",
        ]:
            return Response(
                {"error": "Only Admin and Manager can unlock user accounts."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user = get_object_or_404(CustomUser, user_id=user_id)
        limiter_unlock(user.email)

        logger.info("User %s unlocked by %s", user.email, request.user.email)

        return Response(
            {"message": "User account unlocked successfully."},
            status=status.HTTP_200_OK,
        )
