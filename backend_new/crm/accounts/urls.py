from django.urls import path
from .views import (
    RegisterAPIView,
    LoginAPIView,
    LogoutAPIView,
    RefreshTokenAPIView,
    ChangePasswordAPIView,
    ProfileAPIView,
    RoleListCreateAPIView,
    RoleDetailAPIView,
    AssignRoleAPIView,
    PermissionListCreateAPIView,
    PermissionDetailAPIView,
)

# Forgot / Reset password (new - existing imports untouched)
from .views import ForgotPasswordAPIView, ResetPasswordAPIView

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("refresh/", RefreshTokenAPIView.as_view(), name="token_refresh"),
    path("change-password/", ChangePasswordAPIView.as_view(), name="change_password"),
    path("profile/<uuid:user_id>/", ProfileAPIView.as_view(), name="profile"),
    path("roles/", RoleListCreateAPIView.as_view(), name="roles"),
    path("roles/<int:role_id>/", RoleDetailAPIView.as_view(), name="role_detail"),
    path("permissions/", PermissionListCreateAPIView.as_view(), name="permissions"),
    path(
        "permissions/<int:permission_id>/",
        PermissionDetailAPIView.as_view(),
        name="permission_detail",
    ),
    path(
        "assign-role/<uuid:user_id>/", AssignRoleAPIView.as_view(), name="assign_role"
    ),
    # Forgot / Reset password (new)
    path("forgot-password/", ForgotPasswordAPIView.as_view(), name="forgot_password"),
    path("reset-password/", ResetPasswordAPIView.as_view(), name="reset_password"),
]
