import uuid
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import CustomUser, Role
from accounts.permissions import HasDynamicPermission
from accounts.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogOutSerializer,
    ProfileSerializer,
    RegisterSerializer,
    RoleSerializer,
)

PERMISSION_CODENAMES = [
    "view_role",
    "add_role",
    "change_role",
    "delete_role",
    "view_permission",
    "add_permission",
    "change_permission",
    "delete_permission",
    "assign_role",
]


class AccountTestCase(APITestCase):
    def setUp(self):
        self.role_content_type = ContentType.objects.get_for_model(Role)
        self.employee_role = self._create_role("Employee")
        self.manager_role = self._create_role("Manager", ["view_role", "assign_role"])
        self.admin_role = self._create_role("Admin", PERMISSION_CODENAMES)

    def _create_role(self, rolename, codenames=()):
        role, _ = Role.objects.get_or_create(rolename=rolename)
        self._grant_permissions(role, codenames)
        return role

    def _grant_permissions(self, role, codenames):
        for codename in codenames:
            permission, _ = Permission.objects.get_or_create(
                content_type=self.role_content_type,
                codename=codename,
                defaults={"name": codename.replace("_", " ").title()},
            )
            role.permissions.add(permission)

    def _create_user(self, username, email, phone_number, password, role=None, **extra):
        return CustomUser.objects.create_user(
            username=username,
            email=email,
            phone_number=phone_number,
            password=password,
            role=role,
            **extra,
        )

    def _create_admin_user(self):
        return self._create_user(
            "admin",
            "admin@example.com",
            "9000000001",
            "AdminPass@123",
            role=self.admin_role,
        )

    def _create_manager_user(self):
        return self._create_user(
            "manager",
            "manager@example.com",
            "9000000002",
            "ManagerPass@123",
            role=self.manager_role,
        )

    def _create_employee_user(self):
        return self._create_user(
            "employee",
            "employee@example.com",
            "9000000003",
            "EmployeePass@123",
            role=self.employee_role,
        )

    def _create_plain_user(self, **kwargs):
        return self._create_user(**kwargs)

    def _auth(self, user):
        self.client.force_authenticate(user=user)


class CustomUserManagerTests(AccountTestCase):
    def test_create_user_success(self):
        user = self._create_user(
            "alice",
            "alice@example.com",
            "9111111111",
            "TestPass@123",
            role=self.employee_role,
        )
        self.assertIsInstance(user, CustomUser)
        self.assertEqual(user.email, "alice@example.com")
        self.assertTrue(user.check_password("TestPass@123"))
        self.assertFalse(user.check_password("WrongPass@123"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.role, self.employee_role)

    def test_create_user_normalizes_email_domain(self):
        user = self._create_user("bob", "Bob@Example.COM", "9111111112", "TestPass@123")
        self.assertEqual(user.email, "Bob@example.com")

    def test_create_user_without_email_raises_value_error(self):
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                username="bob", email=None, password="TestPass@123"
            )

    def test_create_user_defaults(self):
        user = self._create_user(
            "carol", "carol@example.com", "9111111113", "TestPass@123"
        )
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIsNone(user.role)

    def test_create_superuser_flags_and_admin_role(self):
        user = CustomUser.objects.create_superuser(
            "root", "root@example.com", "RootPass@123"
        )
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertEqual(user.role.rolename, "Admin")

    def test_create_superuser_gets_all_permissions(self):
        user = CustomUser.objects.create_superuser(
            "root2", "root2@example.com", "RootPass@123"
        )
        self.assertEqual(user.role.permissions.count(), Permission.objects.count())


class RoleModelTests(AccountTestCase):
    def test_role_str_returns_rolename(self):
        role = Role.objects.create(rolename="Support")
        self.assertEqual(str(role), "Support")


class CustomUserModelTests(AccountTestCase):
    def test_user_str_returns_email(self):
        user = self._create_user(
            "dave", "dave@example.com", "9111111114", "TestPass@123"
        )
        self.assertEqual(str(user), "dave@example.com")


class RegisterAPITests(AccountTestCase):
    def test_register_success_with_employee_role(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "phone_number": "9111111115",
                "password": "TestPass@123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "User registered successfully")
        user = CustomUser.objects.get(email="newuser@example.com")
        self.assertEqual(response.data["user_id"], str(user.user_id))
        self.assertTrue(user.check_password("TestPass@123"))
        self.assertEqual(user.role, self.employee_role)

    def test_register_invalid_email(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "bad",
                "email": "not-an-email",
                "phone_number": "9111111116",
                "password": "TestPass@123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields(self):
        response = self.client.post(reverse("register"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        self._create_user("taken", "taken@example.com", "9111111117", "TestPass@123")
        response = self.client.post(
            reverse("register"),
            {
                "username": "taken2",
                "email": "taken@example.com",
                "phone_number": "9111111118",
                "password": "TestPass@123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_phone(self):
        self._create_user("taken3", "taken3@example.com", "9111111119", "TestPass@123")
        response = self.client.post(
            reverse("register"),
            {
                "username": "newbie",
                "email": "newbie@example.com",
                "phone_number": "9111111119",
                "password": "TestPass@123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_when_employee_role_missing(self):
        Role.objects.filter(rolename="Employee").delete()
        response = self.client.post(
            reverse("register"),
            {
                "username": "mike",
                "email": "mike@example.com",
                "phone_number": "9111111140",
                "password": "TestPass@123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = CustomUser.objects.get(email="mike@example.com")
        self.assertIsNone(user.role)


class LoginAPITests(AccountTestCase):
    def _login(self, email, password):
        return self.client.post(
            reverse("login"), {"email": email, "password": password}, format="json"
        )

    def test_login_success_returns_tokens(self):
        self._create_user("joe", "joe@example.com", "9111111120", "TestPass@123")
        response = self._login("joe@example.com", "TestPass@123")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Login successful")
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)

    def test_login_wrong_password(self):
        self._create_user("joe", "joe@example.com", "9111111120", "TestPass@123")
        response = self._login("joe@example.com", "wrongpass")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["error"], "Invalid credentials")

    def test_login_unknown_email(self):
        response = self._login("ghost@example.com", "whatever")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["error"], "Invalid credentials")

    def test_login_inactive_user(self):
        user = self._create_user(
            "sleepy", "sleepy@example.com", "9111111121", "TestPass@123"
        )
        user.is_active = False
        user.save()
        response = self._login("sleepy@example.com", "TestPass@123")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_fields(self):
        response = self.client.post(
            reverse("login"), {"email": "x@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_invalid_email_format(self):
        response = self._login("not-an-email", "whatever")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutAPITests(AccountTestCase):
    def _token_pair(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token), str(refresh)

    def _logout(self, access, refresh_token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return self.client.post(
            reverse("logout"), {"refresh_token": refresh_token}, format="json"
        )

    def test_logout_success(self):
        user = self._create_user("joe", "joe@example.com", "9111111120", "TestPass@123")
        access, refresh = self._token_pair(user)
        response = self._logout(access, refresh)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Logout successful", response.data["message"])

    def test_logout_blacklists_refresh_token(self):
        user = self._create_user("joe", "joe@example.com", "9111111120", "TestPass@123")
        access, refresh = self._token_pair(user)
        self._logout(access, refresh)
        response = self.client.post(
            reverse("token_refresh"), {"refresh_token": refresh}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid refresh token")

    def test_logout_twice_returns_already_logged_out(self):
        user = self._create_user("joe", "joe@example.com", "9111111120", "TestPass@123")
        access, refresh = self._token_pair(user)
        self.assertEqual(self._logout(access, refresh).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self._logout(access, refresh).status_code, status.HTTP_400_BAD_REQUEST
        )

    def test_logout_missing_token(self):
        user = self._create_user("joe", "joe@example.com", "9111111120", "TestPass@123")
        access, _ = self._token_pair(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.post(reverse("logout"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_invalid_token(self):
        user = self._create_user("joe", "joe@example.com", "9111111120", "TestPass@123")
        access, _ = self._token_pair(user)
        response = self._logout(access, "not-a-token")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_unauthenticated(self):
        response = self.client.post(
            reverse("logout"), {"refresh_token": "x"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RefreshTokenAPITests(AccountTestCase):
    def test_refresh_success(self):
        user = self._create_user("joe", "joe@example.com", "9111111120", "TestPass@123")
        refresh = str(RefreshToken.for_user(user))
        response = self.client.post(
            reverse("token_refresh"), {"refresh_token": refresh}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Access token refreshed successfully"
        )
        self.assertIn("access_token", response.data)

    def test_refresh_returns_usable_access_token(self):
        user = self._create_user("joe", "joe@example.com", "9111111120", "TestPass@123")
        refresh = str(RefreshToken.for_user(user))
        response = self.client.post(
            reverse("token_refresh"), {"refresh_token": refresh}, format="json"
        )
        access = response.data["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        profile_response = self.client.get(
            reverse("profile", kwargs={"user_id": user.user_id})
        )
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)

    def test_refresh_invalid_token(self):
        response = self.client.post(
            reverse("token_refresh"), {"refresh_token": "garbage"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid refresh token")

    def test_refresh_missing_token(self):
        response = self.client.post(reverse("token_refresh"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ChangePasswordAPITests(AccountTestCase):
    def _change_password(self, user, payload):
        self._auth(user)
        return self.client.post(reverse("change_password"), payload, format="json")

    def test_change_password_success(self):
        user = self._create_user("joe", "joe@example.com", "9111111120", "TestPass@123")
        response = self._change_password(
            user,
            {"old_password": "TestPass@123", "new_password": "NewSecurePass@456"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewSecurePass@456"))
        self.assertFalse(user.check_password("TestPass@123"))

    def test_change_password_wrong_old_password(self):
        user = self._create_user("joe", "joe@example.com", "9111111120", "TestPass@123")
        response = self._change_password(
            user,
            {"old_password": "WrongPass@999", "new_password": "NewSecurePass@456"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Old password is incorrect.")

    def test_change_password_weak_new_password(self):
        user = self._create_user("joe", "joe@example.com", "9111111120", "TestPass@123")
        response = self._change_password(
            user, {"old_password": "TestPass@123", "new_password": "123"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_missing_fields(self):
        user = self._create_user("joe", "joe@example.com", "9111111120", "TestPass@123")
        response = self._change_password(user, {"old_password": "TestPass@123"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_unauthenticated(self):
        response = self.client.post(
            reverse("change_password"),
            {"old_password": "x", "new_password": "y"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProfileAPITests(AccountTestCase):
    def _get_profile(self, user, target_id):
        self._auth(user)
        return self.client.get(reverse("profile", kwargs={"user_id": target_id}))

    def test_profile_self(self):
        user = self._create_employee_user()
        response = self._get_profile(user, user.user_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["profile"]["email"], user.email)
        self.assertEqual(response.data["profile"]["role"], user.role.role_id)

    def test_profile_admin_views_other(self):
        admin = self._create_admin_user()
        employee = self._create_employee_user()
        response = self._get_profile(admin, employee.user_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_profile_manager_views_other(self):
        manager = self._create_manager_user()
        employee = self._create_employee_user()
        response = self._get_profile(manager, employee.user_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_profile_employee_cannot_view_other(self):
        employee = self._create_employee_user()
        other = self._create_plain_user(
            username="other",
            email="other@example.com",
            phone_number="9111111130",
            password="TestPass@123",
        )
        response = self._get_profile(employee, other.user_id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_profile_user_without_role_cannot_view_other(self):
        no_role = self._create_plain_user(
            username="norole",
            email="norole@example.com",
            phone_number="9111111131",
            password="TestPass@123",
        )
        employee = self._create_employee_user()
        response = self._get_profile(no_role, employee.user_id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_profile_not_found(self):
        admin = self._create_admin_user()
        response = self._get_profile(admin, uuid.uuid4())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_profile_unauthenticated(self):
        employee = self._create_employee_user()
        response = self.client.get(
            reverse("profile", kwargs={"user_id": employee.user_id})
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RoleAPITests(AccountTestCase):
    def test_roles_list_admin(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.get(reverse("roles"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Roles retrieved successfully.")
        self.assertEqual(len(response.data["roles"]), 3)

    def test_roles_list_manager(self):
        manager = self._create_manager_user()
        self._auth(manager)
        response = self.client.get(reverse("roles"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_roles_list_superuser(self):
        superuser = CustomUser.objects.create_superuser(
            "root", "root@example.com", "RootPass@123"
        )
        self._auth(superuser)
        response = self.client.get(reverse("roles"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_roles_list_employee_denied(self):
        employee = self._create_employee_user()
        self._auth(employee)
        response = self.client.get(reverse("roles"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_roles_list_employee_with_perm_still_denied(self):
        self._grant_permissions(self.employee_role, ["view_role"])
        employee = self._create_employee_user()
        self._auth(employee)
        response = self.client.get(reverse("roles"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["error"], "Only Admin and Manager can view roles."
        )

    def test_roles_list_user_without_role_denied(self):
        user = self._create_plain_user(
            username="norole",
            email="norole@example.com",
            phone_number="9111111131",
            password="TestPass@123",
        )
        self._auth(user)
        response = self.client.get(reverse("roles"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_roles_list_unauthenticated(self):
        response = self.client.get(reverse("roles"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_role_create_success(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.post(
            reverse("roles"), {"rolename": "Support"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Role created successfully.")
        self.assertTrue(Role.objects.filter(rolename="Support").exists())

    def test_role_create_with_permissions(self):
        admin = self._create_admin_user()
        self._auth(admin)
        permission = Permission.objects.create(
            name="View Invoices",
            codename="view_invoice",
            content_type=self.role_content_type,
        )
        response = self.client.post(
            reverse("roles"),
            {"rolename": "Support", "permissions": [permission.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Role.objects.get(rolename="Support").permissions.count(), 1)

    def test_role_create_duplicate_name(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.post(
            reverse("roles"), {"rolename": "Admin"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_role_create_denied_without_permission(self):
        manager = self._create_manager_user()
        self._auth(manager)
        response = self.client.post(
            reverse("roles"), {"rolename": "Support"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_role_update_success(self):
        admin = self._create_admin_user()
        self._auth(admin)
        role = Role.objects.create(rolename="Support", description="old")
        response = self.client.put(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {"description": "new"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        role.refresh_from_db()
        self.assertEqual(role.description, "new")

    def test_role_update_admin_protected(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.put(
            reverse("role_detail", kwargs={"role_id": self.admin_role.role_id}),
            {"rolename": "SuperAdmin"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "Admin role cannot be updated.")

    def test_role_update_not_found(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.put(
            reverse("role_detail", kwargs={"role_id": 99999}),
            {"description": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_role_update_duplicate_name(self):
        admin = self._create_admin_user()
        self._auth(admin)
        role = Role.objects.create(rolename="Support")
        response = self.client.put(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {"rolename": "Manager"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_role_delete_custom_success(self):
        admin = self._create_admin_user()
        self._auth(admin)
        role = Role.objects.create(rolename="Support")
        response = self.client.delete(
            reverse("role_detail", kwargs={"role_id": role.role_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Role.objects.filter(role_id=role.role_id).exists())

    def test_role_delete_default_protected(self):
        admin = self._create_admin_user()
        self._auth(admin)
        for role in [self.admin_role, self.manager_role, self.employee_role]:
            response = self.client.delete(
                reverse("role_detail", kwargs={"role_id": role.role_id})
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(response.data["error"], "Default roles cannot be deleted.")

    def test_role_delete_not_found(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.delete(reverse("role_detail", kwargs={"role_id": 99999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_role_patch_permissions_success(self):
        superuser = CustomUser.objects.create_superuser(
            "root", "root@example.com", "RootPass@123"
        )
        self._auth(superuser)
        role = Role.objects.create(rolename="Support")
        perm = Permission.objects.create(
            name="View Task",
            codename="view_task",
            content_type=self.role_content_type,
        )
        response = self.client.patch(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {"permissions": [perm.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Permissions added successfully.")
        role.refresh_from_db()
        self.assertIn(perm, role.permissions.all())

    def test_role_patch_admin_role_protected(self):
        superuser = CustomUser.objects.create_superuser(
            "root", "root@example.com", "RootPass@123"
        )
        self._auth(superuser)
        perm = Permission.objects.create(
            name="View Task",
            codename="view_task",
            content_type=self.role_content_type,
        )
        response = self.client.patch(
            reverse("role_detail", kwargs={"role_id": self.admin_role.role_id}),
            {"permissions": [perm.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "Admin role cannot be updated.")

    def test_role_patch_denied_for_admin_role_user(self):
        admin = self._create_admin_user()
        self._auth(admin)
        role = Role.objects.create(rolename="Support")
        perm = Permission.objects.create(
            name="View Task",
            codename="view_task",
            content_type=self.role_content_type,
        )
        response = self.client.patch(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {"permissions": [perm.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_role_patch_denied_for_manager(self):
        manager = self._create_manager_user()
        self._auth(manager)
        role = Role.objects.create(rolename="Support")
        perm = Permission.objects.create(
            name="View Task",
            codename="view_task",
            content_type=self.role_content_type,
        )
        response = self.client.patch(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {"permissions": [perm.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_role_patch_missing_permissions(self):
        superuser = CustomUser.objects.create_superuser(
            "root", "root@example.com", "RootPass@123"
        )
        self._auth(superuser)
        role = Role.objects.create(rolename="Support")
        response = self.client.patch(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "permissions is required.")

    def test_role_patch_invalid_permission_ids(self):
        superuser = CustomUser.objects.create_superuser(
            "root", "root@example.com", "RootPass@123"
        )
        self._auth(superuser)
        role = Role.objects.create(rolename="Support")
        response = self.client.patch(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {"permissions": [99999]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"], "One or more permission IDs are invalid."
        )

    def test_role_patch_not_found(self):
        superuser = CustomUser.objects.create_superuser(
            "root", "root@example.com", "RootPass@123"
        )
        self._auth(superuser)
        perm = Permission.objects.create(
            name="View Task",
            codename="view_task",
            content_type=self.role_content_type,
        )
        response = self.client.patch(
            reverse("role_detail", kwargs={"role_id": 99999}),
            {"permissions": [perm.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_role_patch_unauthenticated(self):
        role = Role.objects.create(rolename="Support")
        response = self.client.patch(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {"permissions": [1]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_role_update_rolename_only(self):
        admin = self._create_admin_user()
        self._auth(admin)
        role = Role.objects.create(rolename="Support", description="desc")
        response = self.client.put(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {"rolename": "NewSupport"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        role.refresh_from_db()
        self.assertEqual(role.rolename, "NewSupport")


class AssignRoleAPITests(AccountTestCase):
    def _assign(self, user, target_id, payload):
        self._auth(user)
        return self.client.put(
            reverse("assign_role", kwargs={"user_id": target_id}),
            payload,
            format="json",
        )

    def test_assign_role_success(self):
        manager = self._create_manager_user()
        target = self._create_employee_user()
        response = self._assign(
            manager, target.user_id, {"role_id": self.manager_role.role_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Role assigned successfully.")
        target.refresh_from_db()
        self.assertEqual(target.role, self.manager_role)

    def test_assign_role_to_admin_denied(self):
        manager = self._create_manager_user()
        admin = self._create_admin_user()
        response = self._assign(
            manager, admin.user_id, {"role_id": self.manager_role.role_id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "Admin role cannot be changed.")

    def test_assign_role_missing_role_id(self):
        manager = self._create_manager_user()
        target = self._create_employee_user()
        response = self._assign(manager, target.user_id, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "role_id is required.")

    def test_assign_role_role_not_found(self):
        manager = self._create_manager_user()
        target = self._create_employee_user()
        response = self._assign(manager, target.user_id, {"role_id": 99999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_assign_role_user_not_found(self):
        manager = self._create_manager_user()
        response = self._assign(
            manager, uuid.uuid4(), {"role_id": self.manager_role.role_id}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_assign_role_denied_without_permission(self):
        employee = self._create_employee_user()
        target = self._create_plain_user(
            username="t",
            email="t@example.com",
            phone_number="9111111132",
            password="TestPass@123",
        )
        response = self._assign(
            employee, target.user_id, {"role_id": self.manager_role.role_id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_assign_role_unauthenticated(self):
        target = self._create_employee_user()
        response = self.client.put(
            reverse("assign_role", kwargs={"user_id": target.user_id}),
            {"role_id": 1},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PermissionAPITests(AccountTestCase):
    def _payload(self, suffix):
        return {
            "name": f"Custom Permission {suffix}",
            "codename": f"custom_perm_{suffix}",
            "content_type": self.role_content_type.id,
        }

    def test_permissions_list_success(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.get(reverse("permissions"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Permissions retrieved successfully."
        )

    def test_permissions_list_denied(self):
        employee = self._create_employee_user()
        self._auth(employee)
        response = self.client.get(reverse("permissions"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_permissions_list_unauthenticated(self):
        response = self.client.get(reverse("permissions"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_permission_create_success(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.post(
            reverse("permissions"), self._payload(1), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Permission.objects.filter(codename="custom_perm_1").exists())

    def test_permission_create_duplicate_codename(self):
        admin = self._create_admin_user()
        self._auth(admin)
        payload = self._payload(2)
        self.client.post(reverse("permissions"), payload, format="json")
        response = self.client.post(reverse("permissions"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_permission_create_invalid_content_type(self):
        admin = self._create_admin_user()
        self._auth(admin)
        payload = self._payload(3)
        payload["content_type"] = 99999
        response = self.client.post(reverse("permissions"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_permission_update_success(self):
        admin = self._create_admin_user()
        self._auth(admin)
        payload = self._payload(4)
        payload["content_type"] = self.role_content_type
        permission = Permission.objects.create(**payload)
        response = self.client.put(
            reverse("permission_detail", kwargs={"permission_id": permission.id}),
            {"name": "Updated Name"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        permission.refresh_from_db()
        self.assertEqual(permission.name, "Updated Name")

    def test_permission_update_not_found(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.put(
            reverse("permission_detail", kwargs={"permission_id": 99999}),
            {"name": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_permission_delete_success(self):
        admin = self._create_admin_user()
        self._auth(admin)
        payload = self._payload(5)
        payload["content_type"] = self.role_content_type
        permission = Permission.objects.create(**payload)
        response = self.client.delete(
            reverse("permission_detail", kwargs={"permission_id": permission.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Permission.objects.filter(id=permission.id).exists())

    def test_permission_delete_not_found(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.delete(
            reverse("permission_detail", kwargs={"permission_id": 99999})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class HasDynamicPermissionTests(AccountTestCase):
    class FakeView:
        permission_names = {"GET": "view_role"}

    def _call_permission(self, user, method="GET"):
        request = APIRequestFactory().request()
        request.method = method
        request.user = user
        return HasDynamicPermission().has_permission(request, self.FakeView())

    def test_anonymous_user_denied(self):
        self.assertFalse(self._call_permission(AnonymousUser()))

    def test_superuser_allowed(self):
        superuser = CustomUser.objects.create_superuser(
            "root", "root@example.com", "RootPass@123"
        )
        self.assertTrue(self._call_permission(superuser))

    def test_user_without_role_denied(self):
        user = self._create_plain_user(
            username="norole",
            email="norole@example.com",
            phone_number="9111111131",
            password="TestPass@123",
        )
        self.assertFalse(self._call_permission(user))

    def test_user_with_role_lacking_permission_denied(self):
        employee = self._create_employee_user()
        self.assertFalse(self._call_permission(employee))

    def test_user_with_role_having_permission_allowed(self):
        admin = self._create_admin_user()
        self.assertTrue(self._call_permission(admin))

    def test_method_not_mapped_denied(self):
        admin = self._create_admin_user()
        self.assertFalse(self._call_permission(admin, method="PATCH"))


class SerializerTests(AccountTestCase):
    def test_login_serializer_valid(self):
        serializer = LoginSerializer(data={"email": "a@b.com", "password": "x"})
        self.assertTrue(serializer.is_valid())

    def test_login_serializer_invalid_email(self):
        serializer = LoginSerializer(data={"email": "nope", "password": "x"})
        self.assertFalse(serializer.is_valid())

    def test_logout_serializer_requires_token(self):
        serializer = LogOutSerializer(data={"refresh_token": ""})
        self.assertFalse(serializer.is_valid())

    def test_register_serializer_invalid(self):
        serializer = RegisterSerializer(data={"username": "x"})
        self.assertFalse(serializer.is_valid())

    def test_change_password_serializer_rejects_weak_password(self):
        serializer = ChangePasswordSerializer(
            data={"old_password": "OldPass@123", "new_password": "123"}
        )
        self.assertFalse(serializer.is_valid())

    def test_role_serializer_valid(self):
        serializer = RoleSerializer(data={"rolename": "Support"})
        self.assertTrue(serializer.is_valid())

    def test_profile_serializer_fields(self):
        user = self._create_employee_user()
        data = ProfileSerializer(user).data
        self.assertEqual(
            set(data.keys()),
            {
                "user_id",
                "username",
                "email",
                "phone_number",
                "role",
                "created_at",
                "updated_at",
            },
        )


# ==========================================================
# REGISTER EDGE CASE TESTS
# ==========================================================


class RegisterEdgeCaseTests(AccountTestCase):
    def test_register_with_weak_password(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "weakpass",
                "email": "weakpass@example.com",
                "phone_number": "9222222201",
                "password": "123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_register_returns_user_id(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "checkid",
                "email": "checkid@example.com",
                "phone_number": "9222222202",
                "password": "TestPass@123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user_id", response.data)
        self.assertIn("email", response.data)
        self.assertIn("username", response.data)

    def test_register_sets_employee_role(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "empcheck",
                "email": "empcheck@example.com",
                "phone_number": "9222222203",
                "password": "TestPass@123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = CustomUser.objects.get(email="empcheck@example.com")
        self.assertEqual(user.role.rolename, "Employee")


# ==========================================================
# LOGIN EDGE CASE TESTS
# ==========================================================


class LoginEdgeCaseTests(AccountTestCase):
    def test_login_empty_password(self):
        self._create_user(
            "emptypass", "emptypass@example.com", "9222222210", "TestPass@123"
        )
        response = self.client.post(
            reverse("login"),
            {"email": "emptypass@example.com", "password": ""},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_returns_user_info(self):
        self._create_user(
            "infocheck", "infocheck@example.com", "9222222211", "TestPass@123"
        )
        response = self.client.post(
            reverse("login"),
            {"email": "infocheck@example.com", "password": "TestPass@123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertIn("message", response.data)


# ==========================================================
# LOGOUT EDGE CASE TESTS
# ==========================================================


class LogoutEdgeCaseTests(AccountTestCase):
    def _token_pair(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token), str(refresh)

    def test_logout_missing_refresh_token_field(self):
        user = self._create_user(
            "nomissing", "nomissing@example.com", "9222222220", "TestPass@123"
        )
        access, _ = self._token_pair(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.post(
            reverse("logout"), {"wrong_field": "x"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ==========================================================
# REFRESH TOKEN EDGE CASE TESTS
# ==========================================================


class RefreshTokenEdgeCaseTests(AccountTestCase):
    def test_refresh_missing_body(self):
        response = self.client.post(reverse("token_refresh"), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ==========================================================
# CHANGE PASSWORD EDGE CASE TESTS
# ==========================================================


class ChangePasswordEdgeCaseTests(AccountTestCase):
    def _change_password(self, user, payload):
        self._auth(user)
        return self.client.post(reverse("change_password"), payload, format="json")

    def test_change_password_same_as_old(self):
        user = self._create_user(
            "sameold", "sameold@example.com", "9222222230", "TestPass@123"
        )
        response = self._change_password(
            user,
            {"old_password": "TestPass@123", "new_password": "TestPass@123"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_change_password_success_message(self):
        user = self._create_user(
            "changemsg", "changemsg@example.com", "9222222231", "TestPass@123"
        )
        response = self._change_password(
            user,
            {"old_password": "TestPass@123", "new_password": "NewSecurePass@456"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Password changed successfully.")

    def test_change_password_empty_new_password(self):
        user = self._create_user(
            "emptynew", "emptynew@example.com", "9222222232", "TestPass@123"
        )
        response = self._change_password(
            user,
            {"old_password": "TestPass@123", "new_password": ""},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ==========================================================
# PROFILE EDGE CASE TESTS
# ==========================================================


class ProfileEdgeCaseTests(AccountTestCase):
    def _get_profile(self, user, target_id):
        self._auth(user)
        return self.client.get(reverse("profile", kwargs={"user_id": target_id}))

    def test_profile_returns_correct_fields(self):
        user = self._create_employee_user()
        response = self._get_profile(user, user.user_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("profile", response.data)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "Profile retrieved successfully.")

    def test_profile_user_without_role_can_view_self(self):
        user = self._create_plain_user(
            username="selfview",
            email="selfview@example.com",
            phone_number="9222222240",
            password="TestPass@123",
        )
        response = self._get_profile(user, user.user_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ==========================================================
# ROLE API EDGE CASE TESTS
# ==========================================================


class RoleAPIEdgeCaseTests(AccountTestCase):
    def test_role_create_empty_rolename(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.post(reverse("roles"), {"rolename": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_role_update_empty_body(self):
        admin = self._create_admin_user()
        self._auth(admin)
        role = Role.objects.create(rolename="Support")
        response = self.client.put(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_role_list_returns_role_count(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.get(reverse("roles"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("roles", response.data)
        self.assertIsInstance(response.data["roles"], list)

    def test_role_create_success_response_message(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.post(reverse("roles"), {"rolename": "QA"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Role created successfully.")

    def test_role_delete_custom_response_message(self):
        admin = self._create_admin_user()
        self._auth(admin)
        role = Role.objects.create(rolename="Temp")
        response = self.client.delete(
            reverse("role_detail", kwargs={"role_id": role.role_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Role deleted successfully.")

    def test_role_patch_returns_role_data(self):
        superuser = CustomUser.objects.create_superuser(
            "root", "root@example.com", "RootPass@123"
        )
        self._auth(superuser)
        role = Role.objects.create(rolename="Patched")
        perm = Permission.objects.create(
            name="View Task",
            codename="view_task",
            content_type=self.role_content_type,
        )
        response = self.client.patch(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {"permissions": [perm.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("role", response.data)


# ==========================================================
# ASSIGN ROLE NOTIFICATION INTEGRATION TESTS
# ==========================================================


class AssignRoleNotificationTests(AccountTestCase):
    def _assign(self, user, target_id, payload):
        self._auth(user)
        return self.client.put(
            reverse("assign_role", kwargs={"user_id": target_id}),
            payload,
            format="json",
        )

    def test_assign_role_triggers_notification(self):
        from Notification.models import Notification, NotificationEventType

        manager = self._create_manager_user()
        target = self._create_employee_user()
        response = self._assign(
            manager, target.user_id, {"role_id": self.manager_role.role_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notif = Notification.objects.filter(
            recipient=target,
            event_type=NotificationEventType.ROLE_CHANGED,
        ).first()
        self.assertIsNotNone(notif)

    def test_assign_role_notification_contains_role_name(self):
        from Notification.models import Notification, NotificationEventType

        manager = self._create_manager_user()
        target = self._create_employee_user()
        response = self._assign(
            manager, target.user_id, {"role_id": self.manager_role.role_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notif = Notification.objects.filter(
            recipient=target,
            event_type=NotificationEventType.ROLE_CHANGED,
        ).first()
        self.assertIn("Manager", notif.message)

    def test_assign_role_success_response_fields(self):
        manager = self._create_manager_user()
        target = self._create_employee_user()
        response = self._assign(
            manager, target.user_id, {"role_id": self.manager_role.role_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user", response.data)
        self.assertIn("role", response.data)
        self.assertEqual(response.data["user"], target.username)


# ==========================================================
# PERMISSION API EDGE CASE TESTS
# ==========================================================


class PermissionAPIEdgeCaseTests(AccountTestCase):
    def _payload(self, suffix):
        return {
            "name": f"Custom Permission {suffix}",
            "codename": f"custom_perm_{suffix}",
            "content_type": self.role_content_type.id,
        }

    def test_permission_create_missing_fields(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.post(reverse("permissions"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_permission_create_success_response_message(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.post(
            reverse("permissions"),
            self._payload(100),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Permission created successfully.")

    def test_permission_update_success_response_message(self):
        admin = self._create_admin_user()
        self._auth(admin)
        perm = Permission.objects.create(
            name="Updatable",
            codename="updatable_perm",
            content_type=self.role_content_type,
        )
        response = self.client.put(
            reverse("permission_detail", kwargs={"permission_id": perm.id}),
            {"name": "Updated"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Permission updated successfully.")

    def test_permission_delete_success_response_message(self):
        admin = self._create_admin_user()
        self._auth(admin)
        perm = Permission.objects.create(
            name="Deletable",
            codename="deletable_perm",
            content_type=self.role_content_type,
        )
        response = self.client.delete(
            reverse("permission_detail", kwargs={"permission_id": perm.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Permission deleted successfully.")

    def test_permission_list_returns_permissions_key(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.get(reverse("permissions"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("permissions", response.data)

    def test_permission_create_duplicate_content_type(self):
        admin = self._create_admin_user()
        self._auth(admin)
        payload1 = self._payload(200)
        payload1["content_type"] = self.role_content_type.id
        self.client.post(reverse("permissions"), payload1, format="json")
        payload2 = self._payload(200)
        payload2["content_type"] = self.role_content_type.id
        response = self.client.post(reverse("permissions"), payload2, format="json")
        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR],
        )

    def test_permission_update_preserves_codename(self):
        admin = self._create_admin_user()
        self._auth(admin)
        perm = Permission.objects.create(
            name="Original",
            codename="preserve_codename_perm",
            content_type=self.role_content_type,
        )
        self.client.put(
            reverse("permission_detail", kwargs={"permission_id": perm.id}),
            {"name": "New Name"},
            format="json",
        )
        perm.refresh_from_db()
        self.assertEqual(perm.codename, "preserve_codename_perm")


# ==========================================================
# HAS DYNAMIC PERMISSION EDGE CASE TESTS
# ==========================================================


class HasDynamicPermissionEdgeCaseTests(AccountTestCase):
    class FakeView:
        permission_names = {"GET": "view_role"}

    class FakeViewNoPermNames:
        pass

    class FakeViewPermNameString:
        permission_name = "view_role"

    def _call_permission(self, user, view=None, method="GET"):
        if view is None:
            view = self.FakeView()
        request = APIRequestFactory().request()
        request.method = method
        request.user = user
        return HasDynamicPermission().has_permission(request, view)

    def test_view_without_permission_names_denied(self):
        employee = self._create_employee_user()
        result = self._call_permission(employee, view=self.FakeViewNoPermNames())
        self.assertFalse(result)

    def test_view_with_permission_name_string(self):
        admin = self._create_admin_user()
        result = self._call_permission(admin, view=self.FakeViewPermNameString())
        self.assertTrue(result)

    def test_manager_with_matching_perm(self):
        manager = self._create_manager_user()
        result = self._call_permission(manager)
        self.assertTrue(result)

    def test_employee_without_matching_perm_denied(self):
        employee = self._create_employee_user()
        result = self._call_permission(employee)
        self.assertFalse(result)


# ==========================================================
# CUSTOM USER MODEL EDGE CASE TESTS
# ==========================================================


class CustomUserModelEdgeCaseTests(AccountTestCase):
    def test_user_uuid_is_unique(self):
        user1 = self._create_user("u1", "u1@example.com", "9333333301", "TestPass@123")
        user2 = self._create_user("u2", "u2@example.com", "9333333302", "TestPass@123")
        self.assertNotEqual(user1.user_id, user2.user_id)

    def test_user_role_set_null_on_delete(self):
        role = Role.objects.create(rolename="ToDelete")
        user = self._create_user(
            "delrole", "delrole@example.com", "9333333303", "TestPass@123", role=role
        )
        self.assertEqual(user.role, role)
        role.delete()
        user.refresh_from_db()
        self.assertIsNone(user.role)

    def test_user_default_is_active(self):
        user = self._create_user(
            "active", "active@example.com", "9333333304", "TestPass@123"
        )
        self.assertTrue(user.is_active)

    def test_user_email_is_username_field(self):
        self.assertEqual(CustomUser.USERNAME_FIELD, "email")

    def test_user_required_fields(self):
        self.assertIn("username", CustomUser.REQUIRED_FIELDS)

    def test_superuser_is_staff(self):
        user = CustomUser.objects.create_superuser(
            "staff", "staff@example.com", "StaffPass@123"
        )
        self.assertTrue(user.is_staff)

    def test_superuser_is_active(self):
        user = CustomUser.objects.create_superuser(
            "active", "active@example.com", "ActivePass@123"
        )
        self.assertTrue(user.is_active)


# ==========================================================
# ROLE MODEL EDGE CASE TESTS
# ==========================================================


class RoleModelEdgeCaseTests(AccountTestCase):
    def test_role_unique_constraint(self):
        Role.objects.create(rolename="Unique")
        with self.assertRaises(Exception):
            Role.objects.create(rolename="Unique")

    def test_role_description_nullable(self):
        role = Role.objects.create(rolename="NoDesc")
        self.assertIsNone(role.description)

    def test_role_description_allows_text(self):
        role = Role.objects.create(rolename="DescRole", description="A" * 500)
        self.assertEqual(len(role.description), 500)

    def test_role_permissions_many_to_many(self):
        role = Role.objects.create(rolename="PermRole")
        perm1 = Permission.objects.create(
            name="P1", codename="p1_test", content_type=self.role_content_type
        )
        perm2 = Permission.objects.create(
            name="P2", codename="p2_test", content_type=self.role_content_type
        )
        role.permissions.add(perm1, perm2)
        self.assertEqual(role.permissions.count(), 2)

    def test_role_str_returns_rolename(self):
        role = Role.objects.create(rolename="TestStr")
        self.assertEqual(str(role), "TestStr")


# ==========================================================
# SIGNALS TESTS
# ==========================================================


class SignalsTests(AccountTestCase):
    def test_seed_permissions_creates_admin_permissions(self):
        from accounts.signals import seed_default_role_permissions

        Permission.objects.all().delete()
        Role.objects.all().delete()
        seed_default_role_permissions(sender=None)
        admin = Role.objects.get(rolename="Admin")
        self.assertEqual(admin.permissions.count(), Permission.objects.count())

    def test_seed_permissions_creates_manager_permissions(self):
        from accounts.signals import seed_default_role_permissions
        from accounts.signals import MANAGER_CODENAMES

        Permission.objects.all().delete()
        Role.objects.all().delete()
        seed_default_role_permissions(sender=None)
        manager = Role.objects.get(rolename="Manager")
        perm_codenames = set(manager.permissions.values_list("codename", flat=True))
        self.assertTrue(MANAGER_CODENAMES.issubset(perm_codenames))

    def test_seed_permissions_creates_employee_permissions(self):
        from accounts.signals import seed_default_role_permissions
        from accounts.signals import EMPLOYEE_CODENAMES

        Permission.objects.all().delete()
        Role.objects.all().delete()
        seed_default_role_permissions(sender=None)
        employee = Role.objects.get(rolename="Employee")
        perm_codenames = set(employee.permissions.values_list("codename", flat=True))
        self.assertTrue(EMPLOYEE_CODENAMES.issubset(perm_codenames))

    def test_seed_permissions_is_idempotent(self):
        from accounts.signals import seed_default_role_permissions

        seed_default_role_permissions(sender=None)
        count1 = Role.objects.get(rolename="Manager").permissions.count()
        seed_default_role_permissions(sender=None)
        count2 = Role.objects.get(rolename="Manager").permissions.count()
        self.assertEqual(count1, count2)

    def test_signal_runs_on_migrate(self):
        from accounts.signals import MANAGER_CODENAMES

        manager = Role.objects.get(rolename="Manager")
        perm_codenames = set(manager.permissions.values_list("codename", flat=True))
        self.assertTrue(MANAGER_CODENAMES.issubset(perm_codenames))


# ==========================================================
# CUSTOM USER MANAGER EDGE CASE TESTS
# ==========================================================


class CustomUserManagerEdgeCaseTests(AccountTestCase):
    def test_create_superuser_existing_admin_role_reuses(self):
        Role.objects.get_or_create(rolename="Admin")
        user = CustomUser.objects.create_superuser(
            "reuse", "reuse@example.com", "ReusePass@123"
        )
        self.assertEqual(user.role.rolename, "Admin")
        self.assertEqual(Role.objects.filter(rolename="Admin").count(), 1)

    def test_create_user_with_extra_fields(self):
        user = CustomUser.objects.create_user(
            "extra",
            "extra@example.com",
            "ExtraPass@123",
            phone_number="9444444401",
            first_name="Extra",
        )
        self.assertEqual(user.first_name, "Extra")

    def test_create_user_sets_password_hash(self):
        user = CustomUser.objects.create_user(
            "hash", "hash@example.com", "HashPass@123"
        )
        self.assertTrue(user.check_password("HashPass@123"))
        self.assertFalse(user.has_usable_password() is False)

    def test_create_superuser_sets_admin_role(self):
        user = CustomUser.objects.create_superuser(
            "adm", "adm@example.com", "AdmPass@123"
        )
        self.assertEqual(user.role.rolename, "Admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


# ==========================================================
# VIEW EXCEPTION PATH TESTS
# ==========================================================


class ViewExceptionPathTests(AccountTestCase):
    @patch("accounts.views.RefreshToken")
    def test_logout_token_blacklist_exception(self, mock_token_cls):

        mock_instance = mock_token_cls.return_value
        mock_instance.blacklist.side_effect = Exception("Blacklist failed")
        user = self._create_user(
            "blkerr", "blkerr@example.com", "9555555501", "TestPass@123"
        )
        refresh = RefreshToken.for_user(user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}"
        )
        response = self.client.post(
            reverse("logout"), {"refresh_token": str(refresh)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.views.CustomUser.objects")
    def test_login_user_get_exception(self, mock_manager):
        mock_manager.get.side_effect = Exception("DB error")
        response = self.client.post(
            reverse("login"),
            {"email": "x@example.com", "password": "y"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_register_serializer_exception_returns_500(self):
        with patch(
            "accounts.serializers.CustomUser.objects.create_user",
            side_effect=Exception("DB fail"),
        ):
            response = self.client.post(
                reverse("register"),
                {
                    "username": "failuser",
                    "email": "failuser@example.com",
                    "phone_number": "9555555502",
                    "password": "TestPass@123",
                },
                format="json",
            )
            self.assertEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @patch("accounts.views.Role.objects")
    def test_role_create_exception_returns_500(self, mock_objects):
        admin = self._create_admin_user()
        self._auth(admin)
        mock_objects.prefetch_related.return_value.order_by.side_effect = Exception(
            "DB fail"
        )
        response = self.client.get(reverse("roles"))
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch("accounts.views.Role.objects")
    def test_role_list_exception_returns_500(self, mock_objects):
        admin = self._create_admin_user()
        self._auth(admin)
        mock_objects.prefetch_related.return_value.order_by.side_effect = Exception(
            "DB fail"
        )
        response = self.client.get(reverse("roles"))
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch("accounts.views.get_object_or_404")
    def test_assign_role_user_save_exception(self, mock_get):
        from accounts.models import CustomUser as CU

        target = self._create_user(
            "savefail", "savefail@example.com", "9555555503", "TestPass@123"
        )
        manager = self._create_manager_user()
        original_get = mock_get.return_value

        with patch.object(CU, "save", side_effect=Exception("DB fail")):
            self._auth(manager)
            response = self.client.put(
                reverse("assign_role", kwargs={"user_id": target.user_id}),
                {"role_id": self.manager_role.role_id},
                format="json",
            )
            self.assertEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ==========================================================
# ROLE SERIALIZER EDGE CASE TESTS
# ==========================================================


class RoleSerializerTests(AccountTestCase):
    def test_role_serializer_create(self):
        data = {"rolename": "Developer"}
        serializer = RoleSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        role = serializer.save()
        self.assertEqual(role.rolename, "Developer")

    def test_role_serializer_update(self):
        role = Role.objects.create(rolename="OldName")
        serializer = RoleSerializer(role, data={"rolename": "NewName"}, partial=True)
        self.assertTrue(serializer.is_valid())
        updated = serializer.save()
        self.assertEqual(updated.rolename, "NewName")

    def test_role_list_serializer_fields(self):
        role = Role.objects.create(rolename="TestRole")
        data = RoleSerializer(role).data
        self.assertIn("role_id", data)
        self.assertIn("rolename", data)
        self.assertIn("permissions", data)

    def test_role_serializer_empty_rolename_invalid(self):
        serializer = RoleSerializer(data={"rolename": ""})
        self.assertFalse(serializer.is_valid())

    def test_role_serializer_permissions_optional(self):
        serializer = RoleSerializer(data={"rolename": "NoPerms"})
        self.assertTrue(serializer.is_valid())


# ==========================================================
# REGISTER SERIALIZER TESTS
# ==========================================================


class RegisterSerializerTests(AccountTestCase):
    def test_register_serializer_create_with_employee_role(self):
        serializer = RegisterSerializer(
            data={
                "username": "seruser",
                "email": "seruser@example.com",
                "phone_number": "9666666601",
                "password": "TestPass@123",
            }
        )
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.role.rolename, "Employee")

    def test_register_serializer_create_without_employee_role(self):
        Role.objects.filter(rolename="Employee").delete()
        serializer = RegisterSerializer(
            data={
                "username": "noroleuser",
                "email": "noroleuser@example.com",
                "phone_number": "9666666602",
                "password": "TestPass@123",
            }
        )
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertIsNone(user.role)

    def test_register_serializer_fields(self):
        serializer = RegisterSerializer(
            data={
                "username": "fieldchk",
                "email": "fieldchk@example.com",
                "phone_number": "9666666603",
                "password": "TestPass@123",
            }
        )
        self.assertTrue(serializer.is_valid())
        data = serializer.data
        self.assertIn("username", data)
        self.assertIn("email", data)
        self.assertNotIn("password", data)


# ==========================================================
# PROFILE VIEW ADDITIONAL TESTS
# ==========================================================


class ProfileViewAdditionalTests(AccountTestCase):
    def _get_profile(self, user, target_id):
        self._auth(user)
        return self.client.get(reverse("profile", kwargs={"user_id": target_id}))

    def test_profile_user_without_role_views_self(self):
        user = self._create_plain_user(
            username="selfview2",
            email="selfview2@example.com",
            phone_number="9777777701",
            password="TestPass@123",
        )
        response = self._get_profile(user, user.user_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_profile_admin_views_employee(self):
        admin = self._create_admin_user()
        emp = self._create_employee_user()
        response = self._get_profile(admin, emp.user_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["profile"]["email"], emp.email)

    def test_profile_manager_views_employee(self):
        mgr = self._create_manager_user()
        emp = self._create_employee_user()
        response = self._get_profile(mgr, emp.user_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_profile_not_found(self):
        admin = self._create_admin_user()
        response = self._get_profile(admin, uuid.uuid4())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_profile_unauthenticated(self):
        emp = self._create_employee_user()
        response = self.client.get(reverse("profile", kwargs={"user_id": emp.user_id}))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ==========================================================
# ASSIGN ROLE ADDITIONAL TESTS
# ==========================================================


class AssignRoleAdditionalTests(AccountTestCase):
    def _assign(self, user, target_id, payload):
        self._auth(user)
        return self.client.put(
            reverse("assign_role", kwargs={"user_id": target_id}),
            payload,
            format="json",
        )

    def test_assign_same_role_again(self):
        mgr = self._create_manager_user()
        target = self._create_employee_user()
        response = self._assign(
            mgr, target.user_id, {"role_id": self.employee_role.role_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        target.refresh_from_db()
        self.assertEqual(target.role, self.employee_role)

    def test_assign_role_to_self(self):
        mgr = self._create_manager_user()
        response = self._assign(
            mgr, mgr.user_id, {"role_id": self.employee_role.role_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mgr.refresh_from_db()
        self.assertEqual(mgr.role, self.employee_role)

    def test_assign_role_removes_existing_role(self):
        mgr = self._create_manager_user()
        target = self._create_employee_user()
        self._assign(mgr, target.user_id, {"role_id": self.manager_role.role_id})
        target.refresh_from_db()
        self.assertEqual(target.role, self.manager_role)

    def test_assign_role_unauthenticated(self):
        target = self._create_employee_user()
        response = self.client.put(
            reverse("assign_role", kwargs={"user_id": target.user_id}),
            {"role_id": self.manager_role.role_id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_assign_role_user_not_found(self):
        mgr = self._create_manager_user()
        response = self._assign(
            mgr, uuid.uuid4(), {"role_id": self.manager_role.role_id}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_assign_role_role_not_found(self):
        mgr = self._create_manager_user()
        target = self._create_employee_user()
        response = self._assign(mgr, target.user_id, {"role_id": 99999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_assign_role_missing_role_id(self):
        mgr = self._create_manager_user()
        target = self._create_employee_user()
        response = self._assign(mgr, target.user_id, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ==========================================================
# PERMISSION VIEW ADDITIONAL TESTS
# ==========================================================


class PermissionViewAdditionalTests(AccountTestCase):
    def _payload(self, suffix):
        return {
            "name": f"Custom Permission {suffix}",
            "codename": f"custom_perm_add_{suffix}",
            "content_type": self.role_content_type.id,
        }

    def test_permission_create_success_response_fields(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.post(
            reverse("permissions"), self._payload(500), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("permission", response.data)
        self.assertIn("message", response.data)

    def test_permission_update_returns_data(self):
        admin = self._create_admin_user()
        self._auth(admin)
        perm = Permission.objects.create(
            name="OldData",
            codename="old_data_perm",
            content_type=self.role_content_type,
        )
        response = self.client.put(
            reverse("permission_detail", kwargs={"permission_id": perm.id}),
            {"name": "NewData"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("permission", response.data)

    def test_permission_delete_returns_message(self):
        admin = self._create_admin_user()
        self._auth(admin)
        perm = Permission.objects.create(
            name="DeleteMe",
            codename="del_me_perm",
            content_type=self.role_content_type,
        )
        response = self.client.delete(
            reverse("permission_detail", kwargs={"permission_id": perm.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_permission_list_unauthenticated(self):
        response = self.client.get(reverse("permissions"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_permission_create_manager_denied(self):
        mgr = self._create_manager_user()
        self._auth(mgr)
        response = self.client.post(
            reverse("permissions"), self._payload(600), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_permission_update_not_found(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.put(
            reverse("permission_detail", kwargs={"permission_id": 99999}),
            {"name": "X"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_permission_delete_not_found(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.delete(
            reverse("permission_detail", kwargs={"permission_id": 99999})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ==========================================================
# ROLE VIEW ADDITIONAL TESTS
# ==========================================================


class RoleViewAdditionalTests(AccountTestCase):
    def test_role_update_duplicate_name_returns_400(self):
        admin = self._create_admin_user()
        self._auth(admin)
        Role.objects.create(rolename="Existing")
        response = self.client.put(
            reverse("role_detail", kwargs={"role_id": self.employee_role.role_id}),
            {"rolename": "Existing"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_role_patch_empty_permissions_list(self):
        superuser = CustomUser.objects.create_superuser(
            "root3", "root3@example.com", "RootPass@123"
        )
        self._auth(superuser)
        role = Role.objects.create(rolename="PatchEmpty")
        response = self.client.patch(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {"permissions": []},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_role_patch_unauthenticated(self):
        role = Role.objects.create(rolename="UnauthPatch")
        response = self.client.patch(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {"permissions": [1]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_role_create_returns_role_data(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.post(
            reverse("roles"),
            {"rolename": "DataReturn"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("role", response.data)

    def test_role_update_returns_role_data(self):
        admin = self._create_admin_user()
        self._auth(admin)
        role = Role.objects.create(rolename="UpdData")
        response = self.client.put(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {"description": "updated"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("role", response.data)

    def test_role_delete_returns_role_name(self):
        admin = self._create_admin_user()
        self._auth(admin)
        role = Role.objects.create(rolename="DelName")
        response = self.client.delete(
            reverse("role_detail", kwargs={"role_id": role.role_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "DelName")

    def test_role_update_not_found(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.put(
            reverse("role_detail", kwargs={"role_id": 99999}),
            {"description": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_role_update_manager_denied(self):
        mgr = self._create_manager_user()
        self._auth(mgr)
        role = Role.objects.create(rolename="MgrUpd")
        response = self.client.put(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {"description": "mgr"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_role_delete_manager_denied(self):
        mgr = self._create_manager_user()
        self._auth(mgr)
        role = Role.objects.create(rolename="MgrDel")
        response = self.client.delete(
            reverse("role_detail", kwargs={"role_id": role.role_id})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ==========================================================
# LOGIN VIEW EDGE CASES
# ==========================================================


class LoginViewEdgeCaseTests(AccountTestCase):
    def test_login_returns_tokens_on_success(self):
        self._create_user("tokchk", "tokchk@example.com", "9888888801", "TestPass@123")
        response = self.client.post(
            reverse("login"),
            {"email": "tokchk@example.com", "password": "TestPass@123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)

    def test_login_inactive_user_returns_401(self):
        user = self._create_user(
            "inactive", "inactive@example.com", "9888888802", "TestPass@123"
        )
        user.is_active = False
        user.save()
        response = self.client.post(
            reverse("login"),
            {"email": "inactive@example.com", "password": "TestPass@123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ==========================================================
# CHANGE PASSWORD VIEW EDGE CASES
# ==========================================================


class ChangePasswordViewEdgeCaseTests(AccountTestCase):
    def _change(self, user, payload):
        self._auth(user)
        return self.client.post(reverse("change_password"), payload, format="json")

    def test_change_password_same_password_accepted(self):
        user = self._create_user(
            "sameold2", "sameold2@example.com", "9999999901", "TestPass@123"
        )
        response = self._change(
            user, {"old_password": "TestPass@123", "new_password": "TestPass@123"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_change_password_success_message(self):
        user = self._create_user(
            "msgchk", "msgchk@example.com", "9999999902", "TestPass@123"
        )
        response = self._change(
            user, {"old_password": "TestPass@123", "new_password": "NewPass@456"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_change_password_empty_new_password(self):
        user = self._create_user(
            "emptynew2", "emptynew2@example.com", "9999999903", "TestPass@123"
        )
        response = self._change(
            user, {"old_password": "TestPass@123", "new_password": ""}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ==========================================================
# LOGOUT VIEW EDGE CASES
# ==========================================================


class LogoutViewEdgeCaseTests(AccountTestCase):
    def _token_pair(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token), str(refresh)

    def test_logout_with_already_blacklisted_token(self):
        user = self._create_user(
            "alreadybl", "alreadybl@example.com", "9999999910", "TestPass@123"
        )
        access, refresh = self._token_pair(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        self.client.post(reverse("logout"), {"refresh_token": refresh}, format="json")
        response = self.client.post(
            reverse("logout"), {"refresh_token": refresh}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("already logged out", response.data["message"])

    def test_logout_invalid_token_format(self):
        user = self._create_user(
            "invfmt", "invfmt@example.com", "9999999911", "TestPass@123"
        )
        access, _ = self._token_pair(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.post(
            reverse("logout"), {"refresh_token": "totally.bogus.token"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_unauthenticated(self):
        response = self.client.post(
            reverse("logout"), {"refresh_token": "x"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ==========================================================
# REFRESH TOKEN VIEW EDGE CASES
# ==========================================================


class RefreshTokenViewEdgeCaseTests(AccountTestCase):
    def test_refresh_invalid_token_returns_400(self):
        response = self.client.post(
            reverse("token_refresh"),
            {"refresh_token": "garbage.token.value"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_success_returns_access_token(self):
        user = self._create_user(
            "refchk", "refchk@example.com", "9999999920", "TestPass@123"
        )
        refresh = str(RefreshToken.for_user(user))
        response = self.client.post(
            reverse("token_refresh"),
            {"refresh_token": refresh},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)


# ==========================================================
# ROLE API MIXED METHOD TESTS
# ==========================================================


class RoleAPIMixedMethodTests(AccountTestCase):
    def test_role_put_manager_denied(self):
        mgr = self._create_manager_user()
        self._auth(mgr)
        role = Role.objects.create(rolename="MgrPut")
        response = self.client.put(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {"description": "mgr"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_role_delete_manager_denied(self):
        mgr = self._create_manager_user()
        self._auth(mgr)
        role = Role.objects.create(rolename="MgrDel2")
        response = self.client.delete(
            reverse("role_detail", kwargs={"role_id": role.role_id})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_role_patch_manager_denied(self):
        mgr = self._create_manager_user()
        self._auth(mgr)
        role = Role.objects.create(rolename="MgrPatch")
        perm = Permission.objects.create(
            name="View Task",
            codename="view_task",
            content_type=self.role_content_type,
        )
        response = self.client.patch(
            reverse("role_detail", kwargs={"role_id": role.role_id}),
            {"permissions": [perm.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_role_list_admin_sees_all_roles(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.get(reverse("roles"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["roles"]), 3)

    def test_role_list_manager_allowed(self):
        mgr = self._create_manager_user()
        self._auth(mgr)
        response = self.client.get(reverse("roles"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("roles", response.data)

    def test_role_list_unauthenticated(self):
        response = self.client.get(reverse("roles"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ==========================================================
# ASSIGN ROLE NOTIFICATION TESTS
# ==========================================================


class AssignRoleNotificationIntegrationTests(AccountTestCase):
    def _assign(self, user, target_id, payload):
        self._auth(user)
        return self.client.put(
            reverse("assign_role", kwargs={"user_id": target_id}),
            payload,
            format="json",
        )

    def test_assign_role_creates_notification(self):
        from Notification.models import Notification, NotificationEventType

        mgr = self._create_manager_user()
        target = self._create_employee_user()
        response = self._assign(
            mgr, target.user_id, {"role_id": self.manager_role.role_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notif = Notification.objects.filter(
            recipient=target,
            event_type=NotificationEventType.ROLE_CHANGED,
        ).first()
        self.assertIsNotNone(notif)

    def test_assign_role_notification_message_contains_rolename(self):
        from Notification.models import Notification, NotificationEventType

        mgr = self._create_manager_user()
        target = self._create_employee_user()
        self._assign(mgr, target.user_id, {"role_id": self.manager_role.role_id})
        notif = Notification.objects.filter(
            recipient=target,
            event_type=NotificationEventType.ROLE_CHANGED,
        ).first()
        self.assertIn("Manager", notif.message)

    def test_assign_role_response_contains_user_and_role(self):
        mgr = self._create_manager_user()
        target = self._create_employee_user()
        response = self._assign(
            mgr, target.user_id, {"role_id": self.manager_role.role_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], target.username)
        self.assertEqual(response.data["role"], self.manager_role.rolename)


# ==========================================================
# CUSTOM USER MODEL FIELD TESTS
# ==========================================================


class CustomUserFieldTests(AccountTestCase):
    def test_phone_number_max_length(self):
        user = CustomUser.objects.create_user(
            "phlen",
            "phlen@example.com",
            "1234567890",
            "TestPass@123",
        )
        self.assertEqual(len(user.phone_number), 10)

    def test_email_unique_constraint(self):
        self._create_user("u1", "same@example.com", "9111111141", "TestPass@123")
        with self.assertRaises(Exception):
            self._create_user("u2", "same@example.com", "9111111142", "TestPass@123")

    def test_phone_unique_constraint(self):
        self._create_user("u3", "u3@example.com", "9111111143", "TestPass@123")
        with self.assertRaises(Exception):
            self._create_user("u4", "u4@example.com", "9111111143", "TestPass@123")

    def test_user_role_nullable(self):
        user = self._create_user(
            "nullrole", "nullrole@example.com", "9111111144", "TestPass@123"
        )
        self.assertIsNone(user.role)

    def test_user_str_returns_email(self):
        user = self._create_user(
            "strchk", "strchk@example.com", "9111111145", "TestPass@123"
        )
        self.assertEqual(str(user), "strchk@example.com")


# ==========================================================
# ROLE MODEL CONSTRAINT TESTS
# ==========================================================


class RoleModelConstraintTests(AccountTestCase):
    def test_role_unique_rolename(self):
        Role.objects.create(rolename="UniqueRole")
        with self.assertRaises(Exception):
            Role.objects.create(rolename="UniqueRole")

    def test_role_rolename_max_length(self):
        role = Role.objects.create(rolename="A" * 13)
        self.assertEqual(len(role.rolename), 13)

    def test_role_rolename_too_long_fails(self):
        with self.assertRaises(Exception):
            Role.objects.create(rolename="A" * 14)

    def test_role_description_nullable(self):
        role = Role.objects.create(rolename="NoDesc")
        self.assertIsNone(role.description)

    def test_role_permissions_m2m(self):
        role = Role.objects.create(rolename="M2MRole")
        perm = Permission.objects.create(
            name="P1",
            codename="m2m_test_perm",
            content_type=self.role_content_type,
        )
        role.permissions.add(perm)
        self.assertEqual(role.permissions.count(), 1)
        self.assertIn(perm, role.permissions.all())

    def test_role_str_returns_rolename(self):
        role = Role.objects.create(rolename="StrRole")
        self.assertEqual(str(role), "StrRole")

    def test_role_created_at_auto_set(self):
        role = Role.objects.create(rolename="TimeRole")
        self.assertIsNotNone(role.created_at)

    def test_role_updated_at_auto_set(self):
        role = Role.objects.create(rolename="UpdTimeRole")
        role.description = "updated"
        role.save()
        self.assertIsNotNone(role.updated_at)


# ==========================================================
# HAS DYNAMIC PERMISSION COMPREHENSIVE TESTS
# ==========================================================


class HasDynamicPermissionComprehensiveTests(AccountTestCase):
    class FakeViewDict:
        permission_names = {"GET": "view_role", "POST": "add_role"}

    class FakeViewStr:
        permission_name = "view_role"

    class FakeViewNoPerm:
        pass

    class FakeViewEmptyDict:
        permission_names = {}

    def _call(self, user, view=None, method="GET"):
        if view is None:
            view = self.FakeViewDict()
        request = APIRequestFactory().request()
        request.method = method
        request.user = user
        return HasDynamicPermission().has_permission(request, view)

    def test_anonymous_user_denied(self):
        self.assertFalse(self._call(AnonymousUser()))

    def test_superuser_always_allowed(self):
        superuser = CustomUser.objects.create_superuser(
            "permroot", "permroot@example.com", "PermRoot@123"
        )
        self.assertTrue(self._call(superuser))

    def test_user_without_role_denied(self):
        user = self._create_plain_user(
            username="nopermrole",
            email="nopermrole@example.com",
            phone_number="9111111150",
            password="TestPass@123",
        )
        self.assertFalse(self._call(user))

    def test_user_with_matching_perm(self):
        admin = self._create_admin_user()
        self.assertTrue(self._call(admin))

    def test_user_without_matching_perm_denied(self):
        employee = self._create_employee_user()
        self.assertFalse(self._call(employee))

    def test_method_not_in_dict_denied(self):
        admin = self._create_admin_user()
        self.assertFalse(self._call(admin, method="DELETE"))

    def test_view_with_string_permission_name(self):
        admin = self._create_admin_user()
        self.assertTrue(self._call(admin, view=self.FakeViewStr()))

    def test_view_without_permission_config_denied(self):
        employee = self._create_employee_user()
        self.assertFalse(self._call(employee, view=self.FakeViewNoPerm()))

    def test_empty_permission_dict_denied(self):
        employee = self._create_employee_user()
        self.assertFalse(self._call(employee, view=self.FakeViewEmptyDict()))

    def test_manager_with_post_perm(self):
        mgr = self._create_manager_user()
        self.assertTrue(self._call(mgr, method="GET"))

    def test_employee_post_denied(self):
        employee = self._create_employee_user()
        self.assertFalse(self._call(employee, method="POST"))


# ==========================================================
# REGISTER VIEW EDGE CASE TESTS
# ==========================================================


class RegisterViewEdgeCaseTests(AccountTestCase):
    def test_register_returns_201_with_user_id(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "idchk",
                "email": "idchk@example.com",
                "phone_number": "9111111160",
                "password": "TestPass@123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user_id", response.data)

    def test_register_sets_employee_role(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "empchk2",
                "email": "empchk2@example.com",
                "phone_number": "9111111161",
                "password": "TestPass@123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = CustomUser.objects.get(email="empchk2@example.com")
        self.assertEqual(user.role.rolename, "Employee")

    def test_register_weak_password_accepted(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "weakchk",
                "email": "weakchk@example.com",
                "phone_number": "9111111162",
                "password": "123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_register_duplicate_email_returns_400(self):
        self._create_user("takenx", "takenx@example.com", "9111111163", "TestPass@123")
        response = self.client.post(
            reverse("register"),
            {
                "username": "takenx2",
                "email": "takenx@example.com",
                "phone_number": "9111111164",
                "password": "TestPass@123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_phone_returns_400(self):
        self._create_user("phchk", "phchk@example.com", "9111111165", "TestPass@123")
        response = self.client.post(
            reverse("register"),
            {
                "username": "phchk2",
                "email": "phchk2@example.com",
                "phone_number": "9111111165",
                "password": "TestPass@123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields_returns_400(self):
        response = self.client.post(reverse("register"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ==========================================================
# FORGOT / RESET PASSWORD TESTS (new - existing code untouched)
# ==========================================================
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ForgotPasswordTests(APITestCase):
    def setUp(self):
        self.forgot_url = reverse("forgot_password")
        self.reset_url = reverse("reset_password")
        self.user = CustomUser.objects.create_user(
            username="resetuser",
            email="resetuser@example.com",
            phone_number="9876543210",
            password="OldPass@123",
        )

    def _get_uid_and_token(self, user=None):
        user = user or self.user
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        return uid, token

    def test_forgot_password_sends_email_for_existing_user(self):
        response = self.client.post(
            self.forgot_url, {"email": "resetuser@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("resetuser@example.com", mail.outbox[0].to)

    def test_forgot_password_generic_response_for_unknown_email(self):
        response = self.client.post(
            self.forgot_url, {"email": "unknown@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)
        self.assertNotIn("error", response.data)

    def test_forgot_password_requires_email(self):
        response = self.client.post(self.forgot_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_success(self):
        uid, token = self._get_uid_and_token()
        response = self.client.post(
            self.reset_url,
            {"uid": uid, "token": token, "new_password": "NewPass@456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass@456"))

    def test_reset_password_token_invalid_after_use(self):
        uid, token = self._get_uid_and_token()
        first = self.client.post(
            self.reset_url,
            {"uid": uid, "token": token, "new_password": "NewPass@456"},
            format="json",
        )
        second = self.client.post(
            self.reset_url,
            {"uid": uid, "token": token, "new_password": "AnotherPass@789"},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass@456"))

    def test_reset_password_invalid_token(self):
        uid, _ = self._get_uid_and_token()
        response = self.client.post(
            self.reset_url,
            {"uid": uid, "token": "invalid-token", "new_password": "NewPass@456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPass@123"))

    def test_reset_password_invalid_uid(self):
        _, token = self._get_uid_and_token()
        response = self.client.post(
            self.reset_url,
            {"uid": "not-a-valid-uid", "token": token, "new_password": "NewPass@456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_weak_password_rejected(self):
        uid, token = self._get_uid_and_token()
        response = self.client.post(
            self.reset_url,
            {"uid": uid, "token": token, "new_password": "123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPass@123"))

    def test_reset_password_missing_fields(self):
        response = self.client.post(self.reset_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.views.send_mail", side_effect=Exception("SMTP down"))
    def test_forgot_password_returns_500_when_email_fails(self, mock_send_mail):
        response = self.client.post(
            self.forgot_url, {"email": "resetuser@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
