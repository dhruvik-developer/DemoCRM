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
