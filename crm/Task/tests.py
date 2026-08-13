from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from FollowUp.models import Notification
from Task.models import Task, TaskCategory, TaskPriority, TaskStatus

User = get_user_model()

TASK_LIST_URL = "/api/tasks/"


class TaskAssignmentNotificationTests(TestCase):
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
            first_name="Eric",
            last_name="Tan",
        )

        self.status = TaskStatus.objects.create(status_name="To Do")
        self.priority = TaskPriority.objects.create(priority_name="High")
        self.category = TaskCategory.objects.create(category_name="Development")

        self.client = APIClient()
        self.client.force_authenticate(user=self.manager)

        self.employee_client = APIClient()
        self.employee_client.force_authenticate(user=self.employee)

    def test_unauthenticated_task_list_rejected(self):
        response = APIClient().get(TASK_LIST_URL)
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_employee_can_list_tasks(self):
        response = self.employee_client.get(TASK_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employee_cannot_create_task(self):
        response = self.employee_client.post(
            TASK_LIST_URL,
            self.task_payload(self.employee.user_id),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_create_task(self):
        response = self.client.post(
            TASK_LIST_URL,
            self.task_payload(self.employee.user_id),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_employee_cannot_assign_task(self):
        response = self.employee_client.post(
            f"/api/tasks/1/assign/",
            {"assigned_to": str(self.employee.user_id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def task_payload(self, assigned_to):
        return {
            "assigned_to": assigned_to,
            "task_title": "Build login page",
            "description": "Implement authentication UI",
            "status": self.status.status_id,
            "priority": self.priority.priority_id,
            "category": self.category.category_id,
        }

    def test_task_creation_notifies_assignee_with_manager_name(self):
        response = self.client.post(TASK_LIST_URL, self.task_payload(self.employee.user_id), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        notification = Notification.objects.filter(user_id=self.employee).first()
        self.assertIsNotNone(notification)
        self.assertIn("Build login page", notification.title)
        self.assertIn("Mona Lise", notification.message)
        self.assertIn("Build login page", notification.message)
        self.assertEqual(notification.status, Notification.Status.SENT)

    def test_task_creation_self_assigned_no_notification(self):
        response = self.client.post(TASK_LIST_URL, self.task_payload(self.manager.user_id), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Notification.objects.count(), 0)

    def test_task_reassignment_notifies_new_assignee(self):
        response = self.client.post(TASK_LIST_URL, self.task_payload(self.employee.user_id), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task_id = response.data["task_id"]

        other_employee = User.objects.create_user(
            username="employee2",
            email="employee2@example.com",
            password="Password123!",
            phone_number="3333333333",
            role=self.employee_role,
        )

        response = self.client.post(f"/api/tasks/{task_id}/assign/", {
            "assigned_to": other_employee.user_id,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        notifications = Notification.objects.filter(user_id=other_employee)
        self.assertEqual(notifications.count(), 1)
        self.assertIn("Mona Lise", notifications.first().message)
