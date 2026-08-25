import unittest
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import CustomUser, Role

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

        # ==================================================
        # USER / ROLE
        # ==================================================

        self.role = Role.objects.create(
            rolename="FUEmployee",
            description="Employee role",
        )

        self.user = CustomUser.objects.create_user(
            email="followupuser@example.com",
            username="followupuser",
            password="Test@123",
            phone_number="9876543210",
            role=self.role,
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
                "followup_status": (self.followup_status.followup_status_id),
                "followup_type": (self.followup_type.followup_type_id),
                "followup_date": (timezone.now() + timedelta(days=2)).isoformat(),
                "decription": "Call customer again",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            Followup.objects.filter(decription="Call customer again").exists()
        )

    # ======================================================
    # CREATE FOLLOWUP - INVALID INPUT
    # ======================================================

    def test_create_followup_without_required_data(self):

        response = self.client.post(
            "/api/followups/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # ======================================================
    # LIST FOLLOWUPS
    # ======================================================

    def test_followup_list(self):

        response = self.client.get("/api/followups/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "results",
            response.data,
        )

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

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "count",
            response.data,
        )

        self.assertIn(
            "results",
            response.data,
        )

    # ======================================================
    # FILTER - STATUS
    # ======================================================

    def test_followup_filter_by_status(self):

        response = self.client.get(
            "/api/followups/"
            f"?followup_status="
            f"{self.followup_status.followup_status_id}"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "results",
            response.data,
        )

    # ======================================================
    # FILTER - TYPE
    # ======================================================

    def test_followup_filter_by_type(self):

        response = self.client.get(
            "/api/followups/"
            f"?followup_type="
            f"{self.followup_type.followup_type_id}"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "results",
            response.data,
        )

    # ======================================================
    # FILTER - TASK
    # ======================================================

    def test_followup_filter_by_task(self):

        response = self.client.get("/api/followups/" f"?task_id={self.task.task_id}")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "results",
            response.data,
        )

    # ======================================================
    # SEARCH
    # ======================================================

    def test_followup_search(self):

        response = self.client.get("/api/followups/?search=customer")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "results",
            response.data,
        )

    # ======================================================
    # ORDERING
    # ======================================================

    def test_followup_ordering(self):

        response = self.client.get("/api/followups/?ordering=-created_at")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "results",
            response.data,
        )

    # ======================================================
    # DETAIL
    # ======================================================

    def test_followup_detail(self):

        response = self.client.get(f"/api/followups/" f"{self.followup.followup_id}/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["followup_id"],
            self.followup.followup_id,
        )

    # ======================================================
    # UPDATE
    # ======================================================

    def test_update_followup(self):

        response = self.client.patch(
            f"/api/followups/" f"{self.followup.followup_id}/",
            {
                "decription": "Updated followup description",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.followup.refresh_from_db()

        self.assertEqual(
            self.followup.decription,
            "Updated followup description",
        )

    # ======================================================
    # DELETE
    # ======================================================

    def test_delete_followup(self):

        response = self.client.delete(
            f"/api/followups/" f"{self.followup.followup_id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        # DELETE is a soft delete (is_active=False), consistent with the
        # Task app's soft-delete behaviour.
        self.assertFalse(
            Followup.objects.filter(
                followup_id=self.followup.followup_id, is_active=True
            ).exists()
        )

    # ======================================================
    # CREATE FOLLOWUP NOTE
    # ======================================================

    @unittest.skip(
        "FollowUpNote model and the /notes/ endpoint were removed in the "
        "FollowUp refactor (merge 7a9fe08). Restore this test if notes return."
    )
    def test_create_followup_note(self):

        response = self.client.post(
            f"/api/followups/" f"{self.followup.followup_id}/notes/",
            {
                "note": "Customer requested callback.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        # NOTE: assertion intentionally omitted - the FollowUpNote model was
        # removed in merge 7a9fe08 (see @unittest.skip above).

    # ======================================================
    # OBJECT PERMISSION - OWNER
    # ======================================================

    def test_followup_owner_can_access(self):

        response = self.client.get(f"/api/followups/" f"{self.followup.followup_id}/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    # ======================================================
    # ERROR & NOTIFICATION TESTS
    # ======================================================

    def test_followup_not_found(self):
        response = self.client.get("/api/followups/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_followup_forbidden_for_other_user(self):
        other_user = CustomUser.objects.create_user(
            email="followupother@example.com",
            username="followupother",
            password="Test@123",
            phone_number="9999999991",
            role=self.role,
        )
        self.client.force_authenticate(user=other_user)
        response = self.client.get(f"/api/followups/{self.followup.followup_id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @unittest.skip(
        "Legacy FollowUp notification endpoints/models were moved to the "
        "dedicated Notification app (/api/notifications/). This test targets "
        "URLs that no longer exist in FollowUp."
    )
    def test_notification_list_and_patch(self):
        from FollowUp.models import Notification, NotificationType, NotificationTemplate

        ntype = NotificationType.objects.create(type_name="Alert")
        ntemplate = NotificationTemplate.objects.create(
            subject="Test Notification", body="Test message"
        )
        notification = Notification.objects.create(
            user_id=self.user,
            notification_type_id=ntype,
            template_id=ntemplate,
            title="Test Notification",
            message="Test message",
            is_read=False,
        )

        # List
        response = self.client.get("/api/followups/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

        # Detail
        response = self.client.get(
            f"/api/followups/notifications/{notification.notification_id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["notification_id"], notification.notification_id)

        # Patch - mark as read
        response = self.client.patch(
            f"/api/followups/notifications/{notification.notification_id}/",
            {"is_read": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
