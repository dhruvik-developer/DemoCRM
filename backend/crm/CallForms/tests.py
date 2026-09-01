from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import Role
from Task.models import TaskStatus, TaskPriority, TaskCategory
from CallForms.services import ensure_canonical_task_master_data
from customer_management.models import (
    Lead,
    LeadSource,
    Pipeline,
    PipelineStage,
    QuotationStatus,
)
from customer_management.services import CRMService, QuotationService

from .models import (
    CallTemplate,
    TemplateVersion,
    TemplateField,
    FieldType,
    PipelineStageActivity,
    ActivityType,
    CallAttempt,
    OutcomeChoice,
    FormSubmission,
    ConditionChoice,
)
from .services import (
    create_template_with_initial_version,
    clone_template_version,
    create_stage_activity,
    create_trigger_rule,
    log_call_attempt,
    submit_call_form,
    validate_submission_data,
)

User = get_user_model()


class CallFormsPhase1Tests(TestCase):
    def setUp(self):
        # Seed Task master data
        ensure_canonical_task_master_data()

        # Create test users
        self.manager_role, _ = Role.objects.get_or_create(rolename="Manager")
        self.employee_role, _ = Role.objects.get_or_create(rolename="Employee")

        self.manager = User.objects.create_user(
            username="manager_user",
            email="manager@example.com",
            password="password123",
            phone_number="9999999901",
            role=self.manager_role,
        )
        self.agent = User.objects.create_user(
            username="agent_user",
            email="agent@example.com",
            password="password123",
            phone_number="9999999902",
            role=self.employee_role,
        )

        # Setup Lead and Pipeline dependencies
        self.lead_source = LeadSource.objects.create(
            name="Website Inquiry",
            created_by=self.manager,
        )
        self.pipeline = Pipeline.objects.create(
            name="Sales Pipeline",
            created_by=self.manager,
        )
        self.stage = PipelineStage.objects.create(
            pipeline=self.pipeline,
            name="Demo Stage",
            display_order=1,
        )
        self.lead = Lead.objects.create(
            name="John Doe",
            company_name="Acme Corp",
            email="john@acme.com",
            phone="1234567890",
            source=self.lead_source,
            pipeline=self.pipeline,
            current_stage=self.stage,
            assigned_to=self.agent,
        )

    def test_01_task_master_data_seeded(self):
        """Verify task master data is correctly seeded."""
        self.assertTrue(TaskStatus.objects.filter(status_name="Pending").exists())
        self.assertTrue(TaskStatus.objects.filter(status_name="Completed").exists())
        self.assertTrue(TaskPriority.objects.filter(priority_name="High").exists())
        self.assertTrue(TaskCategory.objects.filter(category_name="Call").exists())

    def test_02_call_template_and_version_creation(self):
        """Verify creating a CallTemplate and TemplateVersion."""
        template = CallTemplate.objects.create(
            name="Demo Feedback Form",
            description="Form for demo feedback",
            created_by=self.manager,
        )
        self.assertEqual(str(template), "Demo Feedback Form")

        version = TemplateVersion.objects.create(
            template=template,
            version_number=1,
            is_primary=True,
            created_by=self.manager,
        )
        self.assertEqual(version.version_label, "v1.0")
        self.assertFalse(version.is_locked)

    def test_03_template_field_creation_and_types(self):
        """Verify creating fields with choices and required flags."""
        template = CallTemplate.objects.create(
            name="Qualification Form",
            created_by=self.manager,
        )
        version = TemplateVersion.objects.create(
            template=template,
            version_number=1,
            created_by=self.manager,
        )

        field_text = TemplateField.objects.create(
            template_version=version,
            field_key="company_size",
            label="Company Size",
            field_type=FieldType.TEXT,
            is_required=True,
            display_order=1,
        )
        field_select = TemplateField.objects.create(
            template_version=version,
            field_key="budget_range",
            label="Budget Range",
            field_type=FieldType.SELECT,
            is_required=False,
            options=["<10k", "10k-50k", ">50k"],
            display_order=2,
        )

        self.assertEqual(version.fields.count(), 2)
        self.assertEqual(field_select.options, ["<10k", "10k-50k", ">50k"])

    def test_04_pipeline_stage_activity_relationship(self):
        """Verify linking PipelineStageActivity to a CallTemplate."""
        template = CallTemplate.objects.create(
            name="Stage Call Form",
            created_by=self.manager,
        )
        activity = PipelineStageActivity.objects.create(
            stage=self.stage,
            name="Initial Demo Call",
            activity_type=ActivityType.CALL,
            call_template=template,
            is_primary=True,
            created_by=self.manager,
        )
        self.assertEqual(activity.stage, self.stage)
        self.assertTrue(activity.is_primary)
        self.assertEqual(activity.call_template, template)

    def test_05_call_attempt_and_form_submission_flow(self):
        """Verify creating a CallAttempt and attaching a FormSubmission."""
        template = CallTemplate.objects.create(
            name="Closing Call Form",
            created_by=self.manager,
        )
        version = TemplateVersion.objects.create(
            template=template,
            version_number=1,
            created_by=self.manager,
        )
        TemplateField.objects.create(
            template_version=version,
            field_key="decision_maker",
            label="Is Decision Maker Present?",
            field_type=FieldType.BOOLEAN,
            is_required=True,
        )

        attempt = CallAttempt.objects.create(
            lead=self.lead,
            stage=self.stage,
            template_version=version,
            attempt_number=1,
            agent=self.agent,
            outcome=OutcomeChoice.CONNECTED,
            is_form_submitted=True,
        )

        submission = FormSubmission.objects.create(
            lead=self.lead,
            call_attempt=attempt,
            template_version=version,
            submitted_by=self.agent,
            data={"decision_maker": True},
            notes="Call went very well",
        )

        self.assertEqual(submission.lead, self.lead)
        self.assertEqual(submission.call_attempt, attempt)
        self.assertEqual(submission.data["decision_maker"], True)

    def test_06_version_immutability_on_submission(self):
        """Verify that a TemplateVersion becomes immutable once used in a FormSubmission."""
        template = CallTemplate.objects.create(
            name="Immutable Test Form",
            created_by=self.manager,
        )
        version = TemplateVersion.objects.create(
            template=template,
            version_number=1,
            created_by=self.manager,
        )
        field = TemplateField.objects.create(
            template_version=version,
            field_key="feedback",
            label="Feedback",
            field_type=FieldType.TEXTAREA,
        )

        # Before submission, version is unlocked
        self.assertFalse(version.is_locked)

        # Create submission
        FormSubmission.objects.create(
            lead=self.lead,
            template_version=version,
            submitted_by=self.agent,
            data={"feedback": "Great demo"},
        )

        # After submission, version is locked
        self.assertTrue(version.is_locked)

        # Attempting clean() on locked version or field should raise ValidationError
        with self.assertRaises(ValidationError):
            version.clean()

        new_field = TemplateField(
            template_version=version,
            field_key="new_key",
            label="New Field",
            field_type=FieldType.TEXT,
        )
        with self.assertRaises(ValidationError):
            new_field.clean()

    def test_07_role_permissions_seeded(self):
        """Verify CallForms permissions are seeded to Manager and Employee roles."""
        manager_perm_names = set(
            self.manager_role.permissions.values_list("codename", flat=True)
        )
        employee_perm_names = set(
            self.employee_role.permissions.values_list("codename", flat=True)
        )

        # Manager should have full management perms for CallForms models
        self.assertIn("add_calltemplate", manager_perm_names)
        self.assertIn("change_calltemplate", manager_perm_names)
        self.assertIn("view_calltemplate", manager_perm_names)
        self.assertIn("add_templateversion", manager_perm_names)
        self.assertIn("add_pipelinestageactivity", manager_perm_names)

        # Employee should have view perms and call attempt / submission add perms
        self.assertIn("view_calltemplate", employee_perm_names)
        self.assertIn("add_callattempt", employee_perm_names)
        self.assertIn("add_formsubmission", employee_perm_names)


class CallFormsPhase2APITests(APITestCase):
    def setUp(self):
        ensure_canonical_task_master_data()

        self.manager_role, _ = Role.objects.get_or_create(rolename="Manager")
        self.employee_role, _ = Role.objects.get_or_create(rolename="Employee")

        self.manager = User.objects.create_user(
            username="manager_api_user",
            email="manager_api@example.com",
            password="password123",
            phone_number="8888888801",
            role=self.manager_role,
        )
        self.agent = User.objects.create_user(
            username="agent_api_user",
            email="agent_api@example.com",
            password="password123",
            phone_number="8888888802",
            role=self.employee_role,
        )

        self.lead_source = LeadSource.objects.create(
            name="API Source",
            created_by=self.manager,
        )
        self.pipeline = Pipeline.objects.create(
            name="API Pipeline",
            created_by=self.manager,
        )
        self.stage = PipelineStage.objects.create(
            pipeline=self.pipeline,
            name="API Stage",
            display_order=1,
        )
        self.lead = Lead.objects.create(
            name="API Lead",
            company_name="API Corp",
            email="lead@api.com",
            phone="1231231234",
            source=self.lead_source,
            pipeline=self.pipeline,
            current_stage=self.stage,
            assigned_to=self.agent,
        )

    def test_01_create_template_api(self):
        """Manager creates a template with initial fields via API."""
        self.client.force_authenticate(user=self.manager)
        payload = {
            "name": "API Discovery Form",
            "description": "Form for discovery call",
            "initial_fields": [
                {
                    "field_key": "customer_budget",
                    "label": "Customer Budget",
                    "field_type": "number",
                    "is_required": True,
                    "display_order": 1,
                },
                {
                    "field_key": "industry",
                    "label": "Industry",
                    "field_type": "select",
                    "options": ["Tech", "Healthcare", "Finance"],
                    "display_order": 2,
                },
            ],
        }
        res = self.client.post("/api/callforms/templates/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["name"], "API Discovery Form")
        self.assertIsNotNone(res.data["primary_version"])
        self.assertEqual(res.data["primary_version"]["version_number"], 1)

    def test_02_version_cloning_and_primary_selection_api(self):
        """Clone version V1 to V2 and set V2 as primary."""
        self.client.force_authenticate(user=self.manager)
        res_create = self.client.post(
            "/api/callforms/templates/",
            {"name": "Version Test Form"},
            format="json",
        )
        template_id = res_create.data["id"]
        v1_id = res_create.data["primary_version"]["id"]

        # Clone V1 to V2
        res_clone = self.client.post(
            f"/api/callforms/versions/{v1_id}/clone/", {}, format="json"
        )
        self.assertEqual(res_clone.status_code, status.HTTP_201_CREATED)
        v2_id = res_clone.data["id"]
        self.assertEqual(res_clone.data["version_number"], 2)
        self.assertTrue(res_clone.data["is_primary"])

        # Switch primary back to V1
        res_primary = self.client.post(
            f"/api/callforms/templates/{template_id}/set-primary/",
            {"version_id": v1_id},
            format="json",
        )
        self.assertEqual(res_primary.status_code, status.HTTP_200_OK)
        self.assertTrue(res_primary.data["is_primary"])

    def test_03_locked_version_mutation_blocked_api(self):
        """Editing locked version via API should return 400 Bad Request."""
        template, version = create_template_with_initial_version(
            name="Locked API Form",
            description="Locked form",
            created_by=self.manager,
        )
        field = TemplateField.objects.create(
            template_version=version,
            field_key="notes",
            label="Notes",
            field_type=FieldType.TEXT,
        )

        # Create submission to lock version
        FormSubmission.objects.create(
            lead=self.lead,
            template_version=version,
            submitted_by=self.agent,
            data={"notes": "Submission notes"},
        )

        self.client.force_authenticate(user=self.manager)

        # Attempting to edit locked version
        res_v = self.client.patch(
            f"/api/callforms/versions/{version.id}/",
            {"version_label": "v1.1-modified"},
            format="json",
        )
        self.assertEqual(res_v.status_code, status.HTTP_400_BAD_REQUEST)

        # Attempting to edit field on locked version
        res_f = self.client.patch(
            f"/api/callforms/fields/{field.id}/",
            {"label": "New Label"},
            format="json",
        )
        self.assertEqual(res_f.status_code, status.HTTP_400_BAD_REQUEST)

    def test_04_field_reordering_api(self):
        """Reordering fields for an unlocked version."""
        template, version = create_template_with_initial_version(
            name="Reorder API Form",
            description="Reorder form",
            created_by=self.manager,
        )
        f1 = TemplateField.objects.create(
            template_version=version,
            field_key="field_one",
            label="Field One",
            display_order=1,
        )
        f2 = TemplateField.objects.create(
            template_version=version,
            field_key="field_two",
            label="Field Two",
            display_order=2,
        )

        self.client.force_authenticate(user=self.manager)
        payload = {
            "template_version_id": str(version.id),
            "orders": [
                {"field_id": str(f1.id), "display_order": 10},
                {"field_id": str(f2.id), "display_order": 5},
            ],
        }
        res = self.client.post("/api/callforms/fields/reorder/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        f1.refresh_from_db()
        f2.refresh_from_db()
        self.assertEqual(f1.display_order, 10)
        self.assertEqual(f2.display_order, 5)

    def test_05_employee_forbidden_from_modifying_templates(self):
        """Employee role user receives 403 Forbidden when creating or editing templates."""
        self.client.force_authenticate(user=self.agent)

        res_post = self.client.post(
            "/api/callforms/templates/", {"name": "Employee Form"}, format="json"
        )
        self.assertEqual(res_post.status_code, status.HTTP_403_FORBIDDEN)


class CallFormsPhase3APITests(APITestCase):
    def setUp(self):
        ensure_canonical_task_master_data()

        self.manager_role, _ = Role.objects.get_or_create(rolename="Manager")
        self.employee_role, _ = Role.objects.get_or_create(rolename="Employee")

        self.manager = User.objects.create_user(
            username="manager_p3",
            email="manager_p3@example.com",
            password="password123",
            phone_number="7777777701",
            role=self.manager_role,
        )
        self.agent = User.objects.create_user(
            username="agent_p3",
            email="agent_p3@example.com",
            password="password123",
            phone_number="7777777702",
            role=self.employee_role,
        )

        self.lead_source = LeadSource.objects.create(
            name="P3 Source",
            created_by=self.manager,
        )
        self.pipeline = Pipeline.objects.create(
            name="P3 Pipeline",
            created_by=self.manager,
        )
        self.stage = PipelineStage.objects.create(
            pipeline=self.pipeline,
            name="Demo Stage",
            display_order=1,
        )
        self.lead = Lead.objects.create(
            name="Phase 3 Lead",
            company_name="P3 Corp",
            email="p3lead@example.com",
            phone="9988776655",
            source=self.lead_source,
            pipeline=self.pipeline,
            current_stage=self.stage,
            assigned_to=self.agent,
        )

        # Create template with fields
        self.template, self.version = create_template_with_initial_version(
            name="P3 Demo Form",
            description="Form for Demo Stage",
            created_by=self.manager,
            initial_fields=[
                {
                    "field_key": "tech_stack",
                    "label": "Tech Stack",
                    "field_type": "text",
                    "is_required": True,
                },
                {
                    "field_key": "user_count",
                    "label": "Expected Users",
                    "field_type": "number",
                    "is_required": False,
                },
            ],
        )

    def test_01_create_stage_activity_and_set_primary_api(self):
        """Manager creates multiple activities for a stage and sets primary."""
        self.client.force_authenticate(user=self.manager)

        # Create activity 1
        res1 = self.client.post(
            "/api/callforms/stage-activities/",
            {
                "stage": str(self.stage.id),
                "name": "Initial Call",
                "activity_type": "CALL",
                "call_template": str(self.template.id),
                "is_primary": True,
            },
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        act1_id = res1.data["id"]
        self.assertTrue(res1.data["is_primary"])

        # Create activity 2 as primary (should unset act1 primary)
        res2 = self.client.post(
            "/api/callforms/stage-activities/",
            {
                "stage": str(self.stage.id),
                "name": "Demo Follow-up",
                "activity_type": "CALL",
                "call_template": str(self.template.id),
                "is_primary": True,
            },
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        act2_id = res2.data["id"]
        self.assertTrue(res2.data["is_primary"])

        # Switch primary back to act1
        res_switch = self.client.post(
            f"/api/callforms/stage-activities/{act1_id}/set-primary/",
            {},
            format="json",
        )
        self.assertEqual(res_switch.status_code, status.HTTP_200_OK)
        self.assertTrue(res_switch.data["is_primary"])

    def test_02_lead_primary_form_resolution_api(self):
        """Agent resolves primary form for a lead's current stage."""
        activity = create_stage_activity(
            stage=self.stage,
            name="Primary Demo Activity",
            call_template=self.template,
            is_primary=True,
            created_by=self.manager,
        )

        self.client.force_authenticate(user=self.agent)
        res = self.client.get(
            f"/api/callforms/stage-activities/lead-primary-form/?lead_id={self.lead.id}"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["lead_id"], str(self.lead.id))
        self.assertEqual(res.data["stage_name"], "Demo Stage")
        self.assertEqual(res.data["activity"]["name"], "Primary Demo Activity")
        self.assertEqual(res.data["call_template"]["name"], "P3 Demo Form")
        self.assertEqual(len(res.data["fields"]), 2)

    def test_03_stage_activities_for_stage_list_api(self):
        """Retrieve all activities configured for a pipeline stage."""
        create_stage_activity(
            stage=self.stage, name="Activity A", created_by=self.manager
        )
        create_stage_activity(
            stage=self.stage, name="Activity B", created_by=self.manager
        )

        self.client.force_authenticate(user=self.agent)
        res = self.client.get(
            f"/api/callforms/stage-activities/for-stage/?stage_id={self.stage.id}"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)


class CallFormsPhase4APITests(APITestCase):
    def setUp(self):
        ensure_canonical_task_master_data()

        self.manager_role, _ = Role.objects.get_or_create(rolename="Manager")
        self.employee_role, _ = Role.objects.get_or_create(rolename="Employee")

        self.manager = User.objects.create_user(
            username="manager_p4",
            email="manager_p4@example.com",
            password="password123",
            phone_number="6666666601",
            role=self.manager_role,
        )
        self.agent = User.objects.create_user(
            username="agent_p4",
            email="agent_p4@example.com",
            password="password123",
            phone_number="6666666602",
            role=self.employee_role,
        )

        self.lead_source = LeadSource.objects.create(
            name="P4 Source",
            created_by=self.manager,
        )
        self.pipeline = Pipeline.objects.create(
            name="P4 Pipeline",
            created_by=self.manager,
        )
        self.stage = PipelineStage.objects.create(
            pipeline=self.pipeline,
            name="P4 Demo Stage",
            display_order=1,
        )
        self.lead = Lead.objects.create(
            name="Phase 4 Lead",
            company_name="P4 Corp",
            email="p4lead@example.com",
            phone="1122334455",
            source=self.lead_source,
            pipeline=self.pipeline,
            current_stage=self.stage,
            assigned_to=self.agent,
        )

        self.template, self.version = create_template_with_initial_version(
            name="P4 Call Form",
            description="Form for Phase 4 workflow",
            created_by=self.manager,
            initial_fields=[
                {
                    "field_key": "company_name",
                    "label": "Company Name",
                    "field_type": "text",
                    "is_required": True,
                },
                {
                    "field_key": "budget",
                    "label": "Budget",
                    "field_type": "number",
                    "is_required": True,
                },
                {
                    "field_key": "priority_level",
                    "label": "Priority Level",
                    "field_type": "select",
                    "options": ["Low", "High"],
                    "is_required": False,
                },
            ],
        )

    def test_01_log_call_attempts_and_sequential_numbering_api(self):
        """Log call attempt #1 and #2 via API and verify auto attempt_numbering."""
        self.client.force_authenticate(user=self.agent)

        res1 = self.client.post(
            "/api/callforms/attempts/",
            {
                "lead_id": str(self.lead.id),
                "outcome": "NO_ANSWER",
                "notes": "Attempt #1 - Customer didn't pick up",
            },
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res1.data["attempt_number"], 1)
        self.assertEqual(res1.data["outcome"], "NO_ANSWER")
        self.assertFalse(res1.data["suggest_mark_lost"])

        res2 = self.client.post(
            "/api/callforms/attempts/",
            {
                "lead_id": str(self.lead.id),
                "outcome": "BUSY",
                "notes": "Attempt #2 - Line busy",
            },
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res2.data["attempt_number"], 2)
        self.assertEqual(res2.data["outcome"], "BUSY")

    def test_02_form_submission_validation_missing_required_field_api(self):
        """Submitting form missing required field returns 400 Bad Request."""
        self.client.force_authenticate(user=self.agent)

        payload = {
            "lead_id": str(self.lead.id),
            "template_version_id": str(self.version.id),
            "data": {
                "company_name": "P4 Corp",
                # 'budget' missing
            },
        }
        res = self.client.post("/api/callforms/submissions/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("budget", str(res.data))

    def test_03_form_submission_invalid_select_option_api(self):
        """Submitting invalid select option choice returns 400 Bad Request."""
        self.client.force_authenticate(user=self.agent)

        payload = {
            "lead_id": str(self.lead.id),
            "template_version_id": str(self.version.id),
            "data": {
                "company_name": "P4 Corp",
                "budget": 50000,
                "priority_level": "InvalidChoice",
            },
        }
        res = self.client.post("/api/callforms/submissions/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("priority_level", str(res.data))

    def test_04_successful_form_submission_and_attempt_completion_api(self):
        """Valid form submission creates submission, marks CallAttempt completed, and locks version."""
        attempt = CallAttempt.objects.create(
            lead=self.lead,
            attempt_number=1,
            agent=self.agent,
            outcome="CONNECTED",
        )

        self.client.force_authenticate(user=self.agent)
        payload = {
            "lead_id": str(self.lead.id),
            "template_version_id": str(self.version.id),
            "call_attempt_id": str(attempt.id),
            "data": {
                "company_name": "P4 Corp",
                "budget": 100000,
                "priority_level": "High",
            },
            "notes": "Completed call form",
        }
        res = self.client.post("/api/callforms/submissions/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["data"]["company_name"], "P4 Corp")

        # Verify CallAttempt updated
        attempt.refresh_from_db()
        self.assertTrue(attempt.is_form_submitted)
        self.assertEqual(attempt.outcome, "COMPLETED")

        # Verify TemplateVersion is now locked
        self.version.refresh_from_db()
        self.assertTrue(self.version.is_locked)

    def test_05_failed_attempt_threshold_suggests_mark_lost_api(self):
        """Reaching max failed attempt threshold returns suggest_mark_lost: true."""
        self.client.force_authenticate(user=self.agent)

        # Log 4 failed attempts
        for i in range(1, 5):
            CallAttempt.objects.create(
                lead=self.lead,
                attempt_number=i,
                agent=self.agent,
                outcome="NO_ANSWER",
            )

        # Log 5th failed attempt via API
        res = self.client.post(
            "/api/callforms/attempts/",
            {
                "lead_id": str(self.lead.id),
                "outcome": "NO_ANSWER",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["attempt_number"], 5)
        self.assertTrue(res.data["suggest_mark_lost"])
        # The real outcome is preserved; only the suggestion flag is set.
        self.assertEqual(res.data["outcome"], "NO_ANSWER")


class CallFormsPhase5APITests(APITestCase):
    def setUp(self):
        ensure_canonical_task_master_data()

        self.manager_role, _ = Role.objects.get_or_create(rolename="Manager")
        self.employee_role, _ = Role.objects.get_or_create(rolename="Employee")

        self.manager = User.objects.create_user(
            username="manager_p5",
            email="manager_p5@example.com",
            password="password123",
            phone_number="5555555501",
            role=self.manager_role,
        )
        self.agent = User.objects.create_user(
            username="agent_p5",
            email="agent_p5@example.com",
            password="password123",
            phone_number="5555555502",
            role=self.employee_role,
        )

        self.lead_source = LeadSource.objects.create(
            name="P5 Source",
            created_by=self.manager,
        )
        self.pipeline = Pipeline.objects.create(
            name="P5 Pipeline",
            created_by=self.manager,
        )
        self.stage = PipelineStage.objects.create(
            pipeline=self.pipeline,
            name="P5 Demo Stage",
            display_order=1,
        )
        self.lead = Lead.objects.create(
            name="Phase 5 Lead",
            company_name="P5 Corp",
            email="p5lead@example.com",
            phone="1122334466",
            source=self.lead_source,
            pipeline=self.pipeline,
            current_stage=self.stage,
            assigned_to=self.agent,
        )

        self.template, self.version = create_template_with_initial_version(
            name="P5 Trigger Form",
            description="Form for Phase 5 automation testing",
            created_by=self.manager,
            initial_fields=[
                {
                    "field_key": "follow_up_required",
                    "label": "Follow Up Required?",
                    "field_type": "boolean",
                    "is_required": True,
                },
                {
                    "field_key": "notes",
                    "label": "Notes",
                    "field_type": "text",
                    "is_required": False,
                },
            ],
        )

    def test_01_create_task_trigger_rule_api(self):
        """Manager configures a TaskTriggerRule via API."""
        self.client.force_authenticate(user=self.manager)

        payload = {
            "template_version": str(self.version.id),
            "name": "Auto Follow-up Task Rule",
            "trigger_condition": "FOLLOW_UP_REQUIRED",
            "task_title_template": "Automated Call Follow-up with {lead_name}",
            "due_days_offset": 2,
            "assignee_rule": "CONDUCTING_AGENT",
            "create_reminder": True,
            "reminder_minutes_before": 60,
        }
        res = self.client.post("/api/callforms/trigger-rules/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["name"], "Auto Follow-up Task Rule")

    def test_02_submission_triggers_task_creation(self):
        """Submitting a call form matching trigger rule automatically creates Task and Reminder."""
        from Task.models import Task, Reminder

        create_trigger_rule(
            template_version=self.version,
            name="Rule 1",
            trigger_condition="FOLLOW_UP_REQUIRED",
            task_title_template="Follow-up: {lead_name}",
            due_days_offset=1,
            assignee_rule="CONDUCTING_AGENT",
            create_reminder=True,
        )

        self.client.force_authenticate(user=self.agent)
        payload = {
            "lead_id": str(self.lead.id),
            "template_version_id": str(self.version.id),
            "data": {
                "follow_up_required": True,
                "notes": "Customer requested callback",
            },
        }
        res = self.client.post("/api/callforms/submissions/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Verify automated Task creation
        task = Task.objects.filter(lead=self.lead).first()
        self.assertIsNotNone(task)
        self.assertEqual(task.task_title, "Follow-up: Phase 5 Lead")
        self.assertEqual(task.assigned_to, self.agent)

        # Verify Reminder creation
        reminder = Reminder.objects.filter(task_id=task).first()
        self.assertIsNotNone(reminder)
        self.assertEqual(reminder.reminder_for, self.agent)

    def test_03_lead_owner_assignee_rule(self):
        """Verify LEAD_OWNER assignee rule assigns created Task to lead.assigned_to user."""
        from Task.models import Task

        owner_user = User.objects.create_user(
            username="owner_user",
            email="owner@example.com",
            password="password123",
            phone_number="5555555503",
            role=self.employee_role,
        )
        self.lead.assigned_to = owner_user
        self.lead.save()

        create_trigger_rule(
            template_version=self.version,
            name="Rule Owner",
            trigger_condition="ALWAYS",
            task_title_template="Task for Owner: {lead_name}",
            assignee_rule="LEAD_OWNER",
        )

        self.client.force_authenticate(user=self.agent)
        payload = {
            "lead_id": str(self.lead.id),
            "template_version_id": str(self.version.id),
            "data": {
                "follow_up_required": False,
            },
        }
        res = self.client.post("/api/callforms/submissions/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        task = Task.objects.filter(lead=self.lead).first()
        self.assertEqual(task.assigned_to, owner_user)


class CallFormsPhase6APITests(APITestCase):
    def setUp(self):
        ensure_canonical_task_master_data()

        self.manager_role, _ = Role.objects.get_or_create(rolename="Manager")
        self.employee_role, _ = Role.objects.get_or_create(rolename="Employee")

        self.manager = User.objects.create_user(
            username="manager_p6",
            email="manager_p6@example.com",
            password="password123",
            phone_number="7777777701",
            role=self.manager_role,
        )
        self.agent = User.objects.create_user(
            username="agent_p6",
            email="agent_p6@example.com",
            password="password123",
            phone_number="7777777702",
            role=self.employee_role,
        )

        self.lead_source = LeadSource.objects.create(
            name="P6 Source",
            created_by=self.manager,
        )
        self.pipeline = Pipeline.objects.create(
            name="P6 Pipeline",
            created_by=self.manager,
        )
        self.stage = PipelineStage.objects.create(
            pipeline=self.pipeline,
            name="P6 Demo Stage",
            display_order=1,
        )
        self.lead = Lead.objects.create(
            name="Phase 6 Lead",
            company_name="P6 Corp",
            email="p6lead@example.com",
            phone="1122334477",
            source=self.lead_source,
            pipeline=self.pipeline,
            current_stage=self.stage,
            assigned_to=self.agent,
        )

        self.template, self.version = create_template_with_initial_version(
            name="P6 Dynamic Reporting Form",
            description="Form for Phase 6 ad-hoc & reporting test",
            created_by=self.manager,
            initial_fields=[
                {
                    "field_key": "customer_interest",
                    "label": "Interest Level",
                    "field_type": "select",
                    "options": ["High", "Medium", "Low"],
                    "is_required": True,
                },
                {
                    "field_key": "budget_amount",
                    "label": "Budget",
                    "field_type": "number",
                    "is_required": False,
                },
                {
                    "field_key": "decision_maker",
                    "label": "Decision Maker?",
                    "field_type": "boolean",
                    "is_required": False,
                },
            ],
        )

    def test_01_adhoc_fields_submission_and_extraction(self):
        """Submit form with defined fields AND extra ad-hoc un-schematized keys."""
        self.client.force_authenticate(user=self.agent)

        payload = {
            "lead_id": str(self.lead.id),
            "template_version_id": str(self.version.id),
            "data": {
                "customer_interest": "High",
                "budget_amount": 50000,
                "decision_maker": True,
                "competitor_name": "Acme Corp",
                "custom_deal_notes": "Urgent timeline requested",
            },
        }
        res = self.client.post("/api/callforms/submissions/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["data"]["competitor_name"], "Acme Corp")
        self.assertIn("competitor_name", res.data["adhoc_fields"])
        self.assertIn("custom_deal_notes", res.data["adhoc_fields"])
        self.assertNotIn("customer_interest", res.data["adhoc_fields"])

    def test_02_json_field_query_filtering(self):
        """Filter submissions using field_key and field_value query parameters."""
        self.client.force_authenticate(user=self.agent)

        submit_call_form(
            self.lead,
            self.agent,
            self.version,
            {"customer_interest": "High", "budget_amount": 10000},
        )
        submit_call_form(
            self.lead,
            self.agent,
            self.version,
            {"customer_interest": "Low", "budget_amount": 2000},
        )

        res = self.client.get(
            "/api/callforms/submissions/?field_key=customer_interest&field_value=High"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["data"]["customer_interest"], "High")

    def test_03_template_version_analytics_api(self):
        """Query analytics endpoint for aggregated submission response distributions."""
        self.client.force_authenticate(user=self.manager)

        submit_call_form(
            self.lead,
            self.agent,
            self.version,
            {
                "customer_interest": "High",
                "budget_amount": 10000,
                "decision_maker": True,
            },
        )
        submit_call_form(
            self.lead,
            self.agent,
            self.version,
            {
                "customer_interest": "High",
                "budget_amount": 20000,
                "decision_maker": False,
            },
        )
        submit_call_form(
            self.lead,
            self.agent,
            self.version,
            {
                "customer_interest": "Low",
                "budget_amount": 5000,
                "adhoc_promo": "VIP2026",
            },
        )

        res = self.client.get(
            f"/api/callforms/submissions/analytics/?template_version_id={self.version.id}"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_submissions"], 3)

        # Check SELECT distribution
        interest_stats = res.data["fields_analytics"]["customer_interest"]
        self.assertEqual(interest_stats["distribution"]["High"], 2)
        self.assertEqual(interest_stats["distribution"]["Low"], 1)

        # Check NUMBER stats
        budget_stats = res.data["fields_analytics"]["budget_amount"]["numeric_stats"]
        self.assertEqual(budget_stats["min"], 5000)
        self.assertEqual(budget_stats["max"], 20000)
        self.assertEqual(budget_stats["avg"], 11666.67)

        # Check adhoc key count
        self.assertEqual(res.data["adhoc_key_counts"]["adhoc_promo"], 1)

    def test_04_lead_timeline_activity_feed_api(self):
        """Query lead timeline activity feed consolidating attempts and submissions."""
        self.client.force_authenticate(user=self.agent)

        log_call_attempt(self.lead, self.agent, outcome="NO_ANSWER", notes="Attempt 1")
        log_call_attempt(self.lead, self.agent, outcome="CONNECTED", notes="Attempt 2")
        submit_call_form(
            self.lead, self.agent, self.version, {"customer_interest": "High"}
        )

        res = self.client.get(
            f"/api/callforms/submissions/lead-timeline/?lead_id={self.lead.id}"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_events"], 3)

        # Verify chronological order (most recent first)
        timeline = res.data["timeline"]
        self.assertEqual(timeline[0]["entry_type"], "FORM_SUBMISSION")
        self.assertEqual(timeline[1]["entry_type"], "CALL_ATTEMPT")
        self.assertEqual(timeline[2]["entry_type"], "CALL_ATTEMPT")


# ==============================================================================
# SECTION 27 MANDATED WORKFLOW SCENARIO TESTS (SCENARIOS 1 - 10)
# ==============================================================================


class ScenarioWorkflowTests(APITestCase):
    """Rigorous tests covering all 10 end-to-end workflow scenarios mandated by Section 27 of the approved spec."""

    def setUp(self):
        ensure_canonical_task_master_data()

        self.manager_role, _ = Role.objects.get_or_create(rolename="Manager")
        self.employee_role, _ = Role.objects.get_or_create(rolename="Employee")

        self.user = User.objects.create_user(
            username="user_scenario",
            email="user_scenario@example.com",
            password="password123",
            phone_number="7777777701",
            role=self.manager_role,
        )
        self.manager = self.user
        self.agent = User.objects.create_user(
            username="agent_scenario",
            email="agent_scenario@example.com",
            password="password123",
            phone_number="7777777702",
            role=self.employee_role,
        )
        self.role = self.employee_role

        self.lead_source = LeadSource.objects.create(
            name="Scenario Source", created_by=self.manager
        )
        self.pipeline = Pipeline.objects.create(
            name="Scenario Pipeline", created_by=self.manager
        )
        self.stage = PipelineStage.objects.create(
            pipeline=self.pipeline, name="Discovery", display_order=1
        )
        self.lead = Lead.objects.create(
            name="Scenario Lead",
            company_name="Scenario Corp",
            email="lead@scenario.com",
            phone="1234567890",
            source=self.lead_source,
            pipeline=self.pipeline,
            current_stage=self.stage,
            assigned_to=self.agent,
        )

        template, version = create_template_with_initial_version(
            name="Scenario Call Form",
            description="Form for scenario tests",
            created_by=self.manager,
            initial_fields=[
                {
                    "field_key": "customer_interest",
                    "label": "Customer Interest",
                    "field_type": FieldType.SELECT,
                    "is_required": True,
                    "options": ["High", "Medium", "Low"],
                },
                {
                    "field_key": "budget_amount",
                    "label": "Budget Amount",
                    "field_type": FieldType.NUMBER,
                    "is_required": False,
                },
            ],
        )
        self.template = template
        self.version = version

        self.client.force_authenticate(user=self.agent)

    def test_scenario_01_no_answer_followup_and_second_attempt(self):
        """Scenario 1: New lead -> 1st call no answer -> note -> follow-up -> 2nd attempt."""
        # 1st Attempt: No answer with note
        att1, _ = log_call_attempt(
            self.lead,
            self.agent,
            outcome=OutcomeChoice.NO_ANSWER,
            notes="Lead did not pick up call 1.",
        )
        self.assertEqual(att1.attempt_number, 1)
        self.assertEqual(att1.outcome, OutcomeChoice.NO_ANSWER)

        # 2nd Attempt: Follow-up call
        att2, _ = log_call_attempt(
            self.lead,
            self.agent,
            outcome=OutcomeChoice.CALLBACK,
            notes="Call 2: Scheduled callback.",
        )
        self.assertEqual(att2.attempt_number, 2)
        self.assertEqual(att2.outcome, OutcomeChoice.CALLBACK)
        self.assertEqual(self.lead.call_attempts.count(), 2)

    def test_scenario_02_connected_call_submission_interested_followup_task(self):
        """Scenario 2: Lead -> connected call -> form submission -> interested -> follow-up task auto-created."""
        # Add trigger rule
        create_trigger_rule(
            template_version=self.version,
            name="Interested Followup Task",
            trigger_condition=ConditionChoice.ALWAYS,
            task_title_template="Follow up with {lead_name}",
        )

        att, _ = log_call_attempt(
            self.lead, self.agent, outcome=OutcomeChoice.CONNECTED
        )
        sub = submit_call_form(
            self.lead,
            self.agent,
            self.version,
            form_data={"customer_interest": "High", "budget_amount": 50000},
            call_attempt_or_id=att,
            notes="Customer interested in enterprise plan.",
        )

        self.assertTrue(att.is_form_submitted)
        self.assertEqual(sub.lead, self.lead)

        # Verify task created and linked to submission
        from Task.models import Task

        task = Task.objects.filter(form_submission=sub).first()
        self.assertIsNotNone(task)
        self.assertEqual(task.lead, self.lead)
        self.assertEqual(task.form_submission, sub)
        self.assertEqual(task.assigned_to, self.agent)

    def test_scenario_03_connected_call_not_interested_lead_lost(self):
        """Scenario 3: Lead -> connected call -> not interested -> Lost workflow."""
        att, _ = log_call_attempt(
            self.lead, self.agent, outcome=OutcomeChoice.CONNECTED
        )
        submit_call_form(
            self.lead,
            self.agent,
            self.version,
            form_data={"customer_interest": "Low"},
            call_attempt_or_id=att,
            notes="Lead not interested in product.",
        )

        # Mark lead lost using CRMService
        updated_lead = CRMService.mark_lead_lost(
            user=self.agent,
            lead=self.lead,
            lost_reason="Customer expressed no interest during discovery call.",
        )
        self.assertEqual(updated_lead.status, Lead.Status.LOST)
        self.assertEqual(
            updated_lead.lost_reason,
            "Customer expressed no interest during discovery call.",
        )

    def test_scenario_04_repeated_no_answer_threshold_lost_suggestion_and_confirm(self):
        """Scenario 4: Lead -> repeated no-answer -> threshold -> Lost suggestion -> manager confirms."""
        # Log 5 consecutive failed attempts
        for i in range(1, 6):
            att, _ = log_call_attempt(
                self.lead, self.agent, outcome=OutcomeChoice.NO_ANSWER
            )

        # 5th attempt suggests lost without overwriting the real outcome
        self.assertEqual(att.outcome, OutcomeChoice.NO_ANSWER)
        self.assertTrue(att.suggest_mark_lost)

        # Manager confirms lost
        updated_lead = CRMService.mark_lead_lost(
            user=self.manager,
            lead=self.lead,
            lost_reason="Unresponsive after 5 call attempts",
        )
        self.assertEqual(updated_lead.status, Lead.Status.LOST)

    def test_scenario_05_demo_quotation_discussion_negotiation_accepted_customer(self):
        """Scenario 5: Lead -> Demo -> Quotation -> Quotation Discussion -> Accepted -> Customer."""
        # 1. Create Quotation
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[
                {"description": "Enterprise Plan", "quantity": 1, "unit_price": 50000}
            ],
        )

        # 2. Quotation Discussion Call
        att, _ = log_call_attempt(
            self.lead, self.agent, outcome=OutcomeChoice.CONNECTED
        )
        submit_call_form(
            self.lead,
            self.agent,
            self.version,
            form_data={"customer_interest": "High"},
            call_attempt_or_id=att,
        )

        # 3. Accept Quotation and Convert Lead
        q.current_version.status = QuotationStatus.ACCEPTED
        q.current_version.save(update_fields=["status"])
        q.status = QuotationStatus.ACCEPTED
        q.save(update_fields=["status"])

        customer = CRMService.convert_lead(
            user=self.user,
            lead=self.lead,
            name=self.lead.name,
            email=self.lead.email or "client@example.com",
            phone=self.lead.phone or "9998887776",
        )
        self.assertIsNotNone(customer)
        self.assertEqual(customer.name, self.lead.name)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.CONVERTED)

    def test_scenario_06_agent_handles_call_manager_reassigns_task(self):
        """Scenario 6: Agent handles call -> task created -> manager reassigns to another agent."""
        create_trigger_rule(template_version=self.version, name="Reassign Test Rule")
        att, _ = log_call_attempt(
            self.lead, self.agent, outcome=OutcomeChoice.CONNECTED
        )
        sub = submit_call_form(
            self.lead, self.agent, self.version, {"customer_interest": "High"}, att
        )

        from Task.models import Task

        task = Task.objects.filter(form_submission=sub).first()
        self.assertEqual(task.assigned_to, self.agent)

        # Manager reassigns task to second agent
        other_agent = User.objects.create_user(
            username="agent2", email="agent2@example.com", role=self.role
        )
        task.assigned_to = other_agent
        task.save(update_fields=["assigned_to"])

        task.refresh_from_db()
        self.assertEqual(task.assigned_to, other_agent)

    def test_scenario_07_manager_creates_form_required_field_validation_failure(self):
        """Scenario 7: Manager creates form -> marks required field -> agent submits missing field -> validation fails."""
        # Required field already present: customer_interest
        with self.assertRaises(ValidationError) as ctx:
            validate_submission_data(
                self.version, {"budget_amount": 10000}
            )  # Missing required customer_interest
        self.assertIn("customer_interest", str(ctx.exception))

    def test_scenario_08_locked_version_mutation_rejected(self):
        """Scenario 8: Form version used by submission -> attempt to mutate historical version -> rejected."""
        submit_call_form(
            self.lead, self.agent, self.version, {"customer_interest": "High"}
        )
        self.assertTrue(self.version.is_locked)

        with self.assertRaises(ValidationError):
            TemplateField.objects.create(
                template_version=self.version,
                field_key="new_field",
                label="New Field",
                field_type=FieldType.TEXT,
            )

    def test_scenario_09_manager_creates_new_version_primary_old_submissions_intact(
        self,
    ):
        """Scenario 9: Manager creates new version -> sets primary -> new calls use new version -> old submissions unchanged."""
        sub1 = submit_call_form(
            self.lead, self.agent, self.version, {"customer_interest": "High"}
        )

        v2 = clone_template_version(
            self.version, created_by=self.manager, set_primary=True
        )
        self.assertEqual(v2.version_number, 2)

        sub2 = submit_call_form(
            self.lead, self.agent, v2, {"customer_interest": "Medium"}
        )

        self.assertEqual(sub1.template_version, self.version)
        self.assertEqual(sub2.template_version, v2)

    def test_scenario_10_agent_proposes_adhoc_field_manager_approves(self):
        """Scenario 10: Agent proposes new field -> manager approves -> field becomes available."""
        from CallForms.services import propose_adhoc_field, review_adhoc_field
        from CallForms.models import ProposalStatus

        # Agent proposes field
        prop = propose_adhoc_field(
            user=self.agent,
            template_version=self.version,
            field_key="contract_term",
            label="Contract Term (Months)",
            field_type=FieldType.NUMBER,
        )
        self.assertEqual(prop.status, ProposalStatus.PENDING)

        # Manager approves proposal
        approved_prop = review_adhoc_field(
            user=self.manager,
            proposal=prop,
            status=ProposalStatus.APPROVED,
        )
        self.assertEqual(approved_prop.status, ProposalStatus.APPROVED)

        # Field exists on draft template version
        field_exists = self.version.fields.filter(field_key="contract_term").exists()
        self.assertTrue(field_exists)

    def test_indexed_submission_values_indexing(self):
        """FormSubmission automatically indexes dynamic text, number, date, and boolean fields."""
        sub = submit_call_form(
            self.lead,
            self.agent,
            self.version,
            {
                "customer_interest": "High",
                "budget_amount": 75000.50,
                "decision_maker": True,
                "followup_date": "2026-09-15",
            },
        )

        from CallForms.models import IndexedSubmissionValue

        indexed_rows = IndexedSubmissionValue.objects.filter(submission=sub)
        self.assertEqual(indexed_rows.count(), 4)

        interest_row = indexed_rows.get(field_key="customer_interest")
        self.assertEqual(interest_row.value_text, "High")

        budget_row = indexed_rows.get(field_key="budget_amount")
        self.assertEqual(float(budget_row.value_number), 75000.50)

        dm_row = indexed_rows.get(field_key="decision_maker")
        self.assertTrue(dm_row.value_boolean)

        date_row = indexed_rows.get(field_key="followup_date")
        self.assertEqual(date_row.value_date.isoformat(), "2026-09-15")


class SubmissionSideEffectsTests(APITestCase):
    """
    Verifies the two submission side effects:
    1. Basic-information answers sync into blank Lead fields
       (fill-if-blank: existing identity data is never overwritten).
    2. An explicit follow_up_date in the form data overrides the trigger
       rule's day offset for the created Task/FollowUp dates.
    """

    def setUp(self):
        ensure_canonical_task_master_data()

        self.employee_role, _ = Role.objects.get_or_create(rolename="Employee")
        self.agent = User.objects.create_user(
            username="sync_agent",
            email="sync_agent@example.com",
            password="password123",
            phone_number="9999998801",
            role=self.employee_role,
        )

        self.lead_source = LeadSource.objects.create(
            name="Sync Source", created_by=self.agent
        )
        self.pipeline = Pipeline.objects.create(
            name="Sync Pipeline", created_by=self.agent
        )
        self.stage = PipelineStage.objects.create(
            pipeline=self.pipeline, name="Call 1", display_order=1
        )
        # Lead with BLANK email/phone so fill-if-blank kicks in.
        self.lead = Lead.objects.create(
            name="Blank Contact Lead",
            source=self.lead_source,
            pipeline=self.pipeline,
            current_stage=self.stage,
            assigned_to=self.agent,
        )
        self.client.force_authenticate(user=self.agent)

        self.template, self.version = create_template_with_initial_version(
            name="Basic Information Form",
            description="Call 1 capture",
            created_by=self.agent,
            initial_fields=[
                {"field_key": "name", "label": "Name", "field_type": FieldType.TEXT},
                {"field_key": "email", "label": "Email", "field_type": FieldType.TEXT},
                {"field_key": "phone", "label": "Phone", "field_type": FieldType.TEXT},
                {
                    "field_key": "company_name",
                    "label": "Company",
                    "field_type": FieldType.TEXT,
                },
                {
                    "field_key": "follow_up_required",
                    "label": "Follow-up required?",
                    "field_type": FieldType.BOOLEAN,
                },
                {
                    "field_key": "follow_up_date",
                    "label": "Follow-up date",
                    "field_type": FieldType.DATE,
                },
            ],
        )
        create_trigger_rule(
            template_version=self.version,
            name="Follow-up after call",
            trigger_condition=ConditionChoice.FOLLOW_UP_REQUIRED,
            due_days_offset=3,  # must be overridden by explicit form date
        )

    def test_submission_syncs_blank_lead_fields(self):
        submit_call_form(
            lead_or_id=self.lead,
            agent=self.agent,
            template_version_or_id=self.version,
            form_data={
                "name": "Ravi Kumar",
                "email": "ravi@newlead.com",
                "phone": "9876500001",
                "company_name": "Kumar Traders",
                "follow_up_required": True,
                "follow_up_date": "2026-09-01",
            },
        )
        self.lead.refresh_from_db()
        # Existing identity stays; blanks get filled.
        self.assertEqual(self.lead.name, "Blank Contact Lead")
        self.assertEqual(self.lead.email, "ravi@newlead.com")
        self.assertEqual(self.lead.phone, "9876500001")
        self.assertEqual(self.lead.company_name, "Kumar Traders")

    def test_submission_does_not_overwrite_existing_lead_identity(self):
        self.lead.email = "locked@original.com"
        self.lead.save(update_fields=["email"])

        submit_call_form(
            lead_or_id=self.lead,
            agent=self.agent,
            template_version_or_id=self.version,
            form_data={
                "name": "Someone Else",
                "email": "hijack@evil.com",
                "follow_up_required": False,
            },
        )
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.email, "locked@original.com")

    def test_explicit_follow_up_date_overrides_rule_offset(self):
        from Task.models import Task
        from FollowUp.models import Followup

        submit_call_form(
            lead_or_id=self.lead,
            agent=self.agent,
            template_version_or_id=self.version,
            form_data={
                "name": "Dated Lead",
                "follow_up_required": True,
                "follow_up_date": "2099-05-20",
            },
        )
        task = Task.objects.filter(form_submission__isnull=False).latest("task_id")
        self.assertEqual(task.due_date.date().isoformat(), "2099-05-20")

        followup = Followup.objects.filter(task_id=task).latest("followup_id")
        self.assertEqual(followup.followup_date.date().isoformat(), "2099-05-20")

    def test_missing_follow_up_date_uses_default_offset(self):
        from Task.models import Task

        before = timezone.now()
        submit_call_form(
            lead_or_id=self.lead,
            agent=self.agent,
            template_version_or_id=self.version,
            form_data={
                "name": "Default Date Lead",
                "follow_up_required": True,
            },
        )
        task = Task.objects.filter(
            lead=self.lead, form_submission__isnull=False
        ).latest("task_id")
        expected_low = before + timezone.timedelta(days=3)
        self.assertTrue(
            expected_low <= task.due_date <= timezone.now() + timezone.timedelta(days=3)
        )
