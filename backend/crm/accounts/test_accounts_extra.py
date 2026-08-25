"""
New / extended test suite for the `accounts` app.

This file is fully independent of the existing tests.py and does NOT
modify or rely on it. The Swagger / OpenAPI schema tests in
test_spectacular.py remain untouched.

Covered functionality:
    * Models            -> Role, CustomUser, PasswordResetOTP, managers
    * Serializers       -> register, logout, change/reset password
    * Auth endpoints    -> register, login, logout, refresh token
    * Account endpoints -> change-password, profile
    * RBAC              -> roles, role detail, assign-role, permissions
    * OTP flow          -> forgot-password, reset-password (+ security edge cases)
"""

import hashlib
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase, APIRequestFactory

from accounts.models import CustomUser, PasswordResetOTP, Role
from accounts.permissions import HasDynamicPermission
from accounts.serializers import (
    ChangePasswordSerializer,
    LogOutSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
)
from accounts.views import OTP_MAX_ATTEMPTS

# ------------------------------------------------------------------
# Disable throttling so the anon "100/day" rate never interferes.
# ------------------------------------------------------------------

NO_THROTTLE_SETTINGS = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

no_throttle = override_settings(REST_FRAMEWORK=NO_THROTTLE_SETTINGS)


def hash_otp(otp):
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def unique_phone(counter=[0]):
    counter[0] += 1
    return f"900000{counter[0]:04d}"[-10:]


def get_custom_permission(codename):
    """Return (creating if needed) a permission attached to the Role model."""
    ct = ContentType.objects.get_for_model(Role)
    permission, _ = Permission.objects.get_or_create(
        codename=codename,
        content_type=ct,
        defaults={"name": f"Can {codename.replace('_', ' ')}"},
    )
    return permission


def make_user(email, password="Str0ngPass!23", rolename=None, **extra):
    extra.setdefault("username", email.split("@")[0])
    user = CustomUser.objects.create_user(
        email=email, password=password, phone_number=unique_phone(), **extra
    )
    if rolename:
        role, _ = Role.objects.get_or_create(rolename=rolename)
        user.role = role
        user.save(update_fields=["role"])
    return user


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ==================================================================
# MODEL TESTS
# ==================================================================


class RoleModelTests(TestCase):
    def test_str_returns_rolename(self):
        role = Role.objects.create(rolename="Tester")
        self.assertEqual(str(role), "Tester")

    def test_rolename_is_unique(self):
        Role.objects.create(rolename="UniqueRole")
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Role.objects.create(rolename="UniqueRole")

    def test_timestamps_set(self):
        role = Role.objects.create(rolename="Timestamped")
        self.assertIsNotNone(role.created_at)
        self.assertIsNotNone(role.updated_at)

    def test_default_permissions_empty(self):
        role = Role.objects.create(rolename="EmptyPerms")
        self.assertEqual(role.permissions.count(), 0)


class CustomUserModelTests(TestCase):
    def test_str_returns_email(self):
        user = make_user("model.str@example.com")
        self.assertEqual(str(user), "model.str@example.com")

    def test_user_id_is_uuid(self):
        import uuid

        user = make_user("uuid.user@example.com")
        self.assertIsInstance(user.user_id, uuid.UUID)

    def test_email_is_required_unique(self):
        make_user("dup@example.com")
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            make_user("dup@example.com")

    def test_create_user_hashes_password(self):
        user = make_user("hash.pass@example.com", password="S3cret!pass")
        self.assertTrue(user.check_password("S3cret!pass"))
        self.assertNotEqual(user.password, "S3cret!pass")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_create_user_normalizes_email_domain(self):
        user = make_user("Normalize@EXAMPLE.COM")
        self.assertEqual(user.email, "Normalize@example.com")

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(email="", username="noemail", password="x")

    def test_create_superuser_flags_and_admin_role(self):
        user = make_user("super.user@example.com")
        user.is_superuser = True
        user.is_staff = True
        user.save()
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)


class CustomUserManagerTests(TestCase):
    def test_create_superuser_sets_flags_and_admin_role(self):
        from accounts.managers import CustomUserManager

        manager = CustomUserManager()
        manager.model = CustomUser
        user = CustomUser.objects.create_superuser(
            email="admin.manager@example.com",
            username="adminmanager",
            password="SuperSecret!1",
        )
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role.rolename, "Admin")


class PasswordResetOTPModelTests(TestCase):
    def setUp(self):
        self.user = make_user("otp.owner@example.com")

    def test_defaults(self):
        otp = PasswordResetOTP.objects.create(
            user=self.user,
            otp_hash=hash_otp("123456"),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        self.assertFalse(otp.is_used)
        self.assertEqual(otp.attempts, 0)

    def test_str_representation(self):
        otp = PasswordResetOTP.objects.create(
            user=self.user,
            otp_hash=hash_otp("654321"),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        self.assertIn(self.user.email, str(otp))
        self.assertIn("used=False", str(otp))

    def test_ordering_newest_first(self):
        old = PasswordResetOTP.objects.create(
            user=self.user,
            otp_hash=hash_otp("111111"),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        new = PasswordResetOTP.objects.create(
            user=self.user,
            otp_hash=hash_otp("222222"),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        qs = list(PasswordResetOTP.objects.filter(user=self.user))
        self.assertEqual(qs[0], new)
        self.assertEqual(qs[1], old)


# ==================================================================
# SERIALIZER TESTS
# ==================================================================


class RegisterSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.employee_role = Role.objects.get_or_create(rolename="Employee")[0]

    def test_valid_data_creates_user_with_employee_role(self):
        serializer = RegisterSerializer(
            data={
                "username": "seruser",
                "email": "serializer@example.com",
                "phone_number": unique_phone(),
                "password": "VeryStrong!99",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.email, "serializer@example.com")
        self.assertEqual(user.role, self.employee_role)

    def test_missing_password_invalid(self):
        serializer = RegisterSerializer(
            data={
                "username": "nopass",
                "email": "nopass@example.com",
                "phone_number": unique_phone(),
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_duplicate_email_invalid_at_db_level_only(self):
        # Uniqueness is enforced by DB, not the serializer.
        serializer = RegisterSerializer(
            data={
                "username": "dupe",
                "email": "not-a-real-check@example.com",
                "phone_number": unique_phone(),
                "password": "Whatever!12",
            }
        )
        self.assertTrue(serializer.is_valid())


class LogOutSerializerTests(TestCase):
    def test_missing_refresh_token_invalid(self):
        serializer = LogOutSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn("refresh_token", serializer.errors)

    def test_blank_refresh_token_invalid(self):
        serializer = LogOutSerializer(data={"refresh_token": ""})
        self.assertFalse(serializer.is_valid())

    def test_provided_refresh_token_valid(self):
        serializer = LogOutSerializer(data={"refresh_token": "abc.def.ghi"})
        self.assertTrue(serializer.is_valid())


class ChangePasswordSerializerTests(TestCase):
    def test_weak_new_password_rejected(self):
        serializer = ChangePasswordSerializer(
            data={"old_password": "OldPass!12", "new_password": "123"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password", serializer.errors)

    def test_common_password_rejected(self):
        serializer = ChangePasswordSerializer(
            data={"old_password": "OldPass!12", "new_password": "password123"}
        )
        self.assertFalse(serializer.is_valid())

    def test_strong_password_accepted(self):
        serializer = ChangePasswordSerializer(
            data={"old_password": "OldPass!12", "new_password": "N3wSecure!Pass"}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_old_password_required(self):
        serializer = ChangePasswordSerializer(data={"new_password": "N3wSecure!Pass"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("old_password", serializer.errors)


class ResetPasswordSerializerTests(TestCase):
    def test_otp_must_be_six_digits_long(self):
        serializer = ResetPasswordSerializer(
            data={
                "email": "x@example.com",
                "otp": "12345",
                "new_password": "N3wSecure!Pass",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("otp", serializer.errors)

    def test_non_numeric_otp_still_length_checked_only(self):
        serializer = ResetPasswordSerializer(
            data={
                "email": "x@example.com",
                "otp": "abcdef",
                "new_password": "N3wSecure!Pass",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_weak_new_password_rejected(self):
        serializer = ResetPasswordSerializer(
            data={"email": "x@example.com", "otp": "123456", "new_password": "abc"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password", serializer.errors)

    def test_valid_payload(self):
        serializer = ResetPasswordSerializer(
            data={
                "email": "x@example.com",
                "otp": "123456",
                "new_password": "N3wSecure!Pass",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)


# ==================================================================
# PERMISSION CLASS UNIT TESTS
# ==================================================================


class HasDynamicPermissionUnitTests(APITestCase):
    def _request(self, user, method="GET"):
        factory = APIRequestFactory()
        request = getattr(factory, method.lower())("/api/roles/")
        request.user = user
        return request

    def _view(self, config):
        view = type("FakeView", (), {"permission_names": config})
        return view()

    def test_unauthenticated_denied(self):
        perm = HasDynamicPermission()
        self.assertFalse(
            perm.has_permission(self._request(None), self._view({"GET": "view_role"}))
        )

    def test_superuser_allowed_without_permission_entry(self):
        user = make_user("perm.super@example.com", is_superuser=True)
        user.is_superuser = True
        perm = HasDynamicPermission()
        self.assertTrue(perm.has_permission(self._request(user), self._view({})))

    def test_no_role_denied(self):
        user = make_user("perm.norole@example.com")
        perm = HasDynamicPermission()
        self.assertFalse(
            perm.has_permission(self._request(user), self._view({"GET": "view_role"}))
        )

    def test_method_not_mapped_denied(self):
        role, _ = Role.objects.get_or_create(rolename="PermMapRole")
        user = make_user("perm.mapped@example.com", rolename=None)
        user.role = role
        user.save()
        perm = HasDynamicPermission()
        self.assertFalse(
            perm.has_permission(
                self._request(user, method="DELETE"), self._view({"GET": "view_role"})
            )
        )

    def test_single_string_config_used_for_any_mapped_method(self):
        role, _ = Role.objects.get_or_create(rolename="SingleRole")
        role.permissions.add(get_custom_permission("assign_role"))
        user = make_user("perm.single@example.com")
        user.role = role
        user.save()
        perm = HasDynamicPermission()
        view = type("FakeView", (), {"permission_name": "assign_role"})()
        self.assertTrue(perm.has_permission(self._request(user, method="PUT"), view))

    def test_role_without_codename_denied(self):
        role, _ = Role.objects.get_or_create(rolename="BareRole")
        user = make_user("perm.bare@example.com")
        user.role = role
        user.save()
        perm = HasDynamicPermission()
        self.assertFalse(
            perm.has_permission(self._request(user), self._view({"GET": "view_role"}))
        )


# ==================================================================
# REGISTRATION API TESTS
# ==================================================================


@no_throttle
class RegisterAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("register")
        Role.objects.get_or_create(rolename="Employee")

    def _payload(self, **overrides):
        payload = {
            "username": "newuser",
            "email": "newuser@example.com",
            "phone_number": unique_phone(),
            "password": "RegTest!2024",
        }
        payload.update(overrides)
        return payload

    def test_register_success_201(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "User registered successfully")
        self.assertEqual(response.data["email"], "newuser@example.com")
        self.assertIn("user_id", response.data)

    def test_register_assigns_employee_role(self):
        self.client.post(self.url, self._payload(), format="json")
        user = CustomUser.objects.get(email="newuser@example.com")
        self.assertEqual(user.role.rolename, "Employee")

    def test_register_duplicate_email_400(self):
        self.client.post(self.url, self._payload(), format="json")
        response = self.client.post(
            self.url, self._payload(username="other"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_phone_400(self):
        shared_phone = unique_phone()
        self.client.post(
            self.url, self._payload(phone_number=shared_phone), format="json"
        )
        response = self.client.post(
            self.url,
            self._payload(email="second@example.com", phone_number=shared_phone),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields_400(self):
        response = self.client.post(
            self.url, {"email": "only@email.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_email_400(self):
        response = self.client.post(
            self.url, self._payload(email="not-an-email"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_response_has_no_password(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertNotIn("password", response.data)


# ==================================================================
# LOGIN API TESTS
# ==================================================================


@no_throttle
class LoginAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("login")
        self.user = make_user("login.user@example.com", password="LoginPass!12")

    def _login(self, email="login.user@example.com", password="LoginPass!12"):
        return self.client.post(
            self.url, {"email": email, "password": password}, format="json"
        )

    def test_login_success_returns_tokens(self):
        response = self._login()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertEqual(response.data["message"], "Login successful")

    def test_access_token_contains_user_id_claim(self):
        import jwt

        response = self._login()
        access = response.data["access_token"]
        payload = jwt.decode(access, options={"verify_signature": False})
        self.assertEqual(payload.get("user_id"), str(self.user.user_id))

    def test_login_wrong_password_401(self):
        response = self._login(password="WrongPass!12")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["error"], "Invalid credentials")

    def test_login_unknown_email_401(self):
        response = self._login(email="ghost@example.com")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_inactive_user_401(self):
        self.user.is_active = False
        self.user.save()
        response = self._login()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_password_400(self):
        response = self.client.post(
            self.url, {"email": "login.user@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_invalid_email_format_400(self):
        response = self._login(email="bad-email")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ==================================================================
# LOGOUT API TESTS
# ==================================================================


@no_throttle
class LogoutAPITests(APITestCase):
    def setUp(self):
        self.user = make_user("logout.user@example.com", password="LogoutPass!12")
        self.client = auth_client(self.user)
        self.url = reverse("logout")
        login_client = APIClient()
        response = login_client.post(
            reverse("login"),
            {"email": "logout.user@example.com", "password": "LogoutPass!12"},
            format="json",
        )
        self.refresh_token = response.data["refresh_token"]

    def test_logout_unauthenticated_401(self):
        response = APIClient().post(
            self.url, {"refresh_token": self.refresh_token}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_token(self):
        response = self.client.post(
            self.url, {"refresh_token": self.refresh_token}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Logout successful", response.data["message"])
        # Refreshing with the blacklisted token must now fail.
        refresh_response = APIClient().post(
            reverse("token_refresh"),
            {"refresh_token": self.refresh_token},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_with_already_blacklisted_token_returns_200(self):
        self.client.post(self.url, {"refresh_token": self.refresh_token}, format="json")
        response = self.client.post(
            self.url, {"refresh_token": self.refresh_token}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "You are already logged out.")

    def test_logout_garbage_token_400(self):
        response = self.client.post(
            self.url, {"refresh_token": "garbage-token"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_missing_token_400(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ==================================================================
# REFRESH TOKEN API TESTS
# ==================================================================


@no_throttle
class RefreshTokenAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("token_refresh")
        make_user("refresh.user@example.com", password="RefreshPass!12")
        response = self.client.post(
            reverse("login"),
            {"email": "refresh.user@example.com", "password": "RefreshPass!12"},
            format="json",
        )
        self.access_token = response.data["access_token"]
        self.refresh_token = response.data["refresh_token"]

    def test_refresh_success_returns_new_access_token(self):
        response = self.client.post(
            self.url, {"refresh_token": self.refresh_token}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)

    def test_refresh_does_not_invalidate_old_refresh_token(self):
        response = self.client.post(
            self.url, {"refresh_token": self.refresh_token}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        again = self.client.post(
            self.url, {"refresh_token": self.refresh_token}, format="json"
        )
        self.assertEqual(again.status_code, status.HTTP_200_OK)

    def test_refresh_with_access_token_fails_400(self):
        response = self.client.post(
            self.url, {"refresh_token": self.access_token}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_invalid_token_400(self):
        response = self.client.post(
            self.url, {"refresh_token": "invalid.token.value"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid refresh token")

    def test_refresh_missing_field_400(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_new_access_token_works_on_protected_endpoint(self):
        response = self.client.post(
            self.url, {"refresh_token": self.refresh_token}, format="json"
        )
        new_access = response.data["access_token"]
        profile_client = APIClient()
        profile_client.credentials(HTTP_AUTHORIZATION=f"Bearer {new_access}")
        me = CustomUser.objects.get(email="refresh.user@example.com")
        profile_response = profile_client.get(
            reverse("profile", kwargs={"user_id": me.user_id})
        )
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)


# ==================================================================
# CHANGE PASSWORD API TESTS
# ==================================================================


@no_throttle
class ChangePasswordAPITests(APITestCase):
    OLD = "ChangeOld!12"
    NEW = "ChangeNew!34"

    def setUp(self):
        self.user = make_user("change.pw@example.com", password=self.OLD)
        self.client = auth_client(self.user)
        self.url = reverse("change_password")

    def test_unauthenticated_401(self):
        response = APIClient().post(
            self.url,
            {"old_password": self.OLD, "new_password": self.NEW},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_success(self):
        response = self.client.post(
            self.url,
            {"old_password": self.OLD, "new_password": self.NEW},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.NEW))
        self.assertFalse(self.user.check_password(self.OLD))

    def test_can_login_with_new_password_after_change(self):
        self.client.post(
            self.url,
            {"old_password": self.OLD, "new_password": self.NEW},
            format="json",
        )
        login_response = APIClient().post(
            reverse("login"),
            {"email": "change.pw@example.com", "password": self.NEW},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_wrong_old_password_400(self):
        response = self.client.post(
            self.url,
            {"old_password": "TotallyWrong!1", "new_password": self.NEW},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Old password is incorrect.")

    def test_weak_new_password_400(self):
        response = self.client.post(
            self.url, {"old_password": self.OLD, "new_password": "123"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.OLD))

    def test_missing_fields_400(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ==================================================================
# PROFILE API TESTS
# ==================================================================


@no_throttle
class ProfileAPITests(APITestCase):
    def setUp(self):
        self.employee = make_user("profile.emp@example.com", rolename="Employee")
        self.other = make_user("profile.other@example.com", rolename="Employee")
        self.admin = make_user("profile.admin@example.com", rolename="Admin")
        self.manager = make_user("profile.manager@example.com", rolename="Manager")

    def _url(self, user):
        return reverse("profile", kwargs={"user_id": user.user_id})

    def test_own_profile_allowed_for_employee(self):
        response = auth_client(self.employee).get(self._url(self.employee))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Profile retrieved successfully.")
        self.assertEqual(response.data["profile"]["email"], self.employee.email)

    def test_profile_contains_expected_fields(self):
        response = auth_client(self.employee).get(self._url(self.employee))
        expected = {
            "user_id",
            "username",
            "email",
            "phone_number",
            "role",
            "created_at",
            "updated_at",
        }
        self.assertEqual(set(response.data["profile"].keys()), expected)

    def test_employee_cannot_view_other_profile_403(self):
        response = auth_client(self.employee).get(self._url(self.other))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Only Admin and Manager", response.data["error"])

    def test_admin_can_view_other_profile(self):
        response = auth_client(self.admin).get(self._url(self.other))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manager_can_view_other_profile(self):
        response = auth_client(self.manager).get(self._url(self.other))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_role_user_cannot_view_others(self):
        nobody = make_user("profile.norole@example.com")
        response = auth_client(nobody).get(self._url(self.other))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonexistent_user_404(self):
        response = auth_client(self.admin).get(
            reverse("profile", kwargs={"user_id": uuid4()})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_401(self):
        response = APIClient().get(self._url(self.employee))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ==================================================================
# ROLES LIST / CREATE API TESTS
# ==================================================================


@no_throttle
class RoleListCreateAPITests(APITestCase):
    def setUp(self):
        self.admin = make_user("roles.admin@example.com", rolename="Admin")
        self.employee = make_user("roles.emp@example.com", rolename="Employee")
        self.no_role = make_user("roles.norole@example.com")
        self.url = reverse("roles")

    def test_list_roles_as_admin(self):
        response = auth_client(self.admin).get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rolenames = [r["rolename"] for r in response.data["roles"]]
        self.assertIn("Admin", rolenames)
        self.assertIn("Employee", rolenames)

    def test_list_roles_as_employee_403(self):
        response = auth_client(self.employee).get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_roles_without_role_403(self):
        response = auth_client(self.no_role).get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_roles_unauthenticated_401(self):
        response = APIClient().get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_role_as_admin_201(self):
        response = auth_client(self.admin).post(
            self.url,
            {"rolename": "Supervisor", "description": "Supervises teams"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Role.objects.filter(rolename="Supervisor").exists())

    def test_create_duplicate_rolename_400(self):
        Role.objects.get_or_create(rolename="Duplicate")
        response = auth_client(self.admin).post(
            self.url, {"rolename": "Duplicate"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_role_missing_name_400(self):
        response = auth_client(self.admin).post(
            self.url, {"description": "no name"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_role_with_permissions(self):
        perm = Permission.objects.filter(codename="view_role").first()
        response = auth_client(self.admin).post(
            self.url,
            {"rolename": "WithPerms", "permissions": [perm.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        role = Role.objects.get(rolename="WithPerms")
        self.assertIn(perm, role.permissions.all())

    def test_create_role_as_employee_403(self):
        response = auth_client(self.employee).post(
            self.url, {"rolename": "Hacked"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ==================================================================
# ROLE DETAIL API TESTS (PUT / PATCH / DELETE)
# ==================================================================


@no_throttle
class RoleDetailAPITests(APITestCase):
    def setUp(self):
        self.admin = make_user("roledetail.admin@example.com", rolename="Admin")
        self.custom_role, _ = Role.objects.get_or_create(
            rolename="CustomRoleX", description="before"
        )

    def _url(self, role):
        return reverse("role_detail", kwargs={"role_id": role.role_id})

    # ---------------- PUT ----------------

    def test_update_role_description(self):
        response = auth_client(self.admin).put(
            self._url(self.custom_role),
            {"description": "after"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.custom_role.refresh_from_db()
        self.assertEqual(self.custom_role.description, "after")

    def test_update_admin_role_403(self):
        admin_role = Role.objects.get(rolename="Admin")
        response = auth_client(self.admin).put(
            self._url(admin_role), {"description": "hax"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_nonexistent_role_404(self):
        response = auth_client(self.admin).put(
            reverse("role_detail", kwargs={"role_id": 999999}),
            {"description": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_duplicate_rolename_400(self):
        Role.objects.get_or_create(rolename="OtherRole")
        response = auth_client(self.admin).put(
            self._url(self.custom_role), {"rolename": "OtherRole"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------------- PATCH ----------------
    # NOTE: RoleDetailAPIView.permission_names only maps PUT and DELETE,
    # so HasDynamicPermission denies every PATCH request with 403 before
    # the view body ("add permissions") is ever reached.

    def test_patch_add_permissions_to_role(self):
        perms = list(Permission.objects.filter(codename__in=["view_role"])[:1])
        response = auth_client(self.admin).patch(
            self._url(self.custom_role),
            {"permissions": [p.id for p in perms]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_admin_role_403(self):
        admin_role = Role.objects.get(rolename="Admin")
        perm = Permission.objects.first()
        response = auth_client(self.admin).patch(
            self._url(admin_role), {"permissions": [perm.id]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_missing_permissions_key_403(self):
        response = auth_client(self.admin).patch(
            self._url(self.custom_role), {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_invalid_permission_ids_403(self):
        response = auth_client(self.admin).patch(
            self._url(self.custom_role),
            {"permissions": [987654321]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_duplicate_permission_ids_403(self):
        perm = Permission.objects.filter(codename="view_role").first()
        response = auth_client(self.admin).patch(
            self._url(self.custom_role),
            {"permissions": [perm.id, perm.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_nonexistent_role_403(self):
        response = auth_client(self.admin).patch(
            reverse("role_detail", kwargs={"role_id": 999999}),
            {"permissions": []},
            format="json",
        )
        # Permission check happens before object lookup -> 403 not 404.
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---------------- DELETE ----------------

    def test_delete_custom_role(self):
        response = auth_client(self.admin).delete(self._url(self.custom_role))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "CustomRoleX")
        self.assertFalse(Role.objects.filter(pk=self.custom_role.pk).exists())

    def test_delete_default_role_403(self):
        for rolename in ["Admin", "Manager", "Employee"]:
            role = Role.objects.get(rolename=rolename)
            response = auth_client(self.admin).delete(self._url(role))
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_nonexistent_role_404(self):
        response = auth_client(self.admin).delete(
            reverse("role_detail", kwargs={"role_id": 999999})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_unauthenticated_401(self):
        response = APIClient().delete(self._url(self.custom_role))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ==================================================================
# ASSIGN ROLE API TESTS
# ==================================================================


@no_throttle
class AssignRoleAPITests(APITestCase):
    def setUp(self):
        self.assigner_role, _ = Role.objects.get_or_create(rolename="Assigner")
        self.assigner_role.permissions.add(get_custom_permission("assign_role"))
        self.assigner = make_user("assigner@example.com", rolename="Assigner")
        self.target = make_user("assign.target@example.com", rolename="Employee")
        self.new_role, _ = Role.objects.get_or_create(rolename="Manager")
        self.url = reverse("assign_role", kwargs={"user_id": self.target.user_id})

    def _put(self, client=None, url=None, data=None):
        client = client or auth_client(self.assigner)
        payload = {"role_id": self.new_role.role_id} if data is None else data
        return client.put(url or self.url, payload, format="json")

    def test_assign_role_success(self):
        response = self._put()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.target.refresh_from_db()
        self.assertEqual(self.target.role, self.new_role)
        self.assertEqual(response.data["role"], "Manager")
        self.assertEqual(response.data["user"], self.target.username)

    def test_missing_role_id_400(self):
        response = self._put(data={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "role_id is required.")

    def test_target_user_not_found_404(self):
        response = self._put(url=reverse("assign_role", kwargs={"user_id": uuid4()}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_role_not_found_404(self):
        response = self._put(data={"role_id": 999999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_change_admin_user_role_403(self):
        admin_user = make_user("target.admin@example.com", rolename="Admin")
        response = self._put(
            url=reverse("assign_role", kwargs={"user_id": admin_user.user_id})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_without_assign_role_permission_403(self):
        bare_role, _ = Role.objects.get_or_create(rolename="NoAssignPerm")
        weak_user = make_user("weak.assigner@example.com", rolename="NoAssignPerm")
        response = self._put(client=auth_client(weak_user))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_401(self):
        response = self._put(client=APIClient())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reassign_overrides_previous_role(self):
        self._put()  # Manager
        third_role, _ = Role.objects.get_or_create(rolename="ThirdRole")
        response = self._put(data={"role_id": third_role.role_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.target.refresh_from_db()
        self.assertEqual(self.target.role, third_role)


# ==================================================================
# PERMISSION LIST / CREATE API TESTS
# ==================================================================


@no_throttle
class PermissionListCreateAPITests(APITestCase):
    def setUp(self):
        self.admin = make_user("perms.admin@example.com", rolename="Admin")
        self.employee = make_user("perms.emp@example.com", rolename="Employee")
        self.url = reverse("permissions")

    def test_list_permissions_as_admin(self):
        response = auth_client(self.admin).get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["permissions"]), 0)

    def test_list_permissions_as_employee_403(self):
        response = auth_client(self.employee).get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_permissions_unauthenticated_401(self):
        response = APIClient().get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_permission_201(self):
        ct = ContentType.objects.get_for_model(Role)
        payload = {
            "name": "Can archive roles",
            "codename": "archive_rolex",
            "content_type": ct.id,
        }
        response = auth_client(self.admin).post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Permission.objects.filter(codename="archive_rolex").exists())

    def test_create_duplicate_permission_400(self):
        ct = ContentType.objects.get_for_model(Role)
        payload = {
            "name": "Can view role dup",
            "codename": "view_role",
            "content_type": ct.id,
        }
        response = auth_client(self.admin).post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_permission_missing_codename_400(self):
        ct = ContentType.objects.get_for_model(Role)
        response = auth_client(self.admin).post(
            self.url, {"name": "Incomplete", "content_type": ct.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ==================================================================
# PERMISSION DETAIL API TESTS (PUT / DELETE)
# ==================================================================


@no_throttle
class PermissionDetailAPITests(APITestCase):
    def setUp(self):
        self.admin = make_user("permdetail.admin@example.com", rolename="Admin")
        self.permission = Permission.objects.filter(codename="view_role").first()
        self.url = reverse(
            "permission_detail", kwargs={"permission_id": self.permission.id}
        )

    def test_update_permission_name(self):
        response = auth_client(self.admin).put(
            self.url, {"name": "Renamed permission"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.permission.refresh_from_db()
        self.assertEqual(self.permission.name, "Renamed permission")

    def test_update_nonexistent_permission_404(self):
        response = auth_client(self.admin).put(
            reverse("permission_detail", kwargs={"permission_id": 99999999}),
            {"name": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_invalid_payload_400(self):
        response = auth_client(self.admin).put(self.url, {"name": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_permission(self):
        ct = ContentType.objects.get_for_model(Role)
        temp_perm = Permission.objects.create(
            name="Temp delete me", codename="temp_delete_perm", content_type=ct
        )
        url = reverse("permission_detail", kwargs={"permission_id": temp_perm.id})
        response = auth_client(self.admin).delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Permission.objects.filter(pk=temp_perm.pk).exists())

    def test_delete_nonexistent_permission_404(self):
        response = auth_client(self.admin).delete(
            reverse("permission_detail", kwargs={"permission_id": 99999999})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_put_401(self):
        response = APIClient().put(self.url, {"name": "x"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ==================================================================
# FORGOT PASSWORD API TESTS
# ==================================================================


@no_throttle
class ForgotPasswordAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("forgot_password")
        self.user = make_user("forgot.pw@example.com", password="ForgotOld!12")

    def test_forgot_password_sends_otp_email(self):
        response = self.client.post(self.url, {"email": self.user.email}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_forgot_password_creates_otp_record(self):
        self.client.post(self.url, {"email": self.user.email}, format="json")
        self.assertEqual(self.user.password_reset_otps.filter(is_used=False).count(), 1)
        otp_record = self.user.password_reset_otps.first()
        self.assertEqual(len(otp_record.otp_hash), 64)  # sha256 hex digest

    def test_forgot_password_invalidates_previous_unused_otps(self):
        self.client.post(self.url, {"email": self.user.email}, format="json")
        self.client.post(self.url, {"email": self.user.email}, format="json")
        unused = self.user.password_reset_otps.filter(is_used=False)
        self.assertEqual(unused.count(), 1)
        self.assertEqual(self.user.password_reset_otps.count(), 2)

    def test_forgot_password_unknown_email_404(self):
        response = self.client.post(
            self.url, {"email": "unknown@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_forgot_password_inactive_user_404(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(self.url, {"email": self.user.email}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_forgot_password_invalid_payload_400(self):
        response = self.client.post(self.url, {"email": "not-an-email"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_forgot_password_missing_email_400(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_forgot_password_does_not_leak_existing_password(self):
        self.client.post(self.url, {"email": self.user.email}, format="json")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ForgotOld!12"))


# ==================================================================
# RESET PASSWORD API TESTS
# ==================================================================


@no_throttle
class ResetPasswordAPITests(APITestCase):
    NEW_PASSWORD = "BrandN3w!Pass"

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("reset_password")
        self.user = make_user("reset.pw@example.com", password="ResetOld!12")

    def _create_otp(self, otp="123456", minutes=10, used=False, attempts=0):
        record = PasswordResetOTP.objects.create(
            user=self.user,
            otp_hash=hash_otp(otp),
            expires_at=timezone.now() + timedelta(minutes=minutes),
            is_used=used,
            attempts=attempts,
        )
        return record

    def _reset(self, otp="123456", email=None, password=None):
        return self.client.post(
            self.url,
            {
                "email": email or self.user.email,
                "otp": otp,
                "new_password": password or self.NEW_PASSWORD,
            },
            format="json",
        )

    def test_reset_password_success(self):
        self._create_otp()
        response = self._reset()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.NEW_PASSWORD))

    def test_otp_marked_used_after_successful_reset(self):
        record = self._create_otp()
        self._reset()
        record.refresh_from_db()
        self.assertTrue(record.is_used)

    def test_otp_cannot_be_reused(self):
        self._create_otp()
        self._reset()
        second = self._reset(password="Another!Pass22")
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.NEW_PASSWORD))

    def test_wrong_otp_increments_attempts(self):
        record = self._create_otp(otp="111111")
        response = self._reset(otp="999999")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        record.refresh_from_db()
        self.assertEqual(record.attempts, 1)
        self.assertIn("attempt(s) remaining", response.data["error"])

    def test_too_many_attempts_locks_otp(self):
        record = self._create_otp(attempts=OTP_MAX_ATTEMPTS)
        response = self._reset(otp="111111")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Too many invalid attempts", response.data["error"])
        record.refresh_from_db()
        self.assertTrue(record.is_used)

    def test_final_wrong_attempt_exhausts_otp(self):
        record = self._create_otp(attempts=OTP_MAX_ATTEMPTS - 1)
        response = self._reset(otp="999999")
        self.assertIn("Too many invalid attempts", response.data["error"])
        record.refresh_from_db()
        self.assertTrue(record.is_used)

    def test_expired_otp_rejected(self):
        self._create_otp(minutes=-5)
        response = self._reset()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ResetOld!12"))

    def test_used_otp_rejected(self):
        self._create_otp(used=True)
        response = self._reset()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_otp_requested_rejected(self):
        response = self._reset()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_email_400(self):
        self._create_otp()
        response = self._reset(email="ghost@example.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_otp_of_different_user_rejected(self):
        other = make_user("other.reset@example.com")
        PasswordResetOTP.objects.create(
            user=other,
            otp_hash=hash_otp("121212"),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        response = self._reset(otp="121212")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_otp_format_400(self):
        self._create_otp()
        response = self._reset(otp="12345")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("otp", response.data)

    def test_weak_new_password_400(self):
        self._create_otp()
        response = self._reset(password="weak")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.data)

    def test_full_flow_forgot_then_reset_then_login(self):
        from unittest.mock import patch

        # Force a deterministic 6-digit OTP (424242) via secrets.randbelow.
        with patch(
            "accounts.views.secrets.randbelow",
            side_effect=iter([4, 2, 4, 2, 4, 2]),
        ):
            forgot = self.client.post(
                reverse("forgot_password"), {"email": self.user.email}, format="json"
            )
        self.assertEqual(forgot.status_code, status.HTTP_200_OK)

        record = self.user.password_reset_otps.filter(is_used=False).latest(
            "created_at"
        )
        self.assertEqual(record.otp_hash, hash_otp("424242"))

        reset = self._reset(otp="424242")
        self.assertEqual(reset.status_code, status.HTTP_200_OK)
        login = self.client.post(
            reverse("login"),
            {"email": self.user.email, "password": self.NEW_PASSWORD},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", login.data)

    def test_reset_password_missing_fields_400(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
