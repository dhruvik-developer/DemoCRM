from django.shortcuts import render

from .models import CustomUser, Role 
from .serializers import ProfileSerializer, RegisterSerializer, LoginSerializer, LogOutSerializer, RefreshTokenSerializer, ChangePasswordSerializer, RoleSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

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
            
            except Exception:
                return Response(
                    {"error": "An error occurred while registering the user."},
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

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response({"message": "Profile retrieved successfully.", "profile": serializer.data}, status=status.HTTP_200_OK)


class CreateRoleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        roles = Role.objects.all()
        serializer = RoleSerializer(roles, many=True)
        return Response({"message": "Roles retrieved successfully.", "roles": serializer.data}, status=status.HTTP_200_OK)


    def post(self, request):
        serializer = RoleSerializer(data=request.data)

        if request.CustomUser.role.rolename == None and request.CustomUser.role.rolename != "Admin":
            return Response(
                {"error": "Only Admin can create roles"},
                status=status.HTTP_403_FORBIDDEN
            )

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Role created successfully.", "role": serializer.data}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)