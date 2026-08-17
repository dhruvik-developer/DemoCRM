import uuid
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from Task.models import Task, TaskCategory, TaskPriority, TaskStatus
from FollowUp.models import Followup, FollowUpStatus, FollowUpTypes
from customer_management.models import Lead, LeadSource, Pipeline, PipelineStage, Quotation
from customer_management.services import CRMService, QuotationService

from .models import (
    Notification,
    NotificationChannel,
    NotificationEventType,
    NotificationTemplate,
)
from .notification_utils import render_template, trigger_notification_event

User = get_user_model()


class NotificationTemplateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_role, _ = Role.objects.get_or_create(
            rolename="Admin", defaults={"description": "Administrator"}
        )
        self.admin_user = User.objects.create_superuser(
            username="adminuser",
            email="admin@example.com",
            phone_number="9998887770",
            password="Password@123",
            role=self.admin_role,
        )
        self.employee_role, _ = Role.objects.get_or_create(
            rolename="Employee", defaults={"description": "Employee"}
        )
        self.employee_user = User.objects.create_user(
            username="empuser",
            email="emp@example.com",
            phone_number="9998887771",
            password="Password@123",
            role=self.employee_role,
        )

    def test_create_notification_template(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("Notification:template-list-create")
        data = {
            "name": "Task Assigned Template",
            "event_type": NotificationEventType.TASK_ASSIGNED,
            "message": "Hello {{user_name}}, you are assigned {{task_title}}.",
            "channel": NotificationChannel.IN_APP,
            "is_default": True,
            "is_active": True,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Task Assigned Template")
        self.assertTrue(response.data["is_default"])

    def test_update_and_deactivate_template(self):
        self.client.force_authenticate(user=self.admin_user)
        template = NotificationTemplate.objects.create(
            name="Test Template",
            event_type=NotificationEventType.TASK_UPDATED,
            message="Old message {{task_title}}",
            channel=NotificationChannel.IN_APP,
        )
        url = reverse("Notification:template-detail", kwargs={"pk": template.pk})
        
        # Update template
        update_data = {"message": "New message {{task_title}}"}
        patch_res = self.client.patch(url, update_data, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["message"], "New message {{task_title}}")

        # Soft delete / deactivate template
        del_res = self.client.delete(url)
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)
        template.refresh_from_db()
        self.assertFalse(template.is_active)

    def test_multiple_templates_default_selection(self):
        t1 = NotificationTemplate.objects.create(
            name="Template 1",
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Template 1: {{task_title}}",
            is_default=True,
            is_active=True,
        )
        t2 = NotificationTemplate.objects.create(
            name="Template 2",
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Template 2: {{task_title}}",
            is_default=False,
            is_active=True,
        )
        # Creating a new default template should unset previous default
        t3 = NotificationTemplate.objects.create(
            name="Template 3",
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Template 3: {{task_title}}",
            is_default=True,
            is_active=True,
        )
        t1.refresh_from_db()
        self.assertFalse(t1.is_default)
        self.assertTrue(t3.is_default)

        # Trigger event should pick default template t3
        notifications = trigger_notification_event(
            event_type=NotificationEventType.TASK_ASSIGNED,
            recipient=self.employee_user,
            context={"task_title": "Fix Bug #101"},
        )
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].message, "Template 3: Fix Bug #101")


class RenderTemplateTests(TestCase):
    def test_template_rendering_variables(self):
        template_str = "Hi {{user_name}}, Manager {{manager_name}} assigned task {{task_title}}."
        context = {
            "user_name": "John Doe",
            "manager_name": "Jane Smith",
            "task_title": "Prepare Financial Report",
        }
        rendered = render_template(template_str, context)
        self.assertEqual(
            rendered,
            "Hi John Doe, Manager Jane Smith assigned task Prepare Financial Report.",
        )


class NotificationUserAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(
            username="usera",
            email="usera@example.com",
            phone_number="9990001111",
            password="Password@123",
        )
        self.user_b = User.objects.create_user(
            username="userb",
            email="userb@example.com",
            phone_number="9990002222",
            password="Password@123",
        )
        self.notif_a = Notification.objects.create(
            recipient=self.user_a,
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Notification for User A",
            channel=NotificationChannel.IN_APP,
        )
        self.notif_b = Notification.objects.create(
            recipient=self.user_b,
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Notification for User B",
            channel=NotificationChannel.IN_APP,
        )

    def test_user_can_only_view_own_notifications(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse("Notification:user-notification-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.notif_a.id)

        # Accessing detail of User B's notification should be forbidden/404
        detail_url = reverse("Notification:user-notification-detail", kwargs={"pk": self.notif_b.id})
        detail_res = self.client.get(detail_url)
        self.assertEqual(detail_res.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_notification_as_read(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse("Notification:user-notification-mark-read", kwargs={"pk": self.notif_a.id})
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_read"])
        self.notif_a.refresh_from_db()
        self.assertTrue(self.notif_a.is_read)
        self.assertIsNotNone(self.notif_a.read_at)


class NotificationChannelAndPersistentStorageTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testchanuser",
            email="chan@example.com",
            phone_number="9876543210",
            password="Password@123",
        )

    def test_in_app_channel_sends_no_email(self):
        mail.outbox = []
        trigger_notification_event(
            event_type=NotificationEventType.TASK_ASSIGNED,
            recipient=self.user,
            custom_message="In-app only message",
            channel=NotificationChannel.IN_APP,
        )
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(Notification.objects.filter(recipient=self.user).count(), 1)

    def test_email_channel_sends_email(self):
        mail.outbox = []
        trigger_notification_event(
            event_type=NotificationEventType.TASK_ASSIGNED,
            recipient=self.user,
            custom_message="Email notification message",
            channel=NotificationChannel.EMAIL,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Email notification message", mail.outbox[0].body)

    def test_both_channel_creates_notification_and_sends_email(self):
        mail.outbox = []
        trigger_notification_event(
            event_type=NotificationEventType.TASK_ASSIGNED,
            recipient=self.user,
            custom_message="Both channel message",
            channel=NotificationChannel.BOTH,
        )
        self.assertEqual(Notification.objects.filter(recipient=self.user).count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_persistent_message_storage(self):
        template = NotificationTemplate.objects.create(
            name="Static Template",
            event_type=NotificationEventType.QUOTATION_APPROVED,
            message="Original quotation {{quotation_number}} approved.",
            is_default=True,
        )
        notifs = trigger_notification_event(
            event_type=NotificationEventType.QUOTATION_APPROVED,
            recipient=self.user,
            context={"quotation_number": "Q-1001"},
        )
        saved_msg = notifs[0].message
        self.assertEqual(saved_msg, "Original quotation Q-1001 approved.")

        # Admin changes template
        template.message = "Updated quotation {{quotation_number}} text!"
        template.save()

        # Existing notification row message must remain unchanged
        notifs[0].refresh_from_db()
        self.assertEqual(notifs[0].message, "Original quotation Q-1001 approved.")


class ManualNotificationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_role, _ = Role.objects.get_or_create(
            rolename="Admin", defaults={"description": "Administrator"}
        )
        self.admin_user = User.objects.create_superuser(
            username="manualadmin",
            email="madmin@example.com",
            phone_number="9112223334",
            password="Password@123",
            role=self.admin_role,
        )
        self.target_user = User.objects.create_user(
            username="targetuser",
            email="target@example.com",
            phone_number="9112223335",
            password="Password@123",
        )

    def test_manual_notification_send(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("Notification:notification-send")
        data = {
            "recipient_id": str(self.target_user.user_id),
            "custom_message": "Please call client before 5 PM.",
            "channel": NotificationChannel.IN_APP,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["message"], "Please call client before 5 PM.")


class BusinessOperationIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_role, _ = Role.objects.get_or_create(
            rolename="Admin", defaults={"description": "Administrator"}
        )
        self.admin_user = User.objects.create_superuser(
            username="crmadmin",
            email="crmadmin@example.com",
            phone_number="9776665551",
            password="Password@123",
            role=self.admin_role,
        )
        self.employee_user = User.objects.create_user(
            username="crmemp",
            email="crmemp@example.com",
            phone_number="9776665552",
            password="Password@123",
        )
        self.task_status = TaskStatus.objects.create(status_name="Open")
        self.task_completed_status = TaskStatus.objects.create(status_name="Completed")
        self.task_priority = TaskPriority.objects.create(priority_name="High")
        self.task_category = TaskCategory.objects.create(category_name="General")

    def test_task_creation_triggers_notification(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("task-list-create")
        data = {
            "task_title": "New Sales Task",
            "status": self.task_status.pk,
            "priority": self.task_priority.pk,
            "category": self.task_category.pk,
            "assigned_to": str(self.employee_user.pk),
        }
        res = self.client.post(url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        # Verify notification created for assignee
        notifs = Notification.objects.filter(
            recipient=self.employee_user,
            event_type=NotificationEventType.TASK_ASSIGNED,
        )
        self.assertEqual(notifs.count(), 1)
        self.assertIn("New Sales Task", notifs.first().message)

    def test_failed_operation_creates_no_notification(self):
        self.client.force_authenticate(user=self.admin_user)
        initial_notif_count = Notification.objects.count()

        # Submit invalid task post request (missing required status field)
        url = reverse("task-list-create")
        data = {
            "task_title": "Invalid Task",
            "assigned_to": str(self.employee_user.pk),
        }
        res = self.client.post(url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Must NOT create any notification
        self.assertEqual(Notification.objects.count(), initial_notif_count)

    def test_quotation_approval_triggers_notification(self):
        source = LeadSource.objects.create(name="Web", created_by=self.admin_user)
        pipeline = Pipeline.objects.create(name="Sales", created_by=self.admin_user)
        stage = PipelineStage.objects.create(
            pipeline=pipeline,
            name="Quote",
            display_order=1,
            quotation_approval_required=True,
        )
        lead = Lead.objects.create(
            name="Acme Corp",
            source=source,
            assigned_to=self.employee_user,
            pipeline=pipeline,
            current_stage=stage,
        )
        quotation = QuotationService.create_quotation(
            user=self.employee_user,
            lead=lead,
            line_items=[{"description": "Item 1", "quantity": 1, "unit_price": "100.00"}],
        )
        # Submit for approval
        QuotationService.submit_quotation_for_approval(user=self.employee_user, quotation=quotation)

        # Approve quotation as manager
        QuotationService.approve_quotation(reviewer_user=self.admin_user, quotation=quotation)

        notif = Notification.objects.filter(
            recipient=self.employee_user,
            event_type=NotificationEventType.QUOTATION_APPROVED,
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn(quotation.quotation_number, notif.message)


# ==========================================================
# NOTIFICATION TEMPLATE API TESTS
# ==========================================================

class NotificationTemplateAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_role, _ = Role.objects.get_or_create(
            rolename="Admin", defaults={"description": "Administrator"}
        )
        self.admin_user = User.objects.create_superuser(
            username="tpladmin",
            email="tpladmin@example.com",
            phone_number="9113330001",
            password="Password@123",
            role=self.admin_role,
        )
        self.employee_role, _ = Role.objects.get_or_create(
            rolename="Employee", defaults={"description": "Employee"}
        )
        self.employee_user = User.objects.create_user(
            username="tplemp",
            email="tplemp@example.com",
            phone_number="9113330002",
            password="Password@123",
            role=self.employee_role,
        )
        self.user_no_role = User.objects.create_user(
            username="tplnorole",
            email="tplnorole@example.com",
            phone_number="9113330003",
            password="Password@123",
        )
        self.template = NotificationTemplate.objects.create(
            name="Existing Template",
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Hello {{user_name}}, task {{task_title}} assigned.",
            channel=NotificationChannel.IN_APP,
            is_default=True,
            is_active=True,
        )

    def test_list_templates_returns_all(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(reverse("Notification:template-list-create"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_list_templates_filter_by_event_type(self):
        NotificationTemplate.objects.create(
            name="Another",
            event_type=NotificationEventType.ROLE_CHANGED,
            message="Role changed.",
            channel=NotificationChannel.IN_APP,
        )
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(
            reverse("Notification:template-list-create"),
            {"event_type": NotificationEventType.TASK_ASSIGNED},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for tpl in response.data:
            self.assertEqual(tpl["event_type"], NotificationEventType.TASK_ASSIGNED)

    def test_list_templates_filter_by_is_active(self):
        NotificationTemplate.objects.create(
            name="Inactive",
            event_type=NotificationEventType.TASK_COMPLETED,
            message="Done.",
            channel=NotificationChannel.IN_APP,
            is_active=False,
        )
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(
            reverse("Notification:template-list-create"),
            {"is_active": "false"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for tpl in response.data:
            self.assertFalse(tpl["is_active"])

    def test_create_template_missing_required_fields(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse("Notification:template-list-create"),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_template_invalid_channel(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse("Notification:template-list-create"),
            {
                "name": "Bad Channel",
                "event_type": "TASK_ASSIGNED",
                "message": "Test",
                "channel": "INVALID_CHANNEL",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_template_default_becomes_true(self):
        self.client.force_authenticate(user=self.admin_user)
        old_default = NotificationTemplate.objects.filter(
            event_type=NotificationEventType.TASK_ASSIGNED, is_default=True
        ).first()
        response = self.client.post(
            reverse("Notification:template-list-create"),
            {
                "name": "New Default",
                "event_type": NotificationEventType.TASK_ASSIGNED,
                "message": "New default msg {{task_title}}",
                "channel": "IN_APP",
                "is_default": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        if old_default:
            old_default.refresh_from_db()
            self.assertFalse(old_default.is_default)

    def test_get_template_detail(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("Notification:template-detail", kwargs={"pk": self.template.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Existing Template")

    def test_get_template_not_found(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("Notification:template-detail", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_template_full_update(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("Notification:template-detail", kwargs={"pk": self.template.pk})
        response = self.client.put(
            url,
            {
                "name": "Fully Updated",
                "event_type": NotificationEventType.TASK_ASSIGNED,
                "message": "Fully updated message",
                "channel": "BOTH",
                "is_default": True,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, "Fully Updated")
        self.assertEqual(self.template.channel, NotificationChannel.BOTH)

    def test_patch_template_partial_update(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("Notification:template-detail", kwargs={"pk": self.template.pk})
        response = self.client.patch(
            url,
            {"channel": "EMAIL"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.template.refresh_from_db()
        self.assertEqual(self.template.channel, NotificationChannel.EMAIL)

    def test_delete_template_soft_deletes(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("Notification:template-detail", kwargs={"pk": self.template.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.template.refresh_from_db()
        self.assertFalse(self.template.is_active)

    def test_delete_template_not_found(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("Notification:template-detail", kwargs={"pk": 99999})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_employee_denied_template_create(self):
        self.client.force_authenticate(user=self.employee_user)
        response = self.client.post(
            reverse("Notification:template-list-create"),
            {
                "name": "Emp Template",
                "event_type": "TASK_ASSIGNED",
                "message": "Test",
                "channel": "IN_APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_denied_template_list(self):
        response = self.client.get(reverse("Notification:template-list-create"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_denied_template_detail(self):
        url = reverse("Notification:template-detail", kwargs={"pk": self.template.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ==========================================================
# MANUAL NOTIFICATION API TESTS
# ==========================================================

class ManualNotificationSendAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_role, _ = Role.objects.get_or_create(
            rolename="Admin", defaults={"description": "Administrator"}
        )
        self.admin_user = User.objects.create_superuser(
            username="manadmin",
            email="manadmin@example.com",
            phone_number="9113330010",
            password="Password@123",
            role=self.admin_role,
        )
        self.target = User.objects.create_user(
            username="mantarget",
            email="mantarget@example.com",
            phone_number="9113330011",
            password="Password@123",
        )
        self.target2 = User.objects.create_user(
            username="mantarget2",
            email="mantarget2@example.com",
            phone_number="9113330012",
            password="Password@123",
        )
        self.template = NotificationTemplate.objects.create(
            name="Manual Template",
            event_type=NotificationEventType.MANUAL,
            message="Manual msg: {{user_name}}",
            channel=NotificationChannel.IN_APP,
            is_default=True,
        )

    def test_manual_send_multiple_recipients(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse("Notification:notification-send"),
            {
                "recipient_ids": [str(self.target.user_id), str(self.target2.user_id)],
                "custom_message": "Broadcast message",
                "channel": "IN_APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 2)

    def test_manual_send_with_template_id(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse("Notification:notification-send"),
            {
                "recipient_id": str(self.target.user_id),
                "template_id": self.template.pk,
                "channel": "IN_APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notif = Notification.objects.filter(
            recipient=self.target,
            event_type=NotificationEventType.MANUAL,
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn(self.target.get_full_name() or self.target.username, notif.message)

    def test_manual_send_no_recipient(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse("Notification:notification-send"),
            {
                "custom_message": "No one gets this",
                "channel": "IN_APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manual_send_nonexistent_recipient(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse("Notification:notification-send"),
            {
                "recipient_id": str(uuid.uuid4()),
                "custom_message": "Ghost message",
                "channel": "IN_APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manual_send_nonexistent_template(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse("Notification:notification-send"),
            {
                "recipient_id": str(self.target.user_id),
                "template_id": 99999,
                "channel": "IN_APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manual_send_invalid_channel(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse("Notification:notification-send"),
            {
                "recipient_id": str(self.target.user_id),
                "custom_message": "Test",
                "channel": "Pigeon",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manual_send_unauthenticated(self):
        response = self.client.post(
            reverse("Notification:notification-send"),
            {
                "recipient_id": str(self.target.user_id),
                "custom_message": "Test",
                "channel": "IN_APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_manual_send_email_channel(self):
        mail.outbox = []
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse("Notification:notification-send"),
            {
                "recipient_id": str(self.target.user_id),
                "custom_message": "Email via manual",
                "channel": "EMAIL",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 1)


# ==========================================================
# USER NOTIFICATION API TESTS
# ==========================================================

class UserNotificationListAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="listuser",
            email="listuser@example.com",
            phone_number="9113330020",
            password="Password@123",
        )
        self.other_user = User.objects.create_user(
            username="listother",
            email="listother@example.com",
            phone_number="9113330021",
            password="Password@123",
        )
        self.notif1 = Notification.objects.create(
            recipient=self.user,
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Notif 1",
            channel=NotificationChannel.IN_APP,
            is_read=False,
        )
        self.notif2 = Notification.objects.create(
            recipient=self.user,
            event_type=NotificationEventType.TASK_COMPLETED,
            message="Notif 2",
            channel=NotificationChannel.IN_APP,
            is_read=True,
        )
        self.notif_other = Notification.objects.create(
            recipient=self.other_user,
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Other user notif",
            channel=NotificationChannel.IN_APP,
        )

    def test_list_returns_only_own_notifications(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("Notification:user-notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        for n in response.data:
            self.assertIn(n["id"], [self.notif1.id, self.notif2.id])

    def test_list_filter_is_read_true(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("Notification:user-notification-list"),
            {"is_read": "true"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.notif2.id)

    def test_list_filter_is_read_false(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("Notification:user-notification-list"),
            {"is_read": "false"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.notif1.id)

    def test_list_empty_for_user_with_no_notifications(self):
        self.client.force_authenticate(user=self.other_user)
        Notification.objects.filter(recipient=self.other_user).delete()
        response = self.client.get(reverse("Notification:user-notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_list_unauthenticated(self):
        response = self.client.get(reverse("Notification:user-notification-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_does_not_leak_other_users(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(reverse("Notification:user-notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notif_ids = [n["id"] for n in response.data]
        self.assertNotIn(self.notif1.id, notif_ids)


# ==========================================================
# USER NOTIFICATION DETAIL API TESTS
# ==========================================================

class UserNotificationDetailAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="detuser",
            email="detuser@example.com",
            phone_number="9113330030",
            password="Password@123",
        )
        self.other_user = User.objects.create_user(
            username="detother",
            email="detother@example.com",
            phone_number="9113330031",
            password="Password@123",
        )
        self.notif = Notification.objects.create(
            recipient=self.user,
            event_type=NotificationEventType.ROLE_CHANGED,
            message="Your role changed",
            channel=NotificationChannel.IN_APP,
        )
        self.notif_other = Notification.objects.create(
            recipient=self.other_user,
            event_type=NotificationEventType.ROLE_CHANGED,
            message="Other role changed",
            channel=NotificationChannel.IN_APP,
        )

    def test_get_own_notification_detail(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("Notification:user-notification-detail", kwargs={"pk": self.notif.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Your role changed")

    def test_cannot_get_other_users_notification(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("Notification:user-notification-detail", kwargs={"pk": self.notif_other.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_notification_not_found(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("Notification:user-notification-detail", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_denied(self):
        url = reverse("Notification:user-notification-detail", kwargs={"pk": self.notif.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ==========================================================
# NOTIFICATION MARK READ API TESTS
# ==========================================================

class NotificationMarkReadAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="readuser",
            email="readuser@example.com",
            phone_number="9113330040",
            password="Password@123",
        )
        self.other_user = User.objects.create_user(
            username="readother",
            email="readother@example.com",
            phone_number="9113330041",
            password="Password@123",
        )
        self.unread_notif = Notification.objects.create(
            recipient=self.user,
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Unread notif",
            channel=NotificationChannel.IN_APP,
            is_read=False,
        )
        self.already_read = Notification.objects.create(
            recipient=self.user,
            event_type=NotificationEventType.TASK_COMPLETED,
            message="Already read",
            channel=NotificationChannel.IN_APP,
            is_read=True,
        )
        self.other_notif = Notification.objects.create(
            recipient=self.other_user,
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Other user notif",
            channel=NotificationChannel.IN_APP,
        )

    def test_mark_unread_as_read_via_put(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("Notification:user-notification-mark-read", kwargs={"pk": self.unread_notif.id})
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_read"])
        self.unread_notif.refresh_from_db()
        self.assertIsNotNone(self.unread_notif.read_at)

    def test_mark_read_as_read_via_patch(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("Notification:user-notification-mark-read", kwargs={"pk": self.already_read.id})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_read"])

    def test_mark_read_idempotent(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("Notification:user-notification-mark-read", kwargs={"pk": self.already_read.id})
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_read"])

    def test_mark_read_not_found(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("Notification:user-notification-mark-read", kwargs={"pk": 99999})
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_read_other_users_notif_denied(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("Notification:user-notification-mark-read", kwargs={"pk": self.other_notif.id})
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_read_unauthenticated(self):
        url = reverse("Notification:user-notification-mark-read", kwargs={"pk": self.unread_notif.id})
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ==========================================================
# RENDER TEMPLATE UTILITY TESTS
# ==========================================================

class RenderTemplateEdgeCaseTests(TestCase):
    def test_empty_string_returns_empty(self):
        result = render_template("", {})
        self.assertEqual(result, "")

    def test_none_returns_empty(self):
        result = render_template(None, {})
        self.assertEqual(result, "")

    def test_empty_context_leaves_placeholders(self):
        result = render_template("Hello {{user_name}}", {})
        self.assertEqual(result, "Hello {{user_name}}")

    def test_missing_variable_leaves_placeholder(self):
        result = render_template("Hi {{user_name}}, task {{task_title}}", {"user_name": "Alice"})
        self.assertEqual(result, "Hi Alice, task {{task_title}}")

    def test_no_placeholders_returns_original(self):
        result = render_template("Plain text message", {"user_name": "X"})
        self.assertEqual(result, "Plain text message")

    def test_multiple_same_variable(self):
        result = render_template("{{x}} and {{x}}", {"x": "hello"})
        self.assertEqual(result, "hello and hello")

    def test_whitespace_in_placeholders(self):
        result = render_template("Hello {{ user_name }}", {"user_name": "Bob"})
        self.assertEqual(result, "Hello Bob")

    def test_numeric_variable_rendered_as_string(self):
        result = render_template("ID: {{task_id}}", {"task_id": 42})
        self.assertEqual(result, "ID: 42")

    def test_boolean_variable_rendered_as_string(self):
        result = render_template("Active: {{is_active}}", {"is_active": True})
        self.assertEqual(result, "Active: True")


# ==========================================================
# TRIGGER NOTIFICATION EVENT UTILITY TESTS
# ==========================================================

class TriggerNotificationEventTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="triguser",
            email="triguser@example.com",
            phone_number="9113330050",
            password="Password@123",
        )
        self.user2 = User.objects.create_user(
            username="triguser2",
            email="triguser2@example.com",
            phone_number="9113330051",
            password="Password@123",
        )

    def test_none_recipient_returns_empty(self):
        result = trigger_notification_event(
            event_type=NotificationEventType.TASK_ASSIGNED,
            recipient=None,
        )
        self.assertEqual(result, [])

    def test_no_recipients_returns_empty(self):
        result = trigger_notification_event(
            event_type=NotificationEventType.TASK_ASSIGNED,
            recipient=[],
        )
        self.assertEqual(result, [])

    def test_multiple_recipients(self):
        result = trigger_notification_event(
            event_type=NotificationEventType.TASK_ASSIGNED,
            recipient=[self.user, self.user2],
            context={"task_title": "Multi"},
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].recipient, self.user)
        self.assertEqual(result[1].recipient, self.user2)

    def test_fallback_message_without_template(self):
        Notification.objects.filter(event_type=NotificationEventType.TASK_ASSIGNED).delete()
        result = trigger_notification_event(
            event_type=NotificationEventType.TASK_ASSIGNED,
            recipient=self.user,
            context={"task_title": "My Task"},
        )
        self.assertEqual(len(result), 1)
        self.assertIn("My Task", result[0].message)

    def test_fallback_generic_message_without_template_and_context(self):
        Notification.objects.filter(event_type=NotificationEventType.USER_ASSIGNED).delete()
        result = trigger_notification_event(
            event_type=NotificationEventType.USER_ASSIGNED,
            recipient=self.user,
        )
        self.assertEqual(len(result), 1)
        self.assertIn("USER_ASSIGNED", result[0].message)

    def test_custom_message_overrides_template(self):
        template = NotificationTemplate.objects.create(
            name="Override Test",
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Template says {{task_title}}",
            channel=NotificationChannel.IN_APP,
            is_default=True,
        )
        result = trigger_notification_event(
            event_type=NotificationEventType.TASK_ASSIGNED,
            recipient=self.user,
            custom_message="Custom: {{task_title}}",
            context={"task_title": "Override"},
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].message, "Custom: Override")

    def test_explicit_template_id_used(self):
        t1 = NotificationTemplate.objects.create(
            name="Default",
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Default: {{task_title}}",
            channel=NotificationChannel.IN_APP,
            is_default=True,
        )
        t2 = NotificationTemplate.objects.create(
            name="Explicit",
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Explicit: {{task_title}}",
            channel=NotificationChannel.IN_APP,
            is_default=False,
        )
        result = trigger_notification_event(
            event_type=NotificationEventType.TASK_ASSIGNED,
            recipient=self.user,
            context={"task_title": "Test"},
            template_id=t2.pk,
        )
        self.assertEqual(result[0].message, "Explicit: Test")

    def test_inactive_template_not_used(self):
        NotificationTemplate.objects.filter(
            event_type=NotificationEventType.TASK_ASSIGNED
        ).update(is_active=False)
        result = trigger_notification_event(
            event_type=NotificationEventType.TASK_ASSIGNED,
            recipient=self.user,
            context={"task_title": "Fallback"},
        )
        self.assertEqual(len(result), 1)
        self.assertIn("Fallback", result[0].message)

    def test_notification_stored_with_template_reference(self):
        template = NotificationTemplate.objects.create(
            name="Ref Test",
            event_type=NotificationEventType.TASK_COMPLETED,
            message="Done: {{task_title}}",
            channel=NotificationChannel.IN_APP,
            is_default=True,
        )
        result = trigger_notification_event(
            event_type=NotificationEventType.TASK_COMPLETED,
            recipient=self.user,
            context={"task_title": "Task X"},
        )
        self.assertEqual(result[0].template, template)

    def test_user_name_auto_populated_from_recipient(self):
        result = trigger_notification_event(
            event_type=NotificationEventType.TASK_ASSIGNED,
            recipient=self.user,
            custom_message="Hi {{user_name}}",
        )
        self.assertEqual(result[0].message, f"Hi {self.user.get_full_name() or self.user.username}")

    def test_employee_name_auto_populated_from_recipient(self):
        result = trigger_notification_event(
            event_type=NotificationEventType.TASK_ASSIGNED,
            recipient=self.user,
            custom_message="By {{employee_name}}",
        )
        self.assertEqual(result[0].message, f"By {self.user.get_full_name() or self.user.username}")

    def test_notification_not_read_by_default(self):
        result = trigger_notification_event(
            event_type=NotificationEventType.TASK_ASSIGNED,
            recipient=self.user,
            custom_message="Test",
        )
        self.assertFalse(result[0].is_read)
        self.assertIsNone(result[0].read_at)


# ==========================================================
# NOTIFICATION EMAIL UTILITY TESTS
# ==========================================================

class SendNotificationEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="emailuser",
            email="emailuser@example.com",
            phone_number="9113330060",
            password="Password@123",
        )

    def test_email_sent_on_email_channel(self):
        from Notification.notification_utils import send_notification_email
        mail.outbox = []
        result = send_notification_email(self.user, "TestSubject", "TestBody")
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("CRM Notification: TestSubject", mail.outbox[0].subject)

    def test_email_no_recipient_returns_false(self):
        from Notification.notification_utils import send_notification_email
        mail.outbox = []
        result = send_notification_email(None, "Subject", "Body")
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_user_without_email_returns_false(self):
        from Notification.notification_utils import send_notification_email
        self.user.email = ""
        self.user.save()
        mail.outbox = []
        result = send_notification_email(self.user, "Subject", "Body")
        self.assertFalse(result)


# ==========================================================
# NOTIFICATION MODEL TESTS
# ==========================================================

class NotificationModelTests(TestCase):
    def test_notification_str(self):
        user = User.objects.create_user(
            username="struser",
            email="struser@example.com",
            phone_number="9113330070",
            password="Password@123",
        )
        notif = Notification.objects.create(
            recipient=user,
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Test",
            channel=NotificationChannel.IN_APP,
        )
        self.assertIn(user.email, str(notif))
        self.assertIn("TASK_ASSIGNED", str(notif))

    def test_notification_template_str(self):
        tpl = NotificationTemplate.objects.create(
            name="Str Template",
            event_type=NotificationEventType.ROLE_CHANGED,
            message="Role changed",
            channel=NotificationChannel.IN_APP,
        )
        result = str(tpl)
        self.assertIn("Str Template", result)
        self.assertIn("ROLE_CHANGED", result)

    def test_notification_template_ordering(self):
        t1 = NotificationTemplate.objects.create(
            name="A",
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="A",
            channel=NotificationChannel.IN_APP,
            is_default=False,
        )
        t2 = NotificationTemplate.objects.create(
            name="B",
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="B",
            channel=NotificationChannel.IN_APP,
            is_default=True,
        )
        templates = list(
            NotificationTemplate.objects.filter(
                event_type=NotificationEventType.TASK_ASSIGNED
            )
        )
        self.assertEqual(templates[0].pk, t2.pk)

    def test_notification_cascade_delete_on_user(self):
        user = User.objects.create_user(
            username="cascadeuser",
            email="cascadeuser@example.com",
            phone_number="9113330071",
            password="Password@123",
        )
        user_id = user.user_id
        Notification.objects.create(
            recipient=user,
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Cascade test",
            channel=NotificationChannel.IN_APP,
        )
        self.assertEqual(Notification.objects.filter(recipient_id=user_id).count(), 1)
        user.delete()
        self.assertEqual(Notification.objects.filter(recipient_id=user_id).count(), 0)

    def test_template_set_null_on_notification_when_deleted(self):
        user = User.objects.create_user(
            username="tpldel",
            email="tpldel@example.com",
            phone_number="9113330072",
            password="Password@123",
        )
        tpl = NotificationTemplate.objects.create(
            name="Delete Me",
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Del",
            channel=NotificationChannel.IN_APP,
        )
        notif = Notification.objects.create(
            recipient=user,
            template=tpl,
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Has template",
            channel=NotificationChannel.IN_APP,
        )
        tpl.delete()
        notif.refresh_from_db()
        self.assertIsNone(notif.template)

    def test_notification_template_save_only_affects_same_event_type(self):
        t1 = NotificationTemplate.objects.create(
            name="Task Default",
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Task",
            channel=NotificationChannel.IN_APP,
            is_default=True,
        )
        t2 = NotificationTemplate.objects.create(
            name="Role Default",
            event_type=NotificationEventType.ROLE_CHANGED,
            message="Role",
            channel=NotificationChannel.IN_APP,
            is_default=True,
        )
        t3 = NotificationTemplate.objects.create(
            name="New Task Default",
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="New Task",
            channel=NotificationChannel.IN_APP,
            is_default=True,
        )
        t1.refresh_from_db()
        t2.refresh_from_db()
        self.assertFalse(t1.is_default)
        self.assertTrue(t2.is_default)
        self.assertTrue(t3.is_default)


# ==========================================================
# CREATE_NOTIFICATION BACKWARD COMPAT TESTS
# ==========================================================

class CreateNotificationBackwardCompatTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="compatuser",
            email="compatuser@example.com",
            phone_number="9113330080",
            password="Password@123",
        )

    def test_create_notification_returns_single_notification(self):
        from Notification.notification_utils import create_notification
        result = create_notification(
            user=self.user,
            title="Compat Test",
            message="Backward compat message",
            type_name="System",
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.recipient, self.user)
        self.assertEqual(result.message, "Backward compat message")

    def test_create_notification_with_no_user_returns_none(self):
        from Notification.notification_utils import create_notification
        result = create_notification(
            user=None,
            title="No User",
            message="Should fail gracefully",
        )
        self.assertIsNone(result)


# ==========================================================
# NOTIFICATION PERMISSION TESTS
# ==========================================================

class NotificationPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_role, _ = Role.objects.get_or_create(
            rolename="Admin", defaults={"description": "Administrator"}
        )
        self.manager_role, _ = Role.objects.get_or_create(
            rolename="Manager", defaults={"description": "Manager"}
        )
        self.employee_role, _ = Role.objects.get_or_create(
            rolename="Employee", defaults={"description": "Employee"}
        )
        self.admin_user = User.objects.create_superuser(
            username="permadmin",
            email="permadmin@example.com",
            phone_number="9113330090",
            password="Password@123",
            role=self.admin_role,
        )
        self.manager_user = User.objects.create_user(
            username="permmanager",
            email="permmanager@example.com",
            phone_number="9113330091",
            password="Password@123",
            role=self.manager_role,
        )
        self.employee_user = User.objects.create_user(
            username="permemp",
            email="permemp@example.com",
            phone_number="9113330092",
            password="Password@123",
            role=self.employee_role,
        )
        self.no_role_user = User.objects.create_user(
            username="permnorole",
            email="permnorole@example.com",
            phone_number="9113330093",
            password="Password@123",
        )
        self.user_notif = Notification.objects.create(
            recipient=self.employee_user,
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="Emp notif",
            channel=NotificationChannel.IN_APP,
        )

    def test_admin_can_create_template(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse("Notification:template-list-create"),
            {
                "name": "Admin Created",
                "event_type": "TASK_ASSIGNED",
                "message": "Admin msg",
                "channel": "IN_APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_manager_can_list_templates(self):
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.get(reverse("Notification:template-list-create"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employee_can_list_own_notifications(self):
        self.client.force_authenticate(user=self.employee_user)
        response = self.client.get(reverse("Notification:user-notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employee_can_mark_own_notification_read(self):
        self.client.force_authenticate(user=self.employee_user)
        url = reverse("Notification:user-notification-mark-read", kwargs={"pk": self.user_notif.id})
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employee_denied_template_create(self):
        self.client.force_authenticate(user=self.employee_user)
        response = self.client.post(
            reverse("Notification:template-list-create"),
            {"name": "X", "event_type": "TASK_ASSIGNED", "message": "X", "channel": "IN_APP"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_denied_manual_send(self):
        self.client.force_authenticate(user=self.employee_user)
        response = self.client.post(
            reverse("Notification:notification-send"),
            {
                "recipient_id": str(self.employee_user.user_id),
                "custom_message": "Test",
                "channel": "IN_APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_role_user_denied_template_list(self):
        self.client.force_authenticate(user=self.no_role_user)
        response = self.client.get(reverse("Notification:template-list-create"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_role_user_can_access_notification_list(self):
        self.client.force_authenticate(user=self.no_role_user)
        response = self.client.get(reverse("Notification:user-notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_role_user_can_mark_notification_read(self):
        notif = Notification.objects.create(
            recipient=self.no_role_user,
            event_type=NotificationEventType.TASK_ASSIGNED,
            message="No role notif",
            channel=NotificationChannel.IN_APP,
        )
        self.client.force_authenticate(user=self.no_role_user)
        url = reverse("Notification:user-notification-mark-read", kwargs={"pk": notif.id})
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
