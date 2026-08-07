from django.shortcuts import render

from .models import CustomUser, Role 
from .serializers import PermissionSerializer, ProfileSerializer, RegisterSerializer, LoginSerializer, LogOutSerializer, RefreshTokenSerializer, ChangePasswordSerializer, RoleListSerializer, RoleSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken        #type: ignore
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Permission

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
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user_id = serializer.validated_data["user_id"]
            email = serializer.validated_data["email"]
            password = serializer.validated_data["password"]

            try:
                user = CustomUser.objects.get(
                    user_id=user_id,
                    email=email
                )
            except CustomUser.DoesNotExist:
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if not user.check_password(password):
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            refresh = RefreshToken.for_user(user)

            return Response({
                "message": "Login successful",
                "refresh_token": str(refresh),
                "access_token": str(refresh.access_token),
            })


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogOutSerializer(data=request.data)

        if serializer.is_valid():
            refresh_token = serializer.validated_data["refresh_token"]

            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response({"message": f"Logout successful for {request.user.username}"}, status=status.HTTP_205_RESET_CONTENT)
            
            except Exception:
                return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"error": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)


class refreshTokenAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh_token")

        if not refresh_token:
            return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)

            return Response({"access_token": new_access_token}, status=status.HTTP_200_OK)

        except Exception:
            return Response({"error": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)



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

            user.set_password(new_password)
            user.save()

            return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):

        if request.user.role is None:
            return Response(
                {"error": "Role is not assigned."},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.user.role.rolename not in ["Admin", "Manager"]:
            return Response(
                {"error": "Only Admin and Manager can view profiles."},
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
    permission_classes = [IsAuthenticated]

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

        roles = Role.objects.all()
        serializer = RoleListSerializer(roles, many=True)

        return Response(
            {
                "message": "Roles retrieved successfully.",
                "roles": serializer.data
            },
            status=status.HTTP_200_OK
        )


    def post(self, request):
        if request.user.role is None:
            return Response(
                {"error": "Role is not assigned."},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.user.role.rolename != "Admin":
            return Response(
                {"error": "Only Admin can create roles."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RoleSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Role created successfully.",
                    "role": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    def delete(self, request):
        role_id = request.data.get("role_id")

        if not role_id:
            return Response(
                {"error": "role_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.user.role is None:
            return Response(
                {"error": "Role is not assigned."},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.user.role.rolename != "Admin":
            return Response(
                {"error": "Only Admin can delete roles."},
                status=status.HTTP_403_FORBIDDEN
            )

        role = get_object_or_404(Role, role_id=role_id)
        role.delete()

        return Response(
            {"message": "Role deleted successfully.",
             "role": role.rolename
             },
            status=status.HTTP_200_OK
        )

class AssignRoleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, user_id):

        if request.user.role is None or request.user.role.rolename != "Admin":
            return Response(
                {"error": "Only Admin can assign roles."},
                status=status.HTTP_403_FORBIDDEN
            )

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
        user.save()

        return Response(
            {
                "message": "Role assigned successfully.",
                "user": user.username,
                "role": role.rolename
            },
            status=status.HTTP_200_OK
        )



class PermissionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role is None:
            return Response(
                {"error": "Role is not assigned."},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.user.role.rolename != "Admin":
            return Response(
                {"error": "Only Admin can view permissions."},
                status=status.HTTP_403_FORBIDDEN
            )

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
        if request.user.role is None:
            return Response(
                {"error": "Role is not assigned."},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.user.role.rolename != "Admin":
            return Response(
                {"error": "Only Admin can create permissions."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = PermissionSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Permission created successfully.",
                    "permission": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, permission_id):

        if request.user.role is None:
            return Response(
                {"error": "Role is not assigned."},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.user.role.rolename != "Admin":
            return Response(
                {"error": "Only Admin can update permissions."},
                status=status.HTTP_403_FORBIDDEN
            )

        permission = get_object_or_404(Permission, id=permission_id)

        serializer = PermissionSerializer(
            permission,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Permission updated successfully.",
                    "permission": serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, permission_id):

        if request.user.role is None:
            return Response(
                {"error": "Role is not assigned."},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.user.role.rolename != "Admin":
            return Response(
                {"error": "Only Admin can delete permissions."},
                status=status.HTTP_403_FORBIDDEN
            )

        permission = get_object_or_404(Permission, id=permission_id)
        permission.delete()

        return Response(
            {"message": "Permission deleted successfully."},
            status=status.HTTP_200_OK
        )
