import uuid

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
        role = Role.objects.create(rolename=rolename)
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
            "admin", "admin@example.com", "9000000001", "AdminPass@123", role=self.admin_role
        )

    def _create_manager_user(self):
        return self._create_user(
            "manager", "manager@example.com", "9000000002", "ManagerPass@123", role=self.manager_role
        )

    def _create_employee_user(self):
        return self._create_user(
            "employee", "employee@example.com", "9000000003", "EmployeePass@123", role=self.employee_role
        )

    def _create_plain_user(self, **kwargs):
        return self._create_user(**kwargs)

    def _auth(self, user):
        self.client.force_authenticate(user=user)


class CustomUserManagerTests(AccountTestCase):
    def test_create_user_success(self):
        user = self._create_user(
            "alice", "alice@example.com", "9111111111", "TestPass@123", role=self.employee_role
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
        user = self._create_user("carol", "carol@example.com", "9111111113", "TestPass@123")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIsNone(user.role)

    def test_create_superuser_flags_and_admin_role(self):
        user = CustomUser.objects.create_superuser("root", "root@example.com", "RootPass@123")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertEqual(user.role.rolename, "Admin")

    def test_create_superuser_gets_all_permissions(self):
        user = CustomUser.objects.create_superuser("root2", "root2@example.com", "RootPass@123")
        self.assertEqual(user.role.permissions.count(), Permission.objects.count())


class RoleModelTests(AccountTestCase):
    def test_role_str_returns_rolename(self):
        role = Role.objects.create(rolename="Support")
        self.assertEqual(str(role), "Support")


class CustomUserModelTests(AccountTestCase):
    def test_user_str_returns_email(self):
        user = self._create_user("dave", "dave@example.com", "9111111114", "TestPass@123")
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
        user = self._create_user("sleepy", "sleepy@example.com", "9111111121", "TestPass@123")
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

    def test_logout_twice_rejects_blacklisted_token(self):
        user = self._create_user("joe", "joe@example.com", "9111111120", "TestPass@123")
        access, refresh = self._token_pair(user)
        self.assertEqual(self._logout(access, refresh).status_code, status.HTTP_200_OK)
        self.assertEqual(self._logout(access, refresh).status_code, status.HTTP_400_BAD_REQUEST)

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
        self.assertEqual(response.data["message"], "Access token refreshed successfully")
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
        self.assertEqual(
            Role.objects.get(rolename="Support").permissions.count(), 1
        )

    def test_role_create_duplicate_name(self):
        admin = self._create_admin_user()
        self._auth(admin)
        response = self.client.post(reverse("roles"), {"rolename": "Admin"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_role_create_denied_without_permission(self):
        manager = self._create_manager_user()
        self._auth(manager)
        response = self.client.post(reverse("roles"), {"rolename": "Support"}, format="json")
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
        response = self.client.delete(
            reverse("role_detail", kwargs={"role_id": 99999})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


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
        self.assertEqual(response.data["message"], "Permissions retrieved successfully.")

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
        response = self.client.post(reverse("permissions"), self._payload(1), format="json")
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
            {"user_id", "username", "email", "phone_number", "role", "created_at", "updated_at"},
        )
