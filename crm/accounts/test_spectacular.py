"""
Tests for drf-spectacular OpenAPI / Swagger documentation.
Verifies schema generation, endpoint coverage, and tag consistency.
"""
from django.test import TestCase
from drf_spectacular.generators import SchemaGenerator


class SchemaGenerationTests(TestCase):
    """Ensure the OpenAPI schema can be generated without errors."""

    def setUp(self):
        generator = SchemaGenerator()
        self.schema = generator.get_schema(request=None, public=True)

    def test_schema_generates_successfully(self):
        self.assertIsNotNone(self.schema)
        self.assertIn("openapi", self.schema)
        self.assertIn("paths", self.schema)
        self.assertIn("components", self.schema)

    def test_schema_version(self):
        self.assertEqual(self.schema["openapi"], "3.0.3")

    def test_info_section(self):
        info = self.schema["info"]
        self.assertEqual(info["title"], "DemoCRM API")
        self.assertEqual(info["version"], "1.0.0")
        self.assertIn("description", info)

    def test_security_schemes_defined(self):
        security_schemes = self.schema["components"].get("securitySchemes", {})
        self.assertIn("jwtAuth", security_schemes)
        self.assertEqual(security_schemes["jwtAuth"]["type"], "http")
        self.assertEqual(security_schemes["jwtAuth"]["scheme"], "bearer")


class EndpointCoverageTests(TestCase):
    """Verify all API endpoints appear in the OpenAPI schema."""

    def setUp(self):
        generator = SchemaGenerator()
        self.schema = generator.get_schema(request=None, public=True)
        self.paths = self.schema.get("paths", {})

    # ---- Accounts endpoints ----

    def test_register_endpoint(self):
        self.assertIn("/api/register/", self.paths)
        self.assertIn("post", self.paths["/api/register/"])

    def test_login_endpoint(self):
        self.assertIn("/api/login/", self.paths)
        self.assertIn("post", self.paths["/api/login/"])

    def test_logout_endpoint(self):
        self.assertIn("/api/logout/", self.paths)
        self.assertIn("post", self.paths["/api/logout/"])

    def test_token_refresh_endpoint(self):
        self.assertIn("/api/refresh/", self.paths)
        self.assertIn("post", self.paths["/api/refresh/"])

    def test_change_password_endpoint(self):
        self.assertIn("/api/change-password/", self.paths)
        self.assertIn("post", self.paths["/api/change-password/"])

    def test_profile_endpoint(self):
        self.assertIn("/api/profile/{user_id}/", self.paths)
        self.assertIn("get", self.paths["/api/profile/{user_id}/"])

    def test_roles_endpoint(self):
        self.assertIn("/api/roles/", self.paths)
        self.assertIn("get", self.paths["/api/roles/"])
        self.assertIn("post", self.paths["/api/roles/"])

    def test_role_detail_endpoint(self):
        self.assertIn("/api/roles/{role_id}/", self.paths)
        methods = self.paths["/api/roles/{role_id}/"]
        self.assertIn("put", methods)
        self.assertIn("delete", methods)

    def test_assign_role_endpoint(self):
        self.assertIn("/api/assign-role/{user_id}/", self.paths)
        self.assertIn("put", self.paths["/api/assign-role/{user_id}/"])

    def test_permissions_endpoint(self):
        self.assertIn("/api/permissions/", self.paths)
        self.assertIn("get", self.paths["/api/permissions/"])

    # ---- Task endpoints ----

    def test_task_list_create_endpoint(self):
        self.assertIn("/api/tasks/", self.paths)
        self.assertIn("get", self.paths["/api/tasks/"])
        self.assertIn("post", self.paths["/api/tasks/"])

    def test_task_detail_endpoint(self):
        self.assertIn("/api/tasks/{task_id}/", self.paths)
        methods = self.paths["/api/tasks/{task_id}/"]
        self.assertIn("get", methods)
        self.assertIn("patch", methods)
        self.assertIn("delete", methods)

    def test_task_assign_endpoint(self):
        self.assertIn("/api/tasks/{task_id}/assign/", self.paths)
        self.assertIn("post", self.paths["/api/tasks/{task_id}/assign/"])

    def test_task_status_update_endpoint(self):
        self.assertIn("/api/tasks/{task_id}/status/", self.paths)
        self.assertIn("patch", self.paths["/api/tasks/{task_id}/status/"])

    # ---- Meeting endpoints ----

    def test_meeting_create_endpoint(self):
        self.assertIn("/api/tasks/meetings/", self.paths)
        self.assertIn("post", self.paths["/api/tasks/meetings/"])

    def test_meeting_detail_endpoint(self):
        self.assertIn("/api/tasks/meetings/{meeting_id}/", self.paths)
        self.assertIn("get", self.paths["/api/tasks/meetings/{meeting_id}/"])

    def test_meeting_reschedule_endpoint(self):
        self.assertIn("/api/tasks/meetings/{meeting_id}/reschedule/", self.paths)
        self.assertIn("patch", self.paths["/api/tasks/meetings/{meeting_id}/reschedule/"])

    def test_meeting_status_update_endpoint(self):
        self.assertIn("/api/tasks/meetings/{meeting_id}/status/", self.paths)
        self.assertIn("patch", self.paths["/api/tasks/meetings/{meeting_id}/status/"])

    def test_meeting_participant_add_endpoint(self):
        self.assertIn("/api/tasks/meetings/{meeting_id}/participants/", self.paths)
        self.assertIn("post", self.paths["/api/tasks/meetings/{meeting_id}/participants/"])

    def test_meeting_participant_remove_endpoint(self):
        self.assertIn("/api/tasks/meetings/{meeting_id}/participants/{user_id}/", self.paths)
        self.assertIn("delete", self.paths["/api/tasks/meetings/{meeting_id}/participants/{user_id}/"])

    # ---- Reminder endpoints ----

    def test_reminder_create_endpoint(self):
        self.assertIn("/api/tasks/reminders/", self.paths)
        self.assertIn("post", self.paths["/api/tasks/reminders/"])

    def test_reminder_detail_endpoint(self):
        self.assertIn("/api/tasks/reminders/{reminder_id}/", self.paths)
        methods = self.paths["/api/tasks/reminders/{reminder_id}/"]
        self.assertIn("get", methods)
        self.assertIn("patch", methods)
        self.assertIn("delete", methods)

    def test_reminder_status_update_endpoint(self):
        self.assertIn("/api/tasks/reminders/{reminder_id}/status/", self.paths)
        self.assertIn("patch", self.paths["/api/tasks/reminders/{reminder_id}/status/"])

    # ---- FollowUp endpoints ----

    def test_followup_list_create_endpoint(self):
        self.assertIn("/api/followups/", self.paths)
        self.assertIn("get", self.paths["/api/followups/"])
        self.assertIn("post", self.paths["/api/followups/"])

    def test_followup_detail_endpoint(self):
        self.assertIn("/api/followups/{followup_id}/", self.paths)
        methods = self.paths["/api/followups/{followup_id}/"]
        self.assertIn("get", methods)
        self.assertIn("patch", methods)
        self.assertIn("delete", methods)

    def test_followup_note_create_endpoint(self):
        self.assertIn("/api/followups/{followup_id}/notes/", self.paths)
        self.assertIn("post", self.paths["/api/followups/{followup_id}/notes/"])

    # ---- Notification endpoints ----

    def test_notification_list_endpoint(self):
        self.assertIn("/api/followups/notifications/", self.paths)
        self.assertIn("get", self.paths["/api/followups/notifications/"])

    def test_notification_detail_endpoint(self):
        self.assertIn("/api/followups/notifications/{notification_id}/", self.paths)
        methods = self.paths["/api/followups/notifications/{notification_id}/"]
        self.assertIn("get", methods)
        self.assertIn("patch", methods)

    # ---- CRM: Lead Source endpoints ----

    def test_lead_source_list_create_endpoint(self):
        self.assertIn("/api/crm/lead-sources/", self.paths)
        self.assertIn("get", self.paths["/api/crm/lead-sources/"])
        self.assertIn("post", self.paths["/api/crm/lead-sources/"])

    # ---- CRM: Pipeline endpoints ----

    def test_pipeline_list_create_endpoint(self):
        self.assertIn("/api/crm/pipelines/", self.paths)
        self.assertIn("get", self.paths["/api/crm/pipelines/"])
        self.assertIn("post", self.paths["/api/crm/pipelines/"])

    def test_pipeline_stage_list_create_endpoint(self):
        self.assertIn("/api/crm/pipeline-stages/", self.paths)
        self.assertIn("get", self.paths["/api/crm/pipeline-stages/"])
        self.assertIn("post", self.paths["/api/crm/pipeline-stages/"])

    # ---- CRM: Lead endpoints ----

    def test_lead_list_create_endpoint(self):
        self.assertIn("/api/crm/leads/", self.paths)
        self.assertIn("get", self.paths["/api/crm/leads/"])
        self.assertIn("post", self.paths["/api/crm/leads/"])

    def test_lead_detail_endpoint(self):
        self.assertIn("/api/crm/leads/{id}/", self.paths)
        methods = self.paths["/api/crm/leads/{id}/"]
        self.assertIn("get", methods)
        self.assertIn("put", methods)
        self.assertIn("patch", methods)

    def test_lead_assign_endpoint(self):
        self.assertIn("/api/crm/leads/{id}/assign/", self.paths)
        self.assertIn("post", self.paths["/api/crm/leads/{id}/assign/"])

    def test_lead_progress_endpoint(self):
        self.assertIn("/api/crm/leads/{id}/progress/", self.paths)
        self.assertIn("post", self.paths["/api/crm/leads/{id}/progress/"])

    def test_lead_lost_endpoint(self):
        self.assertIn("/api/crm/leads/{id}/lost/", self.paths)
        self.assertIn("post", self.paths["/api/crm/leads/{id}/lost/"])

    def test_lead_reengage_endpoint(self):
        self.assertIn("/api/crm/leads/{id}/reengage/", self.paths)
        self.assertIn("post", self.paths["/api/crm/leads/{id}/reengage/"])

    def test_lead_convert_endpoint(self):
        self.assertIn("/api/crm/leads/{id}/convert/", self.paths)
        self.assertIn("post", self.paths["/api/crm/leads/{id}/convert/"])

    # ---- CRM: Customer endpoints ----

    def test_customer_list_create_endpoint(self):
        self.assertIn("/api/crm/customers/", self.paths)
        self.assertIn("get", self.paths["/api/crm/customers/"])
        self.assertIn("post", self.paths["/api/crm/customers/"])

    def test_customer_detail_endpoint(self):
        self.assertIn("/api/crm/customers/{id}/", self.paths)
        self.assertIn("get", self.paths["/api/crm/customers/{id}/"])

    def test_customer_activities_endpoint(self):
        self.assertIn("/api/crm/customers/{id}/activities/", self.paths)
        self.assertIn("get", self.paths["/api/crm/customers/{id}/activities/"])

    # ---- CRM: Activity endpoints ----

    def test_activity_list_create_endpoint(self):
        self.assertIn("/api/crm/activities/", self.paths)
        self.assertIn("get", self.paths["/api/crm/activities/"])
        self.assertIn("post", self.paths["/api/crm/activities/"])

    # ---- CRM: Audit Log endpoints ----

    def test_audit_log_list_endpoint(self):
        self.assertIn("/api/crm/audit-logs/", self.paths)
        self.assertIn("get", self.paths["/api/crm/audit-logs/"])

    # ---- CRM: Quotation endpoints ----

    def test_quotation_list_create_endpoint(self):
        self.assertIn("/api/crm/quotations/", self.paths)
        self.assertIn("get", self.paths["/api/crm/quotations/"])
        self.assertIn("post", self.paths["/api/crm/quotations/"])

    def test_quotation_detail_endpoint(self):
        self.assertIn("/api/crm/quotations/{id}/", self.paths)
        self.assertIn("get", self.paths["/api/crm/quotations/{id}/"])

    def test_quotation_update_draft_endpoint(self):
        self.assertIn("/api/crm/quotations/{id}/update-draft/", self.paths)
        self.assertIn("patch", self.paths["/api/crm/quotations/{id}/update-draft/"])

    def test_quotation_submit_endpoint(self):
        self.assertIn("/api/crm/quotations/{id}/submit/", self.paths)
        self.assertIn("post", self.paths["/api/crm/quotations/{id}/submit/"])

    def test_quotation_approve_endpoint(self):
        self.assertIn("/api/crm/quotations/{id}/approve/", self.paths)
        self.assertIn("post", self.paths["/api/crm/quotations/{id}/approve/"])

    def test_quotation_reject_approval_endpoint(self):
        self.assertIn("/api/crm/quotations/{id}/reject-approval/", self.paths)
        self.assertIn("post", self.paths["/api/crm/quotations/{id}/reject-approval/"])

    def test_quotation_send_endpoint(self):
        self.assertIn("/api/crm/quotations/{id}/send/", self.paths)
        self.assertIn("post", self.paths["/api/crm/quotations/{id}/send/"])

    def test_quotation_revision_endpoint(self):
        self.assertIn("/api/crm/quotations/{id}/revision/", self.paths)
        self.assertIn("post", self.paths["/api/crm/quotations/{id}/revision/"])

    def test_quotation_accept_endpoint(self):
        self.assertIn("/api/crm/quotations/{id}/accept/", self.paths)
        self.assertIn("post", self.paths["/api/crm/quotations/{id}/accept/"])

    def test_quotation_reject_endpoint(self):
        self.assertIn("/api/crm/quotations/{id}/reject/", self.paths)
        self.assertIn("post", self.paths["/api/crm/quotations/{id}/reject/"])

    def test_quotation_pdf_endpoint(self):
        self.assertIn("/api/crm/quotations/{id}/pdf/", self.paths)
        self.assertIn("get", self.paths["/api/crm/quotations/{id}/pdf/"])

    def test_quotation_send_email_endpoint(self):
        self.assertIn("/api/crm/quotations/{id}/send-email/", self.paths)
        self.assertIn("post", self.paths["/api/crm/quotations/{id}/send-email/"])

    def test_quotation_integration_events_endpoint(self):
        self.assertIn("/api/crm/quotation-events/", self.paths)
        self.assertIn("get", self.paths["/api/crm/quotation-events/"])


class TagTests(TestCase):
    """Verify all expected tags are present in the schema."""

    def setUp(self):
        generator = SchemaGenerator()
        self.schema = generator.get_schema(request=None, public=True)
        self.tags = {t["name"] for t in self.schema.get("tags", [])}

    def test_all_expected_tags_present(self):
        expected_tags = {
            "Accounts",
            "Leads",
            "Customers",
            "Pipelines",
            "Quotations",
            "Tasks",
            "Meetings",
            "Reminders",
            "Follow Ups",
            "Notifications",
            "Audit Logs",
            "Lead Sources",
            "Activities",
        }
        missing = expected_tags - self.tags
        self.assertEqual(missing, set(), f"Missing tags: {missing}")

    def test_each_endpoint_has_at_least_one_tag(self):
        for path, methods in self.schema.get("paths", {}).items():
            for method, details in methods.items():
                if method in ("get", "post", "put", "patch", "delete"):
                    with self.subTest(path=path, method=method):
                        self.assertIn(
                            "tags",
                            details,
                            f"{method.upper()} {path} is missing tags",
                        )
                        self.assertGreater(
                            len(details["tags"]),
                            0,
                            f"{method.upper()} {path} has empty tags",
                        )


class SchemaComponentTests(TestCase):
    """Verify schema components are well-formed."""

    def setUp(self):
        generator = SchemaGenerator()
        self.schema = generator.get_schema(request=None, public=True)
        self.schemas = self.schema.get("components", {}).get("schemas", {})

    def test_key_schemas_exist(self):
        expected_schemas = [
            "Task",
            "PatchedTaskRequest",
            "Meeting",
            "MeetingRequest",
            "MeetingParticipant",
            "Reminder",
            "ReminderRequest",
            "PatchedReminderRequest",
            "Followup",
            "FollowupRequest",
            "PatchedFollowupRequest",
            "FollowUpNote",
            "FollowUpNoteRequest",
            "Notification",
            "PatchedNotificationRequest",
            "Lead",
            "LeadRequest",
            "PatchedLeadRequest",
            "Customer",
            "CustomerRequest",
            "Activity",
            "ActivityRequest",
        ]
        for name in expected_schemas:
            with self.subTest(schema=name):
                self.assertIn(
                    name,
                    self.schemas,
                    f"Schema '{name}' not found in components",
                )

    def test_all_schemas_have_type(self):
        for name, schema in self.schemas.items():
            with self.subTest(schema=name):
                self.assertIn(
                    "type",
                    schema,
                    f"Schema '{name}' is missing 'type'",
                )
