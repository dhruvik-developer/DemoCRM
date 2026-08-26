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

from .models import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskCategory,
    Meeting,
    MeetingStatus,
    MeetingType,
    MeetingParticipant,
    Reminder,
    ReminderType,
    ReminderStatus,
)


class TaskAPITestCase(APITestCase):
    """
    Developer 3 - Task API tests
    """

    def setUp(self):
        self._patch_audit = patch("Task.views.log_audit", return_value=None)
        self._patch_audit.start()
        self._patch_activity = patch("Task.views.log_activity", return_value=None)
        self._patch_activity.start()
        self._patch_notify = patch("Task.views.trigger_notification_event")
        self._patch_notify.start()
        self._patch_tasks_notify = patch("Task.tasks.trigger_notification_event")
        self._patch_tasks_notify.start()
        self.addCleanup(self._patch_audit.stop)
        self.addCleanup(self._patch_activity.stop)
        self.addCleanup(self._patch_notify.stop)
        self.addCleanup(self._patch_tasks_notify.stop)

        # --------------------------------------------------
        # USER / ROLE
        # --------------------------------------------------

        self.role, _ = Role.objects.get_or_create(
            rolename="Employee",
            defaults={"description": "Employee role"},
        )

        ct = ContentType.objects.get_for_model(Task)
        for codename in (
            "add_task",
            "task_assign",
            "task_update",
            "view_task",
            "change_task",
            "delete_task",
            "change_taskstatus",
        ):
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                content_type=ct,
                defaults={"name": f"Can {codename}"},
            )
            self.role.permissions.add(perm)

        self.user = CustomUser.objects.create_user(
            email="taskuser@example.com",
            username="taskuser",
            password="Test@123",
            phone_number="9876543210",
            role=self.role,
        )

        # --------------------------------------------------
        # TASK MASTER DATA
        # --------------------------------------------------

        self.task_status = TaskStatus.objects.create(
            status_name="Pending",
            is_active=True,
        )

        self.task_priority = TaskPriority.objects.create(
            priority_name="High",
            description="High priority",
            is_active=True,
        )

        self.task_category = TaskCategory.objects.create(
            category_name="General",
            is_active=True,
        )

        # --------------------------------------------------
        # LEAD MASTER DATA
        # --------------------------------------------------

        self.lead_source = LeadSource.objects.create(
            name="Website",
            description="Website lead source",
            created_by=self.user,
        )

        self.pipeline = Pipeline.objects.create(
            name="Sales Pipeline",
            description="Test pipeline",
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

        # --------------------------------------------------
        # AUTHENTICATE
        # --------------------------------------------------

        self.client.force_authenticate(user=self.user)

        # --------------------------------------------------
        # COMMON DATES
        # --------------------------------------------------

        self.future_datetime = timezone.now() + timedelta(days=1)

        self.future_date = self.future_datetime.date()

        # --------------------------------------------------
        # TASK
        # --------------------------------------------------

        self.task = Task.objects.create(
            assigned_to=self.user,
            created_by=self.user,
            lead=self.lead,
            task_title="Call Rahul",
            description="Call Rahul about quotation",
            due_date=self.future_datetime,
            status=self.task_status,
            priority=self.task_priority,
            category=self.task_category,
            is_active=True,
        )

    # ======================================================
    # AUTHENTICATION
    # ======================================================

    def test_task_list_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/tasks/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ======================================================
    # TASK - CREATE
    # ======================================================

    def test_create_task(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "assigned_to": str(self.user.user_id),
                "lead": str(self.lead.id),
                "task_title": "New Task",
                "description": "New task description",
                "due_date": self.future_datetime.isoformat(),
                "status": self.task_status.status_id,
                "priority": self.task_priority.priority_id,
                "category": self.task_category.category_id,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        task = Task.objects.get(task_title="New Task")

        self.assertEqual(
            task.created_by,
            self.user,
        )

    # ======================================================
    # TASK - VALIDATION
    # ======================================================

    def test_create_task_without_title(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "assigned_to": str(self.user.user_id),
                "lead": str(self.lead.id),
                "description": "Missing title",
                "due_date": self.future_datetime.isoformat(),
                "status": self.task_status.status_id,
                "priority": self.task_priority.priority_id,
                "category": self.task_category.category_id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # ======================================================
    # TASK - DETAIL
    # ======================================================

    def test_get_task_detail(self):
        response = self.client.get(f"/api/tasks/{self.task.task_id}/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["task_id"],
            self.task.task_id,
        )

    # ======================================================
    # TASK - UPDATE
    # ======================================================

    def test_update_task(self):
        response = self.client.patch(
            f"/api/tasks/{self.task.task_id}/",
            {
                "task_title": "Updated Task",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.task_title,
            "Updated Task",
        )

    # ======================================================
    # TASK - SOFT DELETE
    # ======================================================

    def test_delete_task_soft_delete(self):
        response = self.client.delete(f"/api/tasks/{self.task.task_id}/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.task.refresh_from_db()

        self.assertFalse(self.task.is_active)

    # ======================================================
    # TASK - ASSIGN
    # ======================================================

    def test_assign_task(self):
        second_user = CustomUser.objects.create_user(
            email="second@example.com",
            username="seconduser",
            password="Test@123",
            phone_number="9999999998",
            role=self.role,
        )

        response = self.client.post(
            f"/api/tasks/{self.task.task_id}/assign/",
            {
                "assigned_to": str(second_user.user_id),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.assigned_to,
            second_user,
        )

    # ======================================================
    # TASK - STATUS
    # ======================================================

    def test_update_task_status(self):
        completed_status = TaskStatus.objects.create(
            status_name="Completed",
            is_active=True,
        )

        response = self.client.patch(
            f"/api/tasks/{self.task.task_id}/status/",
            {
                "status_id": completed_status.status_id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.status,
            completed_status,
        )

    # ======================================================
    # TASK - PAGINATION
    # ======================================================

    def test_task_pagination(self):
        for number in range(15):
            Task.objects.create(
                assigned_to=self.user,
                created_by=self.user,
                lead=self.lead,
                task_title=f"Task {number}",
                description="Pagination test",
                due_date=self.future_datetime,
                status=self.task_status,
                priority=self.task_priority,
                category=self.task_category,
                is_active=True,
            )

        response = self.client.get("/api/tasks/?page=1&page_size=10")

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
    # TASK - FILTER
    # ======================================================

    def test_task_filter_by_status(self):
        response = self.client.get(f"/api/tasks/?status={self.task_status.status_id}")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "results",
            response.data,
        )

    # ======================================================
    # TASK - SEARCH
    # ======================================================

    def test_task_search(self):
        response = self.client.get("/api/tasks/?search=Rahul")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "results",
            response.data,
        )

    # ======================================================
    # TASK - ORDERING
    # ======================================================

    def test_task_ordering(self):
        response = self.client.get("/api/tasks/?ordering=-created_at")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "results",
            response.data,
        )


class MeetingAPITestCase(APITestCase):
    """
    Developer 3 - Meeting API tests
    """

    def setUp(self):
        self._patch_audit = patch("Task.views.log_audit", return_value=None)
        self._patch_audit.start()
        self._patch_activity = patch("Task.views.log_activity", return_value=None)
        self._patch_activity.start()
        self._patch_notify = patch("Task.views.trigger_notification_event")
        self._patch_notify.start()
        self._patch_tasks_notify = patch("Task.tasks.trigger_notification_event")
        self._patch_tasks_notify.start()
        self.addCleanup(self._patch_audit.stop)
        self.addCleanup(self._patch_activity.stop)
        self.addCleanup(self._patch_notify.stop)
        self.addCleanup(self._patch_tasks_notify.stop)

        # --------------------------------------------------
        # USER / ROLE
        # --------------------------------------------------

        self.role, _ = Role.objects.get_or_create(
            rolename="Employee",
            defaults={"description": "Employee role"},
        )

        self.manager_role, _ = Role.objects.get_or_create(
            rolename="Manager",
            defaults={"description": "Manager role"},
        )

        ct = ContentType.objects.get_for_model(Task)
        for codename in (
            "view_meeting",
            "add_meeting",
            "change_meeting",
            "delete_meeting",
            "meeting_approve",
            "view_meetingparticipant",
            "add_meetingparticipant",
            "change_meetingparticipant",
            "delete_meetingparticipant",
        ):
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                content_type=ct,
                defaults={"name": f"Can {codename}"},
            )
            self.role.permissions.add(perm)
            self.manager_role.permissions.add(perm)

        self.user = CustomUser.objects.create_user(
            email="meetinguser@example.com",
            username="meetinguser",
            password="Test@123",
            phone_number="9876543211",
            role=self.role,
        )

        self.manager = CustomUser.objects.create_user(
            email="manageruser@example.com",
            username="manageruser",
            password="Test@123",
            phone_number="9876543299",
            role=self.manager_role,
        )

        self.client.force_authenticate(user=self.user)

        # --------------------------------------------------
        # TASK MASTER DATA
        # --------------------------------------------------

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

        # --------------------------------------------------
        # LEAD
        # --------------------------------------------------

        self.lead_source = LeadSource.objects.create(
            name="Referral",
            description="Referral lead",
            created_by=self.user,
        )

        self.pipeline = Pipeline.objects.create(
            name="Meeting Pipeline",
            description="Meeting pipeline",
            created_by=self.user,
        )

        self.pipeline_stage = PipelineStage.objects.create(
            pipeline=self.pipeline,
            name="Interested",
            description="Interested lead",
            display_order=1,
        )

        self.lead = Lead.objects.create(
            name="Rahul",
            email="rahul-meeting@example.com",
            phone="9999999997",
            company_name="Rahul Company",
            source=self.lead_source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.pipeline_stage,
            status=Lead.Status.ACTIVE,
        )

        # --------------------------------------------------
        # TASK
        # --------------------------------------------------

        self.task = Task.objects.create(
            assigned_to=self.user,
            created_by=self.user,
            lead=self.lead,
            task_title="Meeting Task",
            description="Task for meeting",
            due_date=timezone.now() + timedelta(days=1),
            status=self.task_status,
            priority=self.task_priority,
            category=self.task_category,
            is_active=True,
        )

        # --------------------------------------------------
        # MEETING MASTER DATA
        # --------------------------------------------------

        self.meeting_status = MeetingStatus.objects.create(
            status_name="Scheduled",
            is_active=True,
        )

        self.online_meeting_type = MeetingType.objects.create(
            meeting_type_id=1,
            type_name="Online",
            is_active=True,
        )

        self.offline_meeting_type = MeetingType.objects.create(
            meeting_type_id=2,
            type_name="Offline",
            is_active=True,
        )

        self.custom_meeting_type = MeetingType.objects.create(
            meeting_type_id=3,
            type_name="Custom",
            is_active=True,
        )

        self.meeting_type = self.online_meeting_type

    # ======================================================
    # CREATE MEETING
    # ======================================================

    def test_create_meeting(self):
        response = self.client.post(
            "/api/tasks/meetings/",
            {
                "task_id": self.task.task_id,
                "lead": str(self.lead.id),
                "manager": str(self.manager.user_id),
                "meeting_status_id": (self.meeting_status.meeting_status_id),
                "meeting_type_id": (self.online_meeting_type.meeting_type_id),
                "meeting_title": "Client Meeting",
                "meeting_date": (timezone.now() + timedelta(days=1)).date().isoformat(),
                "start_time": "10:00:00",
                "end_time": "11:00:00",
                "location": "Office",
                "description": "Discuss quotation",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(Meeting.objects.filter(meeting_title="Client Meeting").exists())
        meeting = Meeting.objects.get(meeting_title="Client Meeting")
        self.assertEqual(meeting.approval_status, Meeting.ApprovalStatus.PENDING)
        self.assertTrue(bool(meeting.meeting_link))

    # ======================================================
    # MEETING - INVALID TIME
    # ======================================================

    def test_create_meeting_invalid_time(self):
        response = self.client.post(
            "/api/tasks/meetings/",
            {
                "task_id": self.task.task_id,
                "lead": str(self.lead.id),
                "manager": str(self.manager.user_id),
                "meeting_status_id": (self.meeting_status.meeting_status_id),
                "meeting_type_id": (self.meeting_type.meeting_type_id),
                "meeting_title": "Invalid Meeting",
                "meeting_date": (timezone.now() + timedelta(days=1)).date().isoformat(),
                "start_time": "11:00:00",
                "end_time": "10:00:00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # ======================================================
    # MEETING - DETAIL
    # ======================================================

    def test_meeting_detail(self):
        meeting = self.create_meeting(meeting_title="Existing Meeting")

        response = self.client.get(f"/api/tasks/meetings/{meeting.meeting_id}/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    # ======================================================
    # TEMPLATE 1: ONLINE MEETING WORKFLOW
    # ======================================================

    def test_create_and_approve_online_meeting_template_1(self):
        # 1. Employee creates Online meeting
        response = self.client.post(
            "/api/tasks/meetings/",
            {
                "task_id": self.task.task_id,
                "lead": str(self.lead.id),
                "manager": str(self.manager.user_id),
                "meeting_status_id": self.meeting_status.meeting_status_id,
                "meeting_type_id": self.online_meeting_type.meeting_type_id,
                "meeting_title": "Online Client Review",
                "meeting_date": (timezone.now() + timedelta(days=1)).date().isoformat(),
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "description": "Quarterly review with client",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        meeting = Meeting.objects.get(meeting_title="Online Client Review")
        self.assertEqual(meeting.approval_status, Meeting.ApprovalStatus.PENDING)
        self.assertTrue(meeting.meeting_link.startswith("https://meet.google.com/"))

        # 2. Manager Approves
        self.client.force_authenticate(user=self.manager)
        approval_resp = self.client.patch(
            f"/api/tasks/meetings/{meeting.meeting_id}/approval/",
            {"approval_status": "APPROVED"},
            format="json",
        )
        self.assertEqual(approval_resp.status_code, status.HTTP_200_OK)
        meeting.refresh_from_db()
        self.assertEqual(meeting.approval_status, Meeting.ApprovalStatus.APPROVED)
        self.assertEqual(meeting.approved_by, self.manager)

    # ======================================================
    # TEMPLATE 2: OFFLINE MEETING WORKFLOW
    # ======================================================

    def test_create_and_approve_offline_meeting_template_2(self):
        # 1. Employee creates Offline meeting
        response = self.client.post(
            "/api/tasks/meetings/",
            {
                "task_id": self.task.task_id,
                "lead": str(self.lead.id),
                "manager": str(self.manager.user_id),
                "meeting_status_id": self.meeting_status.meeting_status_id,
                "meeting_type_id": self.offline_meeting_type.meeting_type_id,
                "meeting_title": "In-Office Discussion",
                "meeting_date": (timezone.now() + timedelta(days=1)).date().isoformat(),
                "start_time": "11:00:00",
                "end_time": "12:00:00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        meeting = Meeting.objects.get(meeting_title="In-Office Discussion")
        self.assertEqual(meeting.approval_status, Meeting.ApprovalStatus.PENDING)
        self.assertTrue(bool(meeting.location))

        # 2. Manager Approves (offline meeting must succeed without meet link error)
        self.client.force_authenticate(user=self.manager)
        approval_resp = self.client.patch(
            f"/api/tasks/meetings/{meeting.meeting_id}/approval/",
            {"approval_status": "APPROVED"},
            format="json",
        )
        self.assertEqual(approval_resp.status_code, status.HTTP_200_OK)
        meeting.refresh_from_db()
        self.assertEqual(meeting.approval_status, Meeting.ApprovalStatus.APPROVED)

    # ======================================================
    # TEMPLATE 3: CUSTOM MEETING WORKFLOW
    # ======================================================

    def test_create_and_approve_custom_meeting_template_3(self):
        response = self.client.post(
            "/api/tasks/meetings/",
            {
                "task_id": self.task.task_id,
                "lead": str(self.lead.id),
                "manager": str(self.manager.user_id),
                "meeting_status_id": self.meeting_status.meeting_status_id,
                "meeting_type_id": self.custom_meeting_type.meeting_type_id,
                "meeting_title": "Custom Demo Meeting",
                "meeting_date": (timezone.now() + timedelta(days=1)).date().isoformat(),
                "start_time": "16:00:00",
                "end_time": "17:00:00",
                "location": "Client HQ - Conference Room 3",
                "description": "Product demo customized session",
                "extra_fields": {
                    "agenda": "DemoCRM V2 walkthrough",
                    "device": "Laptop + Projector",
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        meeting = Meeting.objects.get(meeting_title="Custom Demo Meeting")
        self.assertEqual(meeting.extra_fields.get("agenda"), "DemoCRM V2 walkthrough")

        # Manager Approves
        self.client.force_authenticate(user=self.manager)
        approval_resp = self.client.patch(
            f"/api/tasks/meetings/{meeting.meeting_id}/approval/",
            {"approval_status": "APPROVED"},
            format="json",
        )
        self.assertEqual(approval_resp.status_code, status.HTTP_200_OK)
        meeting.refresh_from_db()
        self.assertEqual(meeting.approval_status, Meeting.ApprovalStatus.APPROVED)

    # ======================================================
    # REJECTION & RESCHEDULE FLOW
    # ======================================================

    def test_manager_reject_and_employee_reschedule_flow(self):
        meeting = self.create_meeting(meeting_title="Rejection Flow Test")

        # Manager Rejects
        self.client.force_authenticate(user=self.manager)
        reject_resp = self.client.patch(
            f"/api/tasks/meetings/{meeting.meeting_id}/approval/",
            {
                "approval_status": "REJECTED",
                "rejection_reason": "Manager busy with quarterly closing",
            },
            format="json",
        )
        self.assertEqual(reject_resp.status_code, status.HTTP_200_OK)
        meeting.refresh_from_db()
        self.assertEqual(meeting.approval_status, Meeting.ApprovalStatus.REJECTED)
        self.assertEqual(
            meeting.rejection_reason, "Manager busy with quarterly closing"
        )

        # Employee Reschedules
        self.client.force_authenticate(user=self.user)
        new_date = (timezone.now() + timedelta(days=3)).date().isoformat()
        resched_resp = self.client.patch(
            f"/api/tasks/meetings/{meeting.meeting_id}/reschedule/",
            {
                "meeting_date": new_date,
                "start_time": "15:00:00",
                "end_time": "16:00:00",
            },
            format="json",
        )
        self.assertEqual(resched_resp.status_code, status.HTTP_200_OK)
        meeting.refresh_from_db()
        self.assertEqual(meeting.approval_status, Meeting.ApprovalStatus.PENDING)
        self.assertIsNone(meeting.rejection_reason)
        self.assertEqual(str(meeting.start_time), "15:00:00")

    # ======================================================
    # 5-MINUTE REMINDER CELERY BEAT JOB
    # ======================================================

    def test_celery_5_minute_meeting_reminder_job(self):
        from Task.tasks import meeting_reminder_job
        import pytz
        from django.conf import settings

        tz = pytz.timezone(settings.CELERY_TIMEZONE)
        now = timezone.now().astimezone(tz)
        meeting = self.create_meeting(
            meeting_title="Upcoming 5-Min Meeting",
            meeting_date=now.date(),
            start_time=(now + timedelta(minutes=4, seconds=45)).time(),
            end_time=(now + timedelta(minutes=35)).time(),
            approval_status=Meeting.ApprovalStatus.APPROVED,
        )

        result_msg = meeting_reminder_job()
        meeting.refresh_from_db()
        self.assertIsNotNone(meeting.reminder_sent_at)
        self.assertIn("meeting reminders", result_msg.lower())

    @patch("Task.services.send_mail")
    def test_5_minute_reminder_isolates_failed_recipient(self, mock_send_mail):
        from Task.services import send_meeting_5_minute_reminder

        meeting = self.create_meeting(
            meeting_title="Partial Email Failure",
            approval_status=Meeting.ApprovalStatus.APPROVED,
        )

        failed_email = meeting.lead.email

        def send_with_customer_failure(*args, **kwargs):
            if kwargs["recipient_list"] == [failed_email]:
                raise RuntimeError("Recipient rejected")
            return 1

        mock_send_mail.side_effect = send_with_customer_failure

        self.assertTrue(send_meeting_5_minute_reminder(meeting))
        attempted_recipients = [
            call.kwargs["recipient_list"] for call in mock_send_mail.call_args_list
        ]
        self.assertIn([failed_email], attempted_recipients)
        self.assertIn([meeting.created_by.email], attempted_recipients)
        self.assertIn([meeting.manager.email], attempted_recipients)

    # ======================================================
    # MEETING - RESCHEDULE
    # ======================================================

    def test_reschedule_meeting(self):
        meeting = self.create_meeting(approval_status=Meeting.ApprovalStatus.REJECTED)

        response = self.client.patch(
            f"/api/tasks/meetings/{meeting.meeting_id}/reschedule/",
            {
                "meeting_date": (timezone.now() + timedelta(days=2)).date().isoformat(),
                "start_time": "14:00:00",
                "end_time": "15:00:00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        meeting.refresh_from_db()

        self.assertEqual(
            str(meeting.start_time),
            "14:00:00",
        )

    # ======================================================
    # MEETING - STATUS
    # ======================================================

    def test_update_meeting_status(self):
        meeting = self.create_meeting()

        completed_status = MeetingStatus.objects.create(
            status_name="Completed",
            is_active=True,
        )

        response = self.client.patch(
            f"/api/tasks/meetings/{meeting.meeting_id}/status/",
            {
                "meeting_status_id": (completed_status.meeting_status_id),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        meeting.refresh_from_db()

        self.assertEqual(
            meeting.meeting_status_id,
            completed_status,
        )

    # ======================================================
    # MEETING - ADD PARTICIPANT
    # ======================================================

    def test_add_meeting_participant(self):
        meeting = self.create_meeting()

        second_user = CustomUser.objects.create_user(
            email="participant@example.com",
            username="participant",
            password="Test@123",
            phone_number="9999999996",
            role=self.role,
        )

        response = self.client.post(
            f"/api/tasks/meetings/{meeting.meeting_id}/participants/",
            {
                "user_id": str(second_user.user_id),
                "participant_role": "Client Representative",
                "is_required": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            MeetingParticipant.objects.filter(
                meeting_id=meeting,
                user_id=second_user,
            ).exists()
        )

    # ======================================================
    # MEETING - REMOVE PARTICIPANT
    # ======================================================

    def test_remove_meeting_participant(self):
        meeting = self.create_meeting()

        participant = CustomUser.objects.create_user(
            email="remove@example.com",
            username="removeuser",
            password="Test@123",
            phone_number="9999999995",
            role=self.role,
        )

        MeetingParticipant.objects.create(
            meeting_id=meeting,
            user_id=participant,
            participant_role="Participant",
            is_required=True,
        )

        response = self.client.delete(
            f"/api/tasks/meetings/"
            f"{meeting.meeting_id}/participants/"
            f"{participant.user_id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            MeetingParticipant.objects.filter(
                meeting_id=meeting,
                user_id=participant,
            ).exists()
        )

    def test_meeting_not_found(self):
        response = self.client.get("/api/tasks/meetings/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_meeting_forbidden_for_other_user(self):
        basic_role, _ = Role.objects.get_or_create(
            rolename="Basic",
            defaults={"description": "No meeting permissions"},
        )
        other_user = CustomUser.objects.create_user(
            email="meetingother@example.com",
            username="meetingother",
            password="Test@123",
            phone_number="9999999992",
            role=basic_role,
        )
        meeting = self.create_meeting()
        self.client.force_authenticate(user=other_user)
        response = self.client.get(f"/api/tasks/meetings/{meeting.meeting_id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reschedule_meeting_only_time(self):
        meeting = self.create_meeting(approval_status=Meeting.ApprovalStatus.REJECTED)
        response = self.client.patch(
            f"/api/tasks/meetings/{meeting.meeting_id}/reschedule/",
            {
                "start_time": "14:00:00",
                "end_time": "15:00:00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meeting.refresh_from_db()
        self.assertEqual(str(meeting.start_time), "14:00:00")
        self.assertEqual(str(meeting.end_time), "15:00:00")

    def test_reschedule_meeting_empty_data(self):
        meeting = self.create_meeting(approval_status=Meeting.ApprovalStatus.REJECTED)
        response = self.client.patch(
            f"/api/tasks/meetings/{meeting.meeting_id}/reschedule/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ======================================================
    # HELPERS
    # ======================================================

    def future_date(self):
        return (timezone.now() + timedelta(days=1)).date()

    def create_meeting(self, **kwargs):
        defaults = {
            "task_id": self.task,
            "lead": self.lead,
            "meeting_status_id": self.meeting_status,
            "meeting_type_id": self.meeting_type,
            "meeting_title": "Test Meeting",
            "meeting_date": self.future_date(),
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "location": "Office",
            "description": "Test meeting",
            "created_by": self.user,
            "manager": self.manager,
            "approval_status": Meeting.ApprovalStatus.PENDING,
        }
        defaults.update(kwargs)
        return Meeting.objects.create(**defaults)


class ReminderAPITestCase(APITestCase):
    """
    Developer 3 - Reminder API tests
    """

    def setUp(self):
        self._patch_audit = patch("Task.views.log_audit", return_value=None)
        self._patch_audit.start()
        self._patch_activity = patch("Task.views.log_activity", return_value=None)
        self._patch_activity.start()
        self._patch_notify = patch("Task.views.trigger_notification_event")
        self._patch_notify.start()
        self._patch_tasks_notify = patch("Task.tasks.trigger_notification_event")
        self._patch_tasks_notify.start()
        self.addCleanup(self._patch_audit.stop)
        self.addCleanup(self._patch_activity.stop)
        self.addCleanup(self._patch_notify.stop)
        self.addCleanup(self._patch_tasks_notify.stop)

        # --------------------------------------------------
        # USER / ROLE
        # --------------------------------------------------

        self.role, _ = Role.objects.get_or_create(
            rolename="Employee",
            defaults={"description": "Employee role"},
        )

        self.manager_role, _ = Role.objects.get_or_create(
            rolename="Manager",
            defaults={"description": "Manager role"},
        )

        ct = ContentType.objects.get_for_model(Task)
        for codename in ("add_reminder", "view_reminder", "change_reminder", "delete_reminder"):
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                content_type=ct,
                defaults={"name": f"Can {codename}"},
            )
            self.role.permissions.add(perm)

        self.user = CustomUser.objects.create_user(
            email="reminderuser@example.com",
            username="reminderuser",
            password="Test@123",
            phone_number="9876543212",
            role=self.role,
        )

        self.manager = CustomUser.objects.create_user(
            email="remindermanager@example.com",
            username="remindermanager",
            password="Test@123",
            phone_number="9876543298",
            role=self.manager_role,
        )

        self.client.force_authenticate(user=self.user)

        # --------------------------------------------------
        # TASK DATA
        # --------------------------------------------------

        self.task_status = TaskStatus.objects.create(
            status_name="Pending",
            is_active=True,
        )

        self.task_priority = TaskPriority.objects.create(
            priority_name="Low",
            description="Low priority",
            is_active=True,
        )

        self.task_category = TaskCategory.objects.create(
            category_name="General",
            is_active=True,
        )

        # --------------------------------------------------
        # LEAD
        # --------------------------------------------------

        self.lead_source = LeadSource.objects.create(
            name="Reminder Source",
            description="Reminder test source",
            created_by=self.user,
        )

        self.pipeline = Pipeline.objects.create(
            name="Reminder Pipeline",
            description="Reminder pipeline",
            created_by=self.user,
        )

        self.pipeline_stage = PipelineStage.objects.create(
            pipeline=self.pipeline,
            name="Reminder Stage",
            description="Reminder stage",
            display_order=1,
        )

        self.lead = Lead.objects.create(
            name="Rahul",
            email="rahul-reminder@example.com",
            phone="9999999994",
            company_name="Reminder Company",
            source=self.lead_source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.pipeline_stage,
            status=Lead.Status.ACTIVE,
        )

        self.task = Task.objects.create(
            assigned_to=self.user,
            created_by=self.user,
            lead=self.lead,
            task_title="Reminder Task",
            description="Reminder test task",
            due_date=timezone.now() + timedelta(days=1),
            status=self.task_status,
            priority=self.task_priority,
            category=self.task_category,
            is_active=True,
        )

        # --------------------------------------------------
        # MEETING
        # --------------------------------------------------

        self.meeting_status = MeetingStatus.objects.create(
            status_name="Scheduled",
            is_active=True,
        )

        self.meeting_type = MeetingType.objects.create(
            type_name="Online",
            is_active=True,
        )

        self.meeting = Meeting.objects.create(
            task_id=self.task,
            lead=self.lead,
            meeting_status_id=self.meeting_status,
            meeting_type_id=self.meeting_type,
            meeting_title="Reminder Meeting",
            meeting_date=(timezone.now() + timedelta(days=1)).date(),
            start_time="10:00:00",
            end_time="11:00:00",
            location="Office",
            description="Reminder meeting",
            created_by=self.user,
            manager=self.manager,
        )

        # --------------------------------------------------
        # REMINDER MASTER DATA
        # --------------------------------------------------

        self.reminder_type = ReminderType.objects.create(
            type_name="Meeting Reminder",
            is_active=True,
        )

        self.reminder_status = ReminderStatus.objects.create(
            status_name="Pending",
            is_active=True,
        )

    # ======================================================
    # CREATE REMINDER
    # ======================================================

    def test_create_reminder(self):
        reminder_datetime = timezone.now() + timedelta(hours=1)

        response = self.client.post(
            "/api/tasks/reminders/",
            {
                "task_id": self.task.task_id,
                "meeting_id": self.meeting.meeting_id,
                "reminder_type_id": (self.reminder_type.reminder_type_id),
                "reminder_status_id": (self.reminder_status.reminder_status_id),
                "reminder_datetime": (reminder_datetime.isoformat()),
                "message": "Meeting reminder",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(Reminder.objects.filter(message="Meeting reminder").exists())

    # ======================================================
    # REMINDER DETAIL
    # ======================================================

    def test_reminder_detail(self):
        reminder = Reminder.objects.create(
            task_id=self.task,
            meeting_id=self.meeting,
            reminder_type_id=self.reminder_type,
            reminder_status_id=self.reminder_status,
            reminder_datetime=(timezone.now() + timedelta(hours=1)),
            message="Existing reminder",
            created_by=self.user,
        )

        response = self.client.get(f"/api/tasks/reminders/{reminder.reminder_id}/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    # ======================================================
    # UPDATE REMINDER
    # ======================================================

    def test_update_reminder(self):
        reminder = Reminder.objects.create(
            task_id=self.task,
            meeting_id=self.meeting,
            reminder_type_id=self.reminder_type,
            reminder_status_id=self.reminder_status,
            reminder_datetime=(timezone.now() + timedelta(hours=1)),
            message="Old reminder",
            created_by=self.user,
        )

        response = self.client.patch(
            f"/api/tasks/reminders/{reminder.reminder_id}/",
            {
                "message": "Updated reminder",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        reminder.refresh_from_db()

        self.assertEqual(
            reminder.message,
            "Updated reminder",
        )

    # ======================================================
    # DELETE REMINDER
    # ======================================================

    def test_delete_reminder(self):
        reminder = Reminder.objects.create(
            task_id=self.task,
            meeting_id=self.meeting,
            reminder_type_id=self.reminder_type,
            reminder_status_id=self.reminder_status,
            reminder_datetime=(timezone.now() + timedelta(hours=1)),
            message="Delete reminder",
            created_by=self.user,
        )

        response = self.client.delete(f"/api/tasks/reminders/{reminder.reminder_id}/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            Reminder.objects.filter(reminder_id=reminder.reminder_id).exists()
        )

    # ======================================================
    # UPDATE REMINDER STATUS
    # ======================================================

    def test_update_reminder_status(self):
        reminder = Reminder.objects.create(
            task_id=self.task,
            meeting_id=self.meeting,
            reminder_type_id=self.reminder_type,
            reminder_status_id=self.reminder_status,
            reminder_datetime=(timezone.now() + timedelta(hours=1)),
            message="Status reminder",
            created_by=self.user,
        )

        sent_status = ReminderStatus.objects.create(
            status_name="Sent",
            is_active=True,
        )

        response = self.client.patch(
            f"/api/tasks/reminders/{reminder.reminder_id}/status/",
            {
                "reminder_status_id": (sent_status.reminder_status_id),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        reminder.refresh_from_db()

        self.assertEqual(
            reminder.reminder_status_id,
            sent_status,
        )

    # ======================================================
    # ERROR & EDGE CASE TESTS
    # ======================================================

    def test_reminder_not_found(self):
        response = self.client.get("/api/tasks/reminders/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reminder_forbidden_for_other_user(self):
        basic_role, _ = Role.objects.get_or_create(
            rolename="Basic",
            defaults={"description": "No reminder permissions"},
        )
        other_user = CustomUser.objects.create_user(
            email="other@example.com",
            username="otheruser",
            password="Test@123",
            phone_number="9999999993",
            role=basic_role,
        )
        reminder = Reminder.objects.create(
            task_id=self.task,
            meeting_id=None,
            reminder_for=self.user,
            reminder_type_id=self.reminder_type,
            reminder_status_id=self.reminder_status,
            reminder_datetime=timezone.now() + timedelta(hours=1),
            message="Private reminder",
            created_by=self.user,
        )
        self.client.force_authenticate(user=other_user)
        response = self.client.get(f"/api/tasks/reminders/{reminder.reminder_id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_process_due_meeting_reminders_task_and_meeting(self):
        from Task.services import process_due_meeting_reminders

        # Create a due standalone reminder
        due_reminder = Reminder.objects.create(
            task_id=self.task,
            meeting_id=None,
            reminder_for=self.user,
            reminder_type_id=self.reminder_type,
            reminder_status_id=self.reminder_status,
            reminder_datetime=timezone.now() - timedelta(minutes=5),
            message="Due task reminder",
            created_by=self.user,
            is_sent=False,
        )
        sent_count = process_due_meeting_reminders()
        self.assertGreaterEqual(sent_count, 1)
        due_reminder.refresh_from_db()
        self.assertTrue(due_reminder.is_sent)
