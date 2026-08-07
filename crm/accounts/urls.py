from django.urls import path
from .views import PermissionAPIView, RoleAPIView, RegisterAPIView, LoginAPIView, LogoutAPIView, RoleAPIView, refreshTokenAPIView, ChangePasswordAPIView, ProfileAPIView, AssignRoleAPIView

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("refresh/", refreshTokenAPIView.as_view(), name="token_refresh"),
    path("change-password/", ChangePasswordAPIView.as_view(), name="change_password"),
    path("profile/<uuid:user_id>/", ProfileAPIView.as_view(), name="profile"),
    path("roles/", RoleAPIView.as_view(), name="roles"),
    path("assign-role/<uuid:user_id>/", AssignRoleAPIView.as_view(), name="assign_role"),
    path("permissions/", PermissionAPIView.as_view(), name="permissions"),
]
