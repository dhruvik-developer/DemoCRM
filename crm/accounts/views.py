import logging

from django.shortcuts import render

from .models import CustomUser, Role 
from .serializers import PermissionSerializer, ProfileSerializer, RefreshTokenSerializer, RegisterSerializer, LoginSerializer, LogOutSerializer, ChangePasswordSerializer, RoleListSerializer, RoleSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken        #type: ignore
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Permission
from .permissions import HasDynamicPermission
from rest_framework_simplejwt.exceptions import TokenError

logger = logging.getLogger(__name__)

# Create your views here.
class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():

            try:
                serializer.save()
                return Response(
                    {"user_id": serializer.data["user_id"],
                     "username": serializer.data["username"],
                     "email": serializer.data["email"],
                     "message": "User registered successfully"},
                    status=status.HTTP_201_CREATED
                )
            
            except Exception as e:
                logger.exception("Failed to register user %s", request.data.get("email"))
                return Response(
                    {"error": "Failed to register. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data["email"]
            password = serializer.validated_data["password"]

            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if not user.is_active or not user.check_password(password):
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            try:
                refresh = RefreshToken.for_user(user)
            except Exception as e:
                logger.exception("Token generation failed for user %s", email)
                return Response(
                    {"error": "Failed to generate tokens. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response({
                "message": "Login successful",
                "refresh_token": str(refresh),
                "access_token": str(refresh.access_token),
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    permission_name = "logout"

    def post(self, request):
        serializer = LogOutSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        refresh_token = serializer.validated_data["refresh_token"]

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {
                    "message": f"Logout successful for "
                               f"{request.user.username}"
                },
                status=status.HTTP_200_OK
            )

        except TokenError as e:
            if "blacklisted" in str(e).lower():
                return Response(
                {
                    "message" : "You are already logged out."
                },
                status=status.HTTP_200_OK
            )

            return Response(
                {
                    "error": "Invalid or expired refresh token."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception:
            logger.exception("Logout failed for user %s", request.user)
            return Response(
                {"error": "Logout failed. Please try again."},
                status=status.HTTP_400_BAD_REQUEST
            )
        

class RefreshTokenAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)

        if serializer.is_valid():
            refresh_token = serializer.validated_data["refresh_token"]

            try:
                token = RefreshToken(refresh_token)
                new_access_token = str(token.access_token)

                return Response({
                    "message": "Access token refreshed successfully",
                    "access_token": new_access_token
                }, status=status.HTTP_200_OK)

            except Exception:
                return Response({"error": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            old_password = serializer.validated_data["old_password"]
            new_password = serializer.validated_data["new_password"]

            user = request.user

            if not user.check_password(old_password):
                return Response({"error": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                user.set_password(new_password)
                user.save()
            except Exception as e:
                logger.exception("Password change failed for user %s", request.user)
                return Response(
                    {"error": "Failed to change password. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):

        if request.user.user_id != user_id:
            if request.user.role is None or request.user.role.rolename not in ["Admin", "Manager"]:
                return Response(
                    {"error": "Only Admin and Manager can view other profiles."},
                    status=status.HTTP_403_FORBIDDEN
                )

        user = get_object_or_404(CustomUser, user_id=user_id)   

        serializer = ProfileSerializer(user)

        return Response(
            {
                "message": "Profile retrieved successfully.",
                "profile": serializer.data
            },
            status=status.HTTP_200_OK
        )

 
class RoleAPIView(APIView):
    permission_classes = [HasDynamicPermission]
    permission_names = {
        "GET": "view_role",
        "POST": "add_role",
        "PUT": "change_role",
        "DELETE": "delete_role",
    }

    def get(self, request):
        if request.user.role is None:
             return Response(
            {"error": "Role is not assigned."},
            status=status.HTTP_403_FORBIDDEN
        )

        if request.user.role.rolename not in ["Admin", "Manager"]:
            return Response(
                {"error": "Only Admin and Manager can view roles."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            roles = Role.objects.prefetch_related("permissions").order_by("role_id")
            serializer = RoleListSerializer(roles, many=True)
        except Exception as e:
            logger.exception("Failed to retrieve roles")
            return Response(
                {"error": "Failed to retrieve roles. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "message": "Roles retrieved successfully.",
                "roles": serializer.data
            },
            status=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = RoleSerializer(data=request.data)

        if serializer.is_valid():
            try:
                serializer.save()
            except Exception as e:
                logger.exception("Failed to create role %s", request.data.get("rolename"))
                return Response(
                    {"error": "Failed to create role. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(
                {
                    "message": "Role created successfully.",
                    "role": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def put(self, request, role_id):
        role = get_object_or_404(Role, role_id=role_id)

        if role.rolename == "Admin":
            return Response(
                {"error": "Admin role cannot be updated."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RoleSerializer(
            role,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            try:
                serializer.save()
            except Exception as e:
                logger.exception("Failed to update role %s", role.rolename)
                return Response(
                    {"error": "Failed to update role. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(
                {
                    "message": "Role updated successfully.",
                    "role": serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


    def patch(self, request, role_id):
        role = get_object_or_404(Role, role_id=role_id)

        if role.rolename == "Admin":
            return Response(
                {"error": "Admin role cannot be updated."},
                status=status.HTTP_403_FORBIDDEN
            )

        permission_ids = request.data.get("permissions")

        if not permission_ids:
            return Response(
                {"error": "permissions is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        permissions = Permission.objects.filter(
            id__in=permission_ids
        )

        if permissions.count() != len(set(permission_ids)):
            return Response(
                {"error": "One or more permission IDs are invalid."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            role.permissions.add(*permissions)
        except Exception as e:
            logger.exception("Failed to add permissions to role %s", role.rolename)
            return Response(
                {"error": "Failed to add permissions. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "message": "Permissions added successfully.",
                "role": RoleSerializer(role).data
            },
            status=status.HTTP_200_OK
        )

    def delete(self, request, role_id):
        role = get_object_or_404(Role, role_id=role_id)

        if role.rolename in ["Admin", "Manager", "Employee"]:
            return Response(
                {"error": "Default roles cannot be deleted."},
                status=status.HTTP_403_FORBIDDEN
            )

        role_name = role.rolename

        try:
            role.delete()
        except Exception as e:
            logger.exception("Failed to delete role %s", role_name)
            return Response(
                {"error": "Failed to delete role. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "message": "Role deleted successfully.",
                "role": role_name
            },
            status=status.HTTP_200_OK
        )

class AssignRoleAPIView(APIView):
    permission_classes = [HasDynamicPermission]
    permission_name = "assign_role" 

    def put(self, request, user_id):
        user = get_object_or_404(CustomUser, user_id=user_id)

        if user.role and user.role.rolename == "Admin":
            return Response(
                {"error": "Admin role cannot be changed."},
                status=status.HTTP_403_FORBIDDEN
            )

        role_id = request.data.get("role_id")

        if not role_id:
            return Response(
                {"error": "role_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        role = get_object_or_404(Role, role_id=role_id)

        user.role = role

        try:
            user.save()
        except Exception as e:
            logger.exception("Failed to assign role to user %s", user.username)
            return Response(
                {"error": "Failed to assign role. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "message": "Role assigned successfully.",
                "user": user.username,
                "role": role.rolename
            },
            status=status.HTTP_200_OK
        )



class PermissionAPIView(APIView):
    permission_classes = [HasDynamicPermission]
    permission_names = {
        "GET": "view_permission",
        "POST": "add_permission",
        "PUT": "change_permission",
        "DELETE": "delete_permission",
    }

    def get(self, request):
        permissions = Permission.objects.all().order_by("id")
        serializer = PermissionSerializer(permissions, many=True)

        return Response(
            {
                "message": "Permissions retrieved successfully.",
                "permissions": serializer.data
            },
            status=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = PermissionSerializer(data=request.data)

        if serializer.is_valid():
            try:
                serializer.save()
            except Exception as e:
                logger.exception("Failed to create permission %s", request.data.get("codename"))
                return Response(
                    {"error": "Failed to create permission. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(
                {
                    "message": "Permission created successfully.",
                    "permission": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, permission_id):
        permission = get_object_or_404(Permission, id=permission_id)

        serializer = PermissionSerializer(
            permission,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            try:
                serializer.save()
            except Exception as e:
                logger.exception("Failed to update permission %s", permission.codename)
                return Response(
                    {"error": "Failed to update permission. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(
                {
                    "message": "Permission updated successfully.",
                    "permission": serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, permission_id):
        permission = get_object_or_404(Permission, id=permission_id)

        try:
            permission.delete()
        except Exception as e:
            logger.exception("Failed to delete permission %s", permission.codename)
            return Response(
                {"error": "Failed to delete permission. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {"message": "Permission deleted successfully."},
            status=status.HTTP_200_OK
        )
