from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import CustomUser, Role

from customer_management.models import (
    LeadSource,
    Pipeline,
    PipelineStage,
    Lead,
)

from Task.models import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskCategory,
)

from .models import (
    Followup,
    FollowUpStatus,
    FollowUpTypes,
)


class FollowUpAPITestCase(APITestCase):
    """
    Developer 3 - FollowUp API tests
    """

    def setUp(self):
        # --------------------------------------------------
        # MOCKS (audit_log UUID bug + notifications)
        # --------------------------------------------------
        self._patch_audit = patch("FollowUp.views.log_audit", return_value=None)
        self._patch_audit.start()
        self._patch_activity = patch("FollowUp.views.log_activity", return_value=None)
        self._patch_activity.start()
        self._patch_notify = patch("FollowUp.views.trigger_notification_event")
        self._patch_notify.start()
        self.addCleanup(self._patch_audit.stop)
        self.addCleanup(self._patch_activity.stop)
        self.addCleanup(self._patch_notify.stop)

        # ==================================================
        # USER / ROLE
        # ==================================================

        self.role, _ = Role.objects.get_or_create(
            rolename="FUEmployee",
            defaults={"description": "Employee role"},
        )

        ct = ContentType.objects.get_for_model(Followup)
        for codename in (
            "view_followup",
            "change_followup",
            "delete_followup",
            "change_followupstatus",
        ):
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                content_type=ct,
                defaults={"name": f"Can {codename}"},
            )
            self.role.permissions.add(perm)

        self.user = CustomUser.objects.create_user(
            email="followupuser@example.com",
            username="followupuser",
            password="Test@123",
            phone_number="9876543210",
            role=self.role,
        )

        # ==================================================
        # LEAD (required - Task.lead is NOT NULL)
        # ==================================================

        self.lead_source = LeadSource.objects.create(
            name="Website",
            description="Website source",
            created_by=self.user,
        )

        self.pipeline = Pipeline.objects.create(
            name="FollowUp Pipeline",
            description="FollowUp pipeline",
            created_by=self.user,
        )

        self.pipeline_stage = PipelineStage.objects.create(
            pipeline=self.pipeline,
            name="New",
            description="New lead",
            display_order=1,
        )

        self.lead = Lead.objects.create(
            name="Rahul",
            email="rahul@example.com",
            phone="9999999999",
            company_name="Rahul Company",
            source=self.lead_source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.pipeline_stage,
            status=Lead.Status.ACTIVE,
        )

        # ==================================================
        # TASK MASTER DATA
        # ==================================================

        self.task_status = TaskStatus.objects.create(
            status_name="Pending",
            is_active=True,
        )

        self.task_priority = TaskPriority.objects.create(
            priority_name="Medium",
            description="Medium priority",
            is_active=True,
        )

        self.task_category = TaskCategory.objects.create(
            category_name="General",
            is_active=True,
        )

        # ==================================================
        # TASK
        # ==================================================

        self.task = Task.objects.create(
            assigned_to=self.user,
            created_by=self.user,
            lead=self.lead,
            task_title="Customer FollowUp Task",
            description="Task for customer followup",
            due_date=(timezone.now() + timedelta(days=1)),
            status=self.task_status,
            priority=self.task_priority,
            category=self.task_category,
            is_active=True,
        )

        # ==================================================
        # FOLLOWUP MASTER DATA
        # ==================================================

        self.followup_status = FollowUpStatus.objects.create(
            status_name="Pending",
            is_active=True,
        )

        self.followup_type = FollowUpTypes.objects.create(
            type_name="Call",
            is_active=True,
        )

        # ==================================================
        # AUTHENTICATE
        # ==================================================

        self.client.force_authenticate(user=self.user)

        # ==================================================
        # FOLLOWUP
        # ==================================================

        self.followup = Followup.objects.create(
            task_id=self.task,
            followup_status=self.followup_status,
            followup_type=self.followup_type,
            followup_date=(timezone.now() + timedelta(days=1)),
            decription="Call customer tomorrow",
            created_by=self.user,
        )

    # ======================================================
    # AUTHENTICATION
    # ======================================================

    def test_followup_list_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/followups/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ======================================================
    # CREATE FOLLOWUP
    # ======================================================

    def test_create_followup(self):
        response = self.client.post(
            "/api/followups/",
            {
                "task_id": self.task.task_id,
                "followup_status": self.followup_status.followup_status_id,
                "followup_type": self.followup_type.followup_type_id,
                "followup_date": (timezone.now() + timedelta(days=2)).isoformat(),
                "decription": "Call customer again",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Followup.objects.filter(decription="Call customer again").exists()
        )

    # ======================================================
    # CREATE FOLLOWUP - VALIDATION
    # ======================================================

    def test_create_followup_without_required_data(self):
        response = self.client.post("/api/followups/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_followup_missing_task_id(self):
        response = self.client.post(
            "/api/followups/",
            {
                "followup_status": self.followup_status.followup_status_id,
                "followup_type": self.followup_type.followup_type_id,
                "followup_date": (timezone.now() + timedelta(days=2)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_followup_past_date_rejected(self):
        response = self.client.post(
            "/api/followups/",
            {
                "task_id": self.task.task_id,
                "followup_status": self.followup_status.followup_status_id,
                "followup_type": self.followup_type.followup_type_id,
                "followup_date": (timezone.now() - timedelta(days=1)).isoformat(),
                "decription": "Past date",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_followup_for_other_users_task_forbidden(self):
        other_user = CustomUser.objects.create_user(
            email="other@example.com",
            username="otheruser",
            password="Test@123",
            phone_number="9999999991",
            role=self.role,
        )
        other_task = Task.objects.create(
            assigned_to=other_user,
            created_by=other_user,
            lead=self.lead,
            task_title="Other Task",
            description="Other",
            due_date=timezone.now() + timedelta(days=1),
            status=self.task_status,
            priority=self.task_priority,
            category=self.task_category,
            is_active=True,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/followups/",
            {
                "task_id": other_task.task_id,
                "followup_status": self.followup_status.followup_status_id,
                "followup_type": self.followup_type.followup_type_id,
                "followup_date": (timezone.now() + timedelta(days=2)).isoformat(),
                "decription": "Unauthorized followup",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_followup_inactive_task_404(self):
        inactive_task = Task.objects.create(
            assigned_to=self.user,
            created_by=self.user,
            lead=self.lead,
            task_title="Inactive Task",
            description="Gone",
            due_date=timezone.now() + timedelta(days=1),
            status=self.task_status,
            priority=self.task_priority,
            category=self.task_category,
            is_active=False,
        )
        response = self.client.post(
            "/api/followups/",
            {
                "task_id": inactive_task.task_id,
                "followup_status": self.followup_status.followup_status_id,
                "followup_type": self.followup_type.followup_type_id,
                "followup_date": (timezone.now() + timedelta(days=2)).isoformat(),
                "decription": "Dead task",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ======================================================
    # LIST FOLLOWUPS
    # ======================================================

    def test_followup_list(self):
        response = self.client.get("/api/followups/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    # ======================================================
    # PAGINATION
    # ======================================================

    def test_followup_pagination(self):
        for number in range(15):
            Followup.objects.create(
                task_id=self.task,
                followup_status=self.followup_status,
                followup_type=self.followup_type,
                followup_date=(timezone.now() + timedelta(days=1)),
                decription=f"FollowUp {number}",
                created_by=self.user,
            )
        response = self.client.get("/api/followups/?page=1&page_size=10")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)

    # ======================================================
    # FILTER - STATUS
    # ======================================================

    def test_followup_filter_by_status(self):
        response = self.client.get(
            f"/api/followups/?followup_status={self.followup_status.followup_status_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    # ======================================================
    # FILTER - TYPE
    # ======================================================

    def test_followup_filter_by_type(self):
        response = self.client.get(
            f"/api/followups/?followup_type={self.followup_type.followup_type_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    # ======================================================
    # FILTER - TASK
    # ======================================================

    def test_followup_filter_by_task(self):
        response = self.client.get(f"/api/followups/?task_id={self.task.task_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    # ======================================================
    # SEARCH
    # ======================================================

    def test_followup_search(self):
        response = self.client.get("/api/followups/?search=FollowUp")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    # ======================================================
    # ORDERING
    # ======================================================

    def test_followup_ordering(self):
        response = self.client.get("/api/followups/?ordering=-created_at")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    # ======================================================
    # DETAIL
    # ======================================================

    def test_followup_detail(self):
        response = self.client.get(f"/api/followups/{self.followup.followup_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["followup_id"], self.followup.followup_id)

    # ======================================================
    # UPDATE
    # ======================================================

    def test_update_followup(self):
        response = self.client.patch(
            f"/api/followups/{self.followup.followup_id}/",
            {"decription": "Updated followup description"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.followup.refresh_from_db()
        self.assertEqual(self.followup.decription, "Updated followup description")

    # ======================================================
    # DELETE
    # ======================================================

    def test_delete_followup(self):
        response = self.client.delete(f"/api/followups/{self.followup.followup_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            Followup.objects.filter(
                followup_id=self.followup.followup_id
            ).exists()
        )

    # ======================================================
    # STATUS UPDATE
    # ======================================================

    def test_update_followup_status(self):
        new_status = FollowUpStatus.objects.create(
            status_name="Completed",
            is_active=True,
        )
        response = self.client.patch(
            f"/api/followups/{self.followup.followup_id}/status/",
            {"status_id": new_status.followup_status_id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.followup.refresh_from_db()
        self.assertEqual(self.followup.followup_status, new_status)

    def test_update_followup_status_invalid(self):
        response = self.client.patch(
            f"/api/followups/{self.followup.followup_id}/status/",
            {"status_id": 999999},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_followup_status_missing_field(self):
        response = self.client.patch(
            f"/api/followups/{self.followup.followup_id}/status/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ======================================================
    # OWNER ACCESS
    # ======================================================

    def test_followup_owner_can_access(self):
        response = self.client.get(f"/api/followups/{self.followup.followup_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ======================================================
    # ERROR CASES
    # ======================================================

    def test_followup_not_found(self):
        response = self.client.get("/api/followups/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_followup_forbidden_for_other_user(self):
        other_user = CustomUser.objects.create_user(
            email="followupother@example.com",
            username="followupother",
            password="Test@123",
            phone_number="9999999992",
            role=self.role,
        )
        self.client.force_authenticate(user=other_user)
        response = self.client.get(f"/api/followups/{self.followup.followup_id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_followup_forbidden_for_other_user(self):
        other_user = CustomUser.objects.create_user(
            email="followupupd@example.com",
            username="followupupd",
            password="Test@123",
            phone_number="9999999993",
            role=self.role,
        )
        self.client.force_authenticate(user=other_user)
        response = self.client.patch(
            f"/api/followups/{self.followup.followup_id}/",
            {"decription": "Hacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_followup_forbidden_for_other_user(self):
        other_user = CustomUser.objects.create_user(
            email="followupdel@example.com",
            username="followupdel",
            password="Test@123",
            phone_number="9999999994",
            role=self.role,
        )
        self.client.force_authenticate(user=other_user)
        response = self.client.delete(
            f"/api/followups/{self.followup.followup_id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_followup_status_forbidden_for_other_user(self):
        other_user = CustomUser.objects.create_user(
            email="followupst@example.com",
            username="followupst",
            password="Test@123",
            phone_number="9999999995",
            role=self.role,
        )
        new_status = FollowUpStatus.objects.create(
            status_name="Done",
            is_active=True,
        )
        self.client.force_authenticate(user=other_user)
        response = self.client.patch(
            f"/api/followups/{self.followup.followup_id}/status/",
            {"status_id": new_status.followup_status_id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class FollowUpManagerAccessTestCase(APITestCase):
    """
    Manager/Admin role access tests for FollowUp
    """

    def setUp(self):
        self._patch_audit = patch("FollowUp.views.log_audit", return_value=None)
        self._patch_audit.start()
        self._patch_activity = patch("FollowUp.views.log_activity", return_value=None)
        self._patch_activity.start()
        self._patch_notify = patch("FollowUp.views.trigger_notification_event")
        self._patch_notify.start()
        self.addCleanup(self._patch_audit.stop)
        self.addCleanup(self._patch_activity.stop)
        self.addCleanup(self._patch_notify.stop)

        # Manager role + permissions
        self.manager_role, _ = Role.objects.get_or_create(
            rolename="Manager",
            defaults={"description": "Manager role"},
        )

        ct = ContentType.objects.get_for_model(Followup)
        for codename in (
            "view_followup",
            "change_followup",
            "delete_followup",
            "change_followupstatus",
        ):
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                content_type=ct,
                defaults={"name": f"Can {codename}"},
            )
            self.manager_role.permissions.add(perm)

        self.manager = CustomUser.objects.create_user(
            email="fumanager@example.com",
            username="fumanager",
            password="Test@123",
            phone_number="9876543220",
            role=self.manager_role,
        )

        # Employee (task assignee)
        self.emp_role, _ = Role.objects.get_or_create(
            rolename="FUEmployee",
            defaults={"description": "Employee"},
        )
        ct_task = ContentType.objects.get_for_model(Task)
        for codename in ("add_task", "view_task", "change_task"):
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                content_type=ct_task,
                defaults={"name": f"Can {codename}"},
            )
            self.emp_role.permissions.add(perm)

        self.employee = CustomUser.objects.create_user(
            email="fuemployee@example.com",
            username="fuemployee",
            password="Test@123",
            phone_number="9876543221",
            role=self.emp_role,
        )

        # Lead + Task
        self.lead_source = LeadSource.objects.create(
            name="Referral", description="Ref", created_by=self.employee,
        )
        self.pipeline = Pipeline.objects.create(
            name="Mgr Pipeline", description="p", created_by=self.employee,
        )
        self.pipeline_stage = PipelineStage.objects.create(
            pipeline=self.pipeline, name="New", description="n", display_order=1,
        )
        self.lead = Lead.objects.create(
            name="Amit", email="amit@example.com", phone="8888888888",
            company_name="Amit Corp", source=self.lead_source,
            assigned_to=self.employee, pipeline=self.pipeline,
            current_stage=self.pipeline_stage, status=Lead.Status.ACTIVE,
        )

        self.task_status = TaskStatus.objects.create(status_name="Pending", is_active=True)
        self.task_priority = TaskPriority.objects.create(
            priority_name="High", description="High", is_active=True,
        )
        self.task_category = TaskCategory.objects.create(
            category_name="General", is_active=True,
        )

        self.task = Task.objects.create(
            assigned_to=self.employee,
            created_by=self.employee,
            lead=self.lead,
            task_title="Manager FollowUp Task",
            description="Mgr test",
            due_date=timezone.now() + timedelta(days=1),
            status=self.task_status,
            priority=self.task_priority,
            category=self.task_category,
            is_active=True,
        )

        self.followup_status = FollowUpStatus.objects.create(
            status_name="Pending", is_active=True,
        )
        self.followup_type = FollowUpTypes.objects.create(
            type_name="Email", is_active=True,
        )

        self.followup = Followup.objects.create(
            task_id=self.task,
            followup_status=self.followup_status,
            followup_type=self.followup_type,
            followup_date=timezone.now() + timedelta(days=1),
            decription="Manager can see this",
            created_by=self.employee,
        )

        self.client.force_authenticate(user=self.manager)

    def test_manager_can_list_all_followups(self):
        response = self.client.get("/api/followups/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manager_can_view_any_followup(self):
        response = self.client.get(f"/api/followups/{self.followup.followup_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manager_can_update_any_followup(self):
        response = self.client.patch(
            f"/api/followups/{self.followup.followup_id}/",
            {"decription": "Manager updated"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.followup.refresh_from_db()
        self.assertEqual(self.followup.decription, "Manager updated")

    def test_manager_can_delete_any_followup(self):
        response = self.client.delete(
            f"/api/followups/{self.followup.followup_id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manager_can_update_status(self):
        new_status = FollowUpStatus.objects.create(
            status_name="Resolved", is_active=True,
        )
        response = self.client.patch(
            f"/api/followups/{self.followup.followup_id}/status/",
            {"status_id": new_status.followup_status_id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.followup.refresh_from_db()
        self.assertEqual(self.followup.followup_status, new_status)

    def test_manager_can_filter_by_created_by(self):
        response = self.client.get(
            f"/api/followups/?created_by={self.employee.user_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
