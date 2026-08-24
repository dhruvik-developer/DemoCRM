import logging


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

logger = logging.getLogger(__name__)


# Create your views here.
class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register a new user",
        description="Create a new user account. The user is automatically assigned the Employee role. No authentication required.",
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
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        # breakpoint()

        if serializer.is_valid():
            try:
                serializer.save()
                logger.info(
                    "User registered successfully: %s (ID: %s)",
                    serializer.data["email"],
                    serializer.data["user_id"],
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
        description="Authenticate with email and password. Returns access and refresh tokens.",
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

            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                logger.warning("Failed login attempt for non-existent email: %s", email)
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if not user.is_active or not user.check_password(password):
                logger.warning(
                    "Failed login attempt for user: %s (inactive or wrong password)",
                    email,
                )
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            try:
                refresh = RefreshToken.for_user(user)
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

    def patch(self, request, role_id):
        role = get_object_or_404(Role, role_id=role_id)

        if role.rolename == "Admin":
            return Response(
                {"error": "Admin role cannot be updated."},
                status=status.HTTP_403_FORBIDDEN,
            )

        permission_ids = request.data.get("permissions")

        if not permission_ids:
            return Response(
                {"error": "permissions is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        permissions = Permission.objects.filter(id__in=permission_ids)

        if permissions.count() != len(set(permission_ids)):
            return Response(
                {"error": "One or more permission IDs are invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            role.permissions.add(*permissions)
        except Exception as e:
            logger.exception("Failed to add permissions to role %s", role.rolename)
            return Response(
                {"error": "Failed to add permissions. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": "Permissions added successfully.",
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


# Backward compatibility alias
RoleAPIView = RoleListCreateAPIView


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


# Backward compatibility alias
PermissionAPIView = PermissionListCreateAPIView
