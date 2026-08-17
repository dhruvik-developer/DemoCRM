from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from Notification.models import Notification, NotificationTemplate, NotificationEventType

User = get_user_model()

TEMPLATE_LIST_URL = "/api/followups/notification-templates/"
PREVIEW_URL = "/api/followups/notifications/preview/"
SEND_URL = "/api/followups/notifications/send/"


class NotificationTemplateBaseTestCase(TestCase):
    def setUp(self):
        self.manager_role, _ = Role.objects.get_or_create(rolename="Manager")
        self.employee_role, _ = Role.objects.get_or_create(rolename="Employee")

        self.manager = User.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="Password123!",
            phone_number="1111111111",
            role=self.manager_role,
            first_name="Mona",
            last_name="Lise",
        )
        self.employee = User.objects.create_user(
            username="employee",
            email="employee@example.com",
            password="Password123!",
            phone_number="2222222222",
            role=self.employee_role,
        )

        self.type, _ = NotificationEventType.objects.get_or_create(
            type_name="Follow-up"
        )
        self.template = NotificationTemplate.objects.create(
            name="Follow-up Reminder",
            notification_type_id=self.type,
            subject="Reminder for {{full_name}}",
            body="Hi {{first_name}}, you have a follow-up scheduled.",
        )

        self.manager_client = APIClient()
        self.manager_client.force_authenticate(user=self.manager)

        self.employee_client = APIClient()
        self.employee_client.force_authenticate(user=self.employee)


class NotificationTemplateListTests(NotificationTemplateBaseTestCase):
    def test_unauthenticated_template_list_rejected(self):
        response = APIClient().get(TEMPLATE_LIST_URL)
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_template_list_returns_active_templates(self):
        response = self.manager_client.get(TEMPLATE_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Follow-up Reminder")

    def test_inactive_template_excluded(self):
        self.template.is_active = False
        self.template.save()
        response = self.manager_client.get(TEMPLATE_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class NotificationPreviewTests(NotificationTemplateBaseTestCase):
    def test_preview_renders_placeholders(self):
        response = self.manager_client.post(PREVIEW_URL, {
            "recipients": [str(self.manager.user_id)],
            "template_id": self.template.template_id,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["subject"], "Reminder for Mona Lise")
        self.assertIn("Hi Mona,", response.data["body"])

    def test_preview_unknown_recipient_rejected(self):
        response = self.manager_client.post(PREVIEW_URL, {
            "recipients": ["00000000-0000-0000-0000-000000000000"],
            "template_id": self.template.template_id,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_preview_inactive_template_rejected(self):
        self.template.is_active = False
        self.template.save()
        response = self.manager_client.post(PREVIEW_URL, {
            "recipients": [str(self.manager.user_id)],
            "template_id": self.template.template_id,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class NotificationSendTests(NotificationTemplateBaseTestCase):
    def test_send_creates_notification_for_each_recipient(self):
        response = self.manager_client.post(SEND_URL, {
            "recipients": [
                str(self.manager.user_id),
                str(self.employee.user_id),
            ],
            "template_id": self.template.template_id,
            "notification_type_id": self.type.notification_type_id,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(Notification.objects.count(), 2)
        for notification in Notification.objects.all():
            self.assertEqual(notification.status, Notification.Status.SENT)
            self.assertIsNotNone(notification.sent_at)
            self.assertFalse(notification.is_customized)

    def test_send_employee_cannot_customize_message(self):
        response = self.employee_client.post(SEND_URL, {
            "recipients": [str(self.employee.user_id)],
            "template_id": self.template.template_id,
            "message": "Custom text from employee",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Notification.objects.count(), 0)

    def test_send_manager_can_customize_message(self):
        response = self.manager_client.post(SEND_URL, {
            "recipients": [str(self.employee.user_id)],
            "template_id": self.template.template_id,
            "message": "Edited by manager",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification = Notification.objects.get()
        self.assertEqual(notification.message, "Edited by manager")
        self.assertTrue(notification.is_customized)
        self.assertEqual(notification.edited_by, self.manager)

    def test_send_scheduled_notification_not_emailed(self):
        future = timezone.now() + timezone.timedelta(hours=2)
        response = self.manager_client.post(SEND_URL, {
            "recipients": [str(self.employee.user_id)],
            "template_id": self.template.template_id,
            "scheduled_at": future.isoformat(),
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification = Notification.objects.get()
        self.assertEqual(notification.status, Notification.Status.SCHEDULED)
        self.assertIsNone(notification.sent_at)

    def test_send_scheduled_at_in_past_rejected(self):
        past = (timezone.now() - timezone.timedelta(hours=2)).isoformat()
        response = self.manager_client.post(SEND_URL, {
            "recipients": [str(self.employee.user_id)],
            "template_id": self.template.template_id,
            "scheduled_at": past,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Notification.objects.count(), 0)
