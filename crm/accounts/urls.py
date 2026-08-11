from django.urls import path
from .views import RoleAPIView, RegisterAPIView, LoginAPIView, LogoutAPIView, RoleAPIView, RefreshTokenAPIView, ChangePasswordAPIView, ProfileAPIView, AssignRoleAPIView, PermissionAPIView

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("refresh/", RefreshTokenAPIView.as_view(), name="token_refresh"),
    path("change-password/", ChangePasswordAPIView.as_view(), name="change_password"),
    path("profile/<uuid:user_id>/", ProfileAPIView.as_view(), name="profile"),
    path("roles/", RoleAPIView.as_view(), name="roles"),
    path("roles/<int:role_id>/", RoleAPIView.as_view(), name="role_detail"),
    path("permissions/", PermissionAPIView.as_view(), name="permissions"),
    path("permissions/<int:permission_id>/", PermissionAPIView.as_view(), name="permission_detail"),
    path("assign-role/<uuid:user_id>/", AssignRoleAPIView.as_view(), name="assign_role"),
]
 