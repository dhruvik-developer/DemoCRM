from decimal import Decimal
from unittest import mock
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from customer_management.models import (
    Activity,
    AuditLog,
    Customer,
    Lead,
    LeadSource,
    Pipeline,
    PipelineStage,
    Quotation,
    QuotationApproval,
    QuotationIntegrationEvent,
    QuotationLineItem,
    QuotationStatus,
    QuotationVersion,
)
from customer_management.services import CRMService, QuotationService

User = get_user_model()


# ==============================================================================
# BASE TEST CASE
# ==============================================================================


class CRMBaseTestCase(TestCase):
    """Shared setUp for all CRM tests: roles, users, sources, pipelines, stages."""

    def setUp(self):
        # --- Role & Permissions ---
        self.role = Role.objects.create(rolename="Manager")
        all_perms = Permission.objects.filter(
            codename__in=[
                "view_leadsource",
                "manage_lead_source",
                "view_pipeline",
                "manage_pipeline",
                "view_pipelinestage",
                "manage_pipeline_stage",
                "view_lead",
                "add_lead",
                "change_lead",
                "delete_lead",
                "assign_lead",
                "progress_lead",
                "mark_lead_lost",
                "reengage_lead",
                "convert_lead",
                "view_customer",
                "add_customer",
                "view_activity",
                "add_activity",
                "view_auditlog",
                "submit_quotation",
                "approve_quotation",
                "send_quotation",
                "accept_quotation",
                "reject_quotation",
                "request_quotation_revision",
                "add_quotation",
                "change_quotation",
                "view_quotation",
                "delete_quotation",
                "generate_quotation_pdf",
            ]
        )
        self.role.permissions.set(all_perms)

        # --- Users ---
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="Password123!",
            phone_number="1234567890",
            role=self.role,
        )
        self.inactive_user = User.objects.create_user(
            username="inactiveuser",
            email="inactive@example.com",
            password="Password123!",
            phone_number="0987654321",
            is_active=False,
        )

        # --- API Client (authenticated as self.user) ---
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # --- Lead Sources ---
        self.source = CRMService.create_lead_source(
            user=self.user,
            name="Web Search",
            description="Organic search",
        )
        self.inactive_source = LeadSource.objects.create(
            name="Inactive Source",
            created_by=self.user,
            is_active=False,
        )

        # --- Pipelines ---
        self.pipeline = CRMService.create_pipeline(
            user=self.user,
            name="Sales Pipeline",
        )
        self.pipeline2 = CRMService.create_pipeline(
            user=self.user,
            name="Second Pipeline",
        )
        self.inactive_pipeline = Pipeline.objects.create(
            name="Inactive Pipeline",
            created_by=self.user,
            is_active=False,
        )

        # --- Pipeline Stages ---
        self.stage1 = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=self.pipeline,
            name="Stage 1",
            display_order=1,
        )
        self.stage2 = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=self.pipeline,
            name="Stage 2",
            display_order=2,
        )
        self.stage2_p2 = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=self.pipeline2,
            name="Pipeline 2 Stage 1",
            display_order=1,
        )
        self.inactive_stage = PipelineStage.objects.create(
            pipeline=self.pipeline,
            name="Inactive Stage",
            display_order=3,
            is_active=False,
        )

    # ---- Helpers ----

    def _create_manager_client(self, permissions=None, username=None, **kwargs):
        """Create an authenticated APIClient for a manager-level user."""
        rolename = kwargs.get("rolename", "Mgr_" + (username or "user"))
        role = Role.objects.create(rolename=rolename)
        codenames = permissions or [
            "view_lead",
            "add_lead",
            "change_lead",
            "assign_lead",
            "progress_lead",
            "mark_lead_lost",
            "reengage_lead",
            "convert_lead",
            "view_quotation",
            "add_quotation",
            "change_quotation",
            "submit_quotation",
            "approve_quotation",
            "send_quotation",
            "request_quotation_revision",
            "accept_quotation",
            "reject_quotation",
            "delete_quotation",
            "generate_quotation_pdf",
            "view_customer",
            "add_customer",
            "view_activity",
            "add_activity",
            "view_auditlog",
            "manage_lead_source",
            "manage_pipeline",
        ]
        role.permissions.set(Permission.objects.filter(codename__in=codenames))
        uname = username or f"mgr_{rolename.lower()}"
        phone = kwargs.get("phone", f"555{str(uuid4().int)[:7]}")
        user = User.objects.create_user(
            username=uname,
            email=f"{uname}@example.com",
            password="Password123!",
            phone_number=phone,
            role=role,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        return client, user, role

    def _create_employee_client(self, permissions=None, username=None, **kwargs):
        """Create an authenticated APIClient for an employee-level user."""
        rolename = "Emp_" + (username or "user")
        role = Role.objects.create(rolename=rolename)
        codenames = permissions or [
            "view_lead",
            "add_lead",
            "change_lead",
            "view_quotation",
            "add_quotation",
            "change_quotation",
            "submit_quotation",
            "send_quotation",
            "request_quotation_revision",
            "generate_quotation_pdf",
            "view_customer",
            "add_customer",
            "view_activity",
            "add_activity",
            "view_leadsource",
            "view_pipeline",
            "view_pipelinestage",
        ]
        role.permissions.set(Permission.objects.filter(codename__in=codenames))
        uname = username or f"emp_{rolename.lower()}"
        phone = kwargs.get("phone", f"555{str(uuid4().int)[:7]}")
        user = User.objects.create_user(
            username=uname,
            email=f"{uname}@example.com",
            password="Password123!",
            phone_number=phone,
            role=role,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        return client, user, role

    def _create_approval_pipeline(self, name="Approval Pipeline"):
        """Create a pipeline with a stage that requires quotation + approval."""
        pl = CRMService.create_pipeline(user=self.user, name=name)
        st = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pl,
            name=f"{name} Stage",
            display_order=1,
            requires_quotation=True,
            quotation_approval_required=True,
        )
        return pl, st


# ==============================================================================
# SECTION 1: LEAD SOURCE, PIPELINE & PIPELINE STAGE TESTS
# ==============================================================================


class LeadSourcePipelineTests(CRMBaseTestCase):
    """Tests for LeadSource, Pipeline, and PipelineStage API endpoints."""

    def test_create_lead_source(self):
        response = self.client.post(
            "/api/crm/lead-sources/",
            {
                "name": "Trade Show",
                "description": "Annual tech expo",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Trade Show")

    def test_list_lead_sources(self):
        CRMService.create_lead_source(user=self.user, name="API Source")
        response = self.client.get("/api/crm/lead-sources/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_duplicate_lead_source_name_rejected(self):
        CRMService.create_lead_source(user=self.user, name="Unique Source")
        response = self.client.post(
            "/api/crm/lead-sources/",
            {
                "name": "Unique Source",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_pipeline(self):
        response = self.client.post(
            "/api/crm/pipelines/",
            {
                "name": "API Pipeline",
                "description": "Created via API",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "API Pipeline")

    def test_duplicate_pipeline_name_rejected(self):
        CRMService.create_pipeline(user=self.user, name="Unique Pipeline")
        response = self.client.post(
            "/api/crm/pipelines/",
            {
                "name": "Unique Pipeline",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_pipelines(self):
        response = self.client.get("/api/crm/pipelines/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_pipeline_stage(self):
        response = self.client.post(
            "/api/crm/pipeline-stages/",
            {
                "pipeline": str(self.pipeline.id),
                "name": "API Stage",
                "display_order": 5,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "API Stage")

    def test_stage_in_inactive_pipeline_rejected(self):
        response = self.client.post(
            "/api/crm/pipeline-stages/",
            {
                "pipeline": str(self.inactive_pipeline.id),
                "name": "Should Fail",
                "display_order": 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_stage_display_order_below_one_rejected(self):
        response = self.client.post(
            "/api/crm/pipeline-stages/",
            {
                "pipeline": str(self.pipeline.id),
                "name": "Bad Order Stage",
                "display_order": 0,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_stage_with_quotation_flags(self):
        response = self.client.post(
            "/api/crm/pipeline-stages/",
            {
                "pipeline": str(self.pipeline.id),
                "name": "Quotation Stage",
                "display_order": 6,
                "requires_quotation": True,
                "quotation_approval_required": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["requires_quotation"])
        self.assertTrue(response.data["quotation_approval_required"])

    def test_list_pipeline_stages(self):
        response = self.client.get("/api/crm/pipeline-stages/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_employee_cannot_manage_lead_sources(self):
        emp_client, _, _ = self._create_employee_client()
        response = emp_client.post(
            "/api/crm/lead-sources/",
            {
                "name": "Emp Source",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_manage_pipelines(self):
        emp_client, _, _ = self._create_employee_client()
        response = emp_client.post(
            "/api/crm/pipelines/",
            {
                "name": "Emp Pipeline",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_manage_lead_sources(self):
        mgr_client, _, _ = self._create_manager_client()
        response = mgr_client.post(
            "/api/crm/lead-sources/",
            {
                "name": "Manager Source",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_manager_can_manage_pipelines(self):
        mgr_client, _, _ = self._create_manager_client()
        response = mgr_client.post(
            "/api/crm/pipelines/",
            {
                "name": "Manager Pipeline",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


# ==============================================================================
# SECTION 2: LEAD TESTS
# ==============================================================================


class LeadTests(CRMBaseTestCase):
    """Tests for Lead CRUD, assignment, progress, lost, re-engage, and conversion."""

    def setUp(self):
        super().setUp()
        self.lead = CRMService.create_lead(
            user=self.user,
            name="Default Lead",
            email="defaultlead@example.com",
            phone="1000000001",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )

    # --- CRUD ---

    def test_create_lead(self):
        response = self.client.post(
            "/api/crm/leads/",
            {
                "name": "API Lead",
                "email": "apilead@example.com",
                "phone": "2525252525",
                "source": str(self.source.id),
                "assigned_to": str(self.user.user_id),
                "pipeline": str(self.pipeline.id),
                "current_stage": str(self.stage1.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "API Lead")

    def test_list_leads(self):
        response = self.client.get("/api/crm/leads/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_lead_detail(self):
        response = self.client.get(f"/api/crm/leads/{self.lead.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Default Lead")

    def test_lead_detail_nonexistent_returns_404(self):
        fake_uuid = "00000000-0000-0000-0000-000000000099"
        response = self.client.get(f"/api/crm/leads/{fake_uuid}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_lead_update_creates_audit_log(self):
        response = self.client.patch(
            f"/api/crm/leads/{self.lead.id}/",
            {"name": "Updated Lead"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        audit = AuditLog.objects.filter(
            entity_id=self.lead.id,
            action="LEAD_UPDATED",
        ).first()
        self.assertIsNotNone(audit, "LEAD_UPDATED audit log should exist")
        self.assertEqual(audit.new_value["name"], "Updated Lead")

    # --- Validation ---

    def test_create_lead_with_inactive_source_rejected(self):
        response = self.client.post(
            "/api/crm/leads/",
            {
                "name": "Bad",
                "source": str(self.inactive_source.id),
                "assigned_to": str(self.user.user_id),
                "pipeline": str(self.pipeline.id),
                "current_stage": str(self.stage1.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_lead_with_inactive_pipeline_rejected(self):
        response = self.client.post(
            "/api/crm/leads/",
            {
                "name": "Bad",
                "source": str(self.source.id),
                "assigned_to": str(self.user.user_id),
                "pipeline": str(self.inactive_pipeline.id),
                "current_stage": str(self.stage1.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_lead_with_inactive_stage_rejected(self):
        response = self.client.post(
            "/api/crm/leads/",
            {
                "name": "Bad",
                "source": str(self.source.id),
                "assigned_to": str(self.user.user_id),
                "pipeline": str(self.pipeline.id),
                "current_stage": str(self.inactive_stage.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_lead_wrong_pipeline_stage_combo_rejected(self):
        response = self.client.post(
            "/api/crm/leads/",
            {
                "name": "Bad",
                "source": str(self.source.id),
                "assigned_to": str(self.user.user_id),
                "pipeline": str(self.pipeline.id),
                "current_stage": str(self.stage2_p2.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_converted_lead_rejected(self):
        CRMService.convert_lead(
            user=self.user,
            lead=self.lead,
            name="Conv Customer",
            email="defaultlead@example.com",
            phone="1000000001",
        )
        self.lead.refresh_from_db()
        response = self.client.patch(
            f"/api/crm/leads/{self.lead.id}/",
            {"current_stage": str(self.stage2.id)},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_lost_reason_on_active_lead_rejected(self):
        response = self.client.patch(
            f"/api/crm/leads/{self.lead.id}/",
            {"lost_reason": "not lost"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_inactive_source_on_lead_rejected(self):
        response = self.client.patch(
            f"/api/crm/leads/{self.lead.id}/",
            {"source": str(self.inactive_source.id)},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Assignment ---

    def test_assign_lead(self):
        new_user = User.objects.create_user(
            username="new_assignee",
            email="newassignee@example.com",
            password="Password123!",
            role=self.role,
        )
        response = self.client.post(
            f"/api/crm/leads/{self.lead.id}/assign/",
            {
                "assigned_to": str(new_user.user_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.assigned_to, new_user)

    def test_assign_lead_to_inactive_user_rejected(self):
        response = self.client.post(
            f"/api/crm/leads/{self.lead.id}/assign/",
            {
                "assigned_to": str(self.inactive_user.user_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assign_lead_missing_field_rejected(self):
        response = self.client.post(
            f"/api/crm/leads/{self.lead.id}/assign/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Progress ---

    def test_progress_lead(self):
        response = self.client.post(
            f"/api/crm/leads/{self.lead.id}/progress/",
            {
                "stage_id": str(self.stage2.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.current_stage, self.stage2)

    def test_progress_lead_to_nonexistent_stage_rejected(self):
        fake_uuid = "00000000-0000-0000-0000-000000000099"
        response = self.client.post(
            f"/api/crm/leads/{self.lead.id}/progress/",
            {
                "stage_id": fake_uuid,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_progress_converted_lead_rejected(self):
        CRMService.convert_lead(
            user=self.user,
            lead=self.lead,
            name="Conv Customer",
            email="defaultlead@example.com",
            phone="1000000001",
        )
        response = self.client.post(f"/api/crm/leads/{self.lead.id}/progress/", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Lost ---

    def test_mark_lead_lost(self):
        response = self.client.post(
            f"/api/crm/leads/{self.lead.id}/lost/",
            {
                "lost_reason": "Competitor offered better price",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.LOST)

    def test_mark_lead_lost_creates_audit_log(self):
        CRMService.mark_lead_lost(user=self.user, lead=self.lead, lost_reason="Budget")
        log = AuditLog.objects.filter(
            entity_id=self.lead.id,
            action="LEAD_LOST",
        ).first()
        self.assertIsNotNone(log, "LEAD_LOST audit log should exist")

    def test_mark_lead_lost_without_reason_rejected(self):
        response = self.client.post(
            f"/api/crm/leads/{self.lead.id}/lost/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Re-engage ---

    def test_reengage_lost_lead(self):
        CRMService.mark_lead_lost(user=self.user, lead=self.lead, lost_reason="Budget")
        response = self.client.post(f"/api/crm/leads/{self.lead.id}/reengage/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.ACTIVE)
        self.assertIsNone(self.lead.lost_reason)

    def test_reengage_active_lead_rejected(self):
        response = self.client.post(f"/api/crm/leads/{self.lead.id}/reengage/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reengagement_creates_audit_log(self):
        CRMService.mark_lead_lost(user=self.user, lead=self.lead, lost_reason="Budget")
        CRMService.reengage_lead(user=self.user, lead=self.lead)
        log = AuditLog.objects.filter(
            entity_id=self.lead.id,
            action="LEAD_REENGAGED",
        ).first()
        self.assertIsNotNone(log, "LEAD_REENGAGED audit log should exist")

    # --- Conversion via API ---

    def test_convert_active_lead_creates_customer(self):
        response = self.client.post(
            f"/api/crm/leads/{self.lead.id}/convert/",
            {
                "name": "Conv Customer",
                "email": "defaultlead@example.com",
                "phone": "1000000001",
                "company_name": "Conv Corp",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Conv Customer")
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.CONVERTED)

    def test_convert_lead_uses_defaults_when_fields_omitted(self):
        response = self.client.post(
            f"/api/crm/leads/{self.lead.id}/convert/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Default Lead")
        self.assertEqual(response.data["email"], "defaultlead@example.com")

    def test_convert_lead_missing_email_rejected(self):
        no_email_lead = CRMService.create_lead(
            user=self.user,
            name="No Email",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        response = self.client.post(
            f"/api/crm/leads/{no_email_lead.id}/convert/",
            {"phone": "9999999999"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_convert_lead_missing_phone_rejected(self):
        no_phone_lead = CRMService.create_lead(
            user=self.user,
            name="No Phone",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
            phone=None,
        )
        response = self.client.post(
            f"/api/crm/leads/{no_phone_lead.id}/convert/",
            {
                "email": "nophone@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_convert_already_converted_lead_rejected(self):
        CRMService.convert_lead(
            user=self.user,
            lead=self.lead,
            name="Already Conv",
            email="defaultlead@example.com",
            phone="1000000001",
        )
        response = self.client.post(
            f"/api/crm/leads/{self.lead.id}/convert/",
            {
                "email": "new@example.com",
                "phone": "1111111111",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_convert_lead_duplicate_customer_email_rejected(self):
        CRMService.convert_lead(
            user=self.user,
            lead=self.lead,
            name="First Customer",
            email="shared@example.com",
            phone="1000000001",
        )
        lead2 = CRMService.create_lead(
            user=self.user,
            name="Lead 2",
            email="lead2@example.com",
            phone="2000000002",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        response = self.client.post(
            f"/api/crm/leads/{lead2.id}/convert/",
            {
                "email": "shared@example.com",
                "phone": "2000000002",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_convert_lost_lead_rejected(self):
        CRMService.mark_lead_lost(user=self.user, lead=self.lead, lost_reason="Budget")
        response = self.client.post(
            f"/api/crm/leads/{self.lead.id}/convert/",
            {
                "email": "x@x.com",
                "phone": "1234567890",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_convert_nonexistent_lead_returns_404(self):
        fake_uuid = "00000000-0000-0000-0000-000000000099"
        response = self.client.post(
            f"/api/crm/leads/{fake_uuid}/convert/",
            {
                "email": "x@x.com",
                "phone": "1234567890",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_convert_lead_quotation_required_but_missing_rejected(self):
        pl, st = CRMService.create_pipeline(user=self.user, name="ReqQ Pipeline"), None
        st = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pl,
            name="ReqQ Stage",
            display_order=1,
            requires_quotation=True,
        )
        lead = CRMService.create_lead(
            user=self.user,
            name="ReqQ Lead",
            email="reqq@example.com",
            phone="3000000003",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        response = self.client.post(
            f"/api/crm/leads/{lead.id}/convert/",
            {
                "email": "reqq@example.com",
                "phone": "3000000003",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_convert_lead_quotation_accepted_succeeds(self):
        pl, st = CRMService.create_pipeline(user=self.user, name="AccQ Pipeline"), None
        st = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pl,
            name="AccQ Stage",
            display_order=1,
            requires_quotation=True,
        )
        lead = CRMService.create_lead(
            user=self.user,
            name="AccQ Lead",
            email="accq@example.com",
            phone="4000000004",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        q.refresh_from_db()
        QuotationService.accept_quotation(user=self.user, quotation=q)
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.Status.CONVERTED)
        self.assertTrue(Customer.objects.filter(lead=lead).exists())

    # --- Unauthenticated ---

    def test_unauthenticated_lead_list_rejected(self):
        unauth = APIClient()
        response = unauth.get("/api/crm/leads/")
        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

    # --- Permission matrix ---

    def test_employee_can_list_leads(self):
        emp_client, _, _ = self._create_employee_client()
        response = emp_client.get("/api/crm/leads/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employee_can_create_lead(self):
        emp_client, emp_user, _ = self._create_employee_client()
        response = emp_client.post(
            "/api/crm/leads/",
            {
                "name": "Emp Lead",
                "source": str(self.source.id),
                "assigned_to": str(emp_user.user_id),
                "pipeline": str(self.pipeline.id),
                "current_stage": str(self.stage1.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_employee_cannot_assign_lead(self):
        emp_client, emp_user, _ = self._create_employee_client()
        lead = CRMService.create_lead(
            user=emp_user,
            name="Emp Lead",
            source=self.source,
            assigned_to=emp_user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        response = emp_client.post(
            f"/api/crm/leads/{lead.id}/assign/",
            {
                "assigned_to": str(emp_user.user_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_progress_lead(self):
        emp_client, emp_user, _ = self._create_employee_client()
        lead = CRMService.create_lead(
            user=emp_user,
            name="Emp Lead",
            source=self.source,
            assigned_to=emp_user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        response = emp_client.post(
            f"/api/crm/leads/{lead.id}/progress/",
            {
                "stage_id": str(self.stage2.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_mark_lead_lost(self):
        emp_client, emp_user, _ = self._create_employee_client()
        lead = CRMService.create_lead(
            user=emp_user,
            name="Emp Lead",
            source=self.source,
            assigned_to=emp_user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        response = emp_client.post(
            f"/api/crm/leads/{lead.id}/lost/",
            {
                "lost_reason": "Budget",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_convert_lead(self):
        emp_client, emp_user, _ = self._create_employee_client()
        lead = CRMService.create_lead(
            user=emp_user,
            name="Emp Lead",
            source=self.source,
            assigned_to=emp_user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        response = emp_client.post(
            f"/api/crm/leads/{lead.id}/convert/",
            {
                "email": "x@x.com",
                "phone": "123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ==============================================================================
# SECTION 3: CUSTOMER TESTS
# ==============================================================================


class CustomerTests(CRMBaseTestCase):
    """Tests for Customer list, detail, create, activities, and endpoint restrictions."""

    def _make_customer(self, name="Cust", email="c@example.com", phone="111"):
        lead = CRMService.create_lead(
            user=self.user,
            name=f"{name} Lead",
            email=email,
            phone=phone,
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        return CRMService.convert_lead(
            user=self.user,
            lead=lead,
            name=name,
            email=email,
            phone=phone,
        )

    def test_customer_list_empty_when_no_customers(self):
        response = self.client.get("/api/crm/customers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_customer_list_returns_all_customers(self):
        self._make_customer(name="Cust A", email="a@x.com", phone="111")
        self._make_customer(name="Cust B", email="b@x.com", phone="222")
        response = self.client.get("/api/crm/customers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_customer_detail_returns_correct_data(self):
        cust = self._make_customer(name="Detail Cust", email="d@x.com", phone="333")
        response = self.client.get(f"/api/crm/customers/{cust.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Detail Cust")
        self.assertEqual(response.data["email"], "d@x.com")

    def test_customer_detail_nonexistent_returns_404(self):
        fake_uuid = "00000000-0000-0000-0000-000000000099"
        response = self.client.get(f"/api/crm/customers/{fake_uuid}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_create_via_direct_post(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Post Lead",
            email="post@x.com",
            phone="444",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        response = self.client.post(
            "/api/crm/customers/",
            {
                "lead": str(lead.id),
                "name": "Post Customer",
                "email": "post@x.com",
                "phone": "444",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Post Customer")

    def test_customer_update_returns_forbidden(self):
        cust = self._make_customer()
        response = self.client.patch(
            f"/api/crm/customers/{cust.id}/",
            {"name": "Nope"},
            format="json",
        )
        self.assertIn(
            response.status_code,
            [
                status.HTTP_405_METHOD_NOT_ALLOWED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

    def test_customer_delete_returns_forbidden(self):
        cust = self._make_customer()
        response = self.client.delete(f"/api/crm/customers/{cust.id}/")
        self.assertIn(
            response.status_code,
            [
                status.HTTP_405_METHOD_NOT_ALLOWED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

    def test_duplicate_email_rejected_via_lead_conversion(self):
        self._make_customer(name="First", email="dup@x.com", phone="555")
        lead2 = CRMService.create_lead(
            user=self.user,
            name="Lead 2",
            email="lead2@x.com",
            phone="666",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        response = self.client.post(
            f"/api/crm/leads/{lead2.id}/convert/",
            {
                "email": "dup@x.com",
                "phone": "666",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_create_triggers_audit_log(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Audit Lead",
            email="audit@x.com",
            phone="777",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        response = self.client.post(
            "/api/crm/customers/",
            {
                "lead": str(lead.id),
                "name": "Audit Cust",
                "email": "audit@x.com",
                "phone": "777",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        customer = Customer.objects.get(lead=lead)
        audit = AuditLog.objects.filter(
            entity_type="Customer",
            entity_id=customer.id,
            action="CUSTOMER_CREATED",
        ).first()
        self.assertIsNotNone(audit, "CUSTOMER_CREATED audit log should exist")

    # --- Customer Activities ---

    def test_customer_activities_empty_for_new_customer(self):
        cust = self._make_customer()
        response = self.client.get(f"/api/crm/customers/{cust.id}/activities/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_customer_activities_returns_activities(self):
        cust = self._make_customer()
        CRMService.create_activity(
            user=self.user,
            activity_type="CALL",
            outcome="Discussed requirements",
            customer=cust,
        )
        response = self.client.get(f"/api/crm/customers/{cust.id}/activities/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["activity_type"], "CALL")

    def test_unauthenticated_customer_access_rejected(self):
        unauth = APIClient()
        response = unauth.get("/api/crm/customers/")
        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )


# ==============================================================================
# SECTION 4: ACTIVITY TESTS
# ==============================================================================


class ActivityTests(CRMBaseTestCase):
    """Tests for Activity list and create endpoints."""

    def test_create_activity_for_lead(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Act Lead",
            email="actlead@x.com",
            phone="1111111111",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        response = self.client.post(
            "/api/crm/activities/",
            {
                "lead": str(lead.id),
                "activity_type": "CALL",
                "outcome": "Initial consultation completed",
                "notes": "Discussed project scope",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["activity_type"], "CALL")

    def test_create_activity_for_customer(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Act Cust Lead",
            email="actcust@x.com",
            phone="2222222222",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        customer = CRMService.convert_lead(
            user=self.user,
            lead=lead,
            name="Act Cust",
            email="actcust@x.com",
            phone="2222222222",
        )
        response = self.client.post(
            "/api/crm/activities/",
            {
                "customer": str(customer.id),
                "activity_type": "MEETING",
                "outcome": "Product demo delivered",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_activity_without_lead_or_customer_rejected(self):
        response = self.client.post(
            "/api/crm/activities/",
            {
                "activity_type": "EMAIL",
                "outcome": "Sent follow-up",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_activity_with_both_lead_and_customer_rejected(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Both Lead",
            email="both@x.com",
            phone="3333333333",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        customer = CRMService.convert_lead(
            user=self.user,
            lead=lead,
            name="Both Cust",
            email="both@x.com",
            phone="3333333333",
        )
        response = self.client.post(
            "/api/crm/activities/",
            {
                "lead": str(lead.id),
                "customer": str(customer.id),
                "activity_type": "CALL",
                "outcome": "Conflicting",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_follow_up_requires_date(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="FU Lead",
            email="fu@x.com",
            phone="4444444444",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        response = self.client.post(
            "/api/crm/activities/",
            {
                "lead": str(lead.id),
                "activity_type": "FOLLOW_UP",
                "outcome": "Schedule next call",
                "follow_up_required": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_follow_up_date_without_flag_rejected(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Flag Lead",
            email="flag@x.com",
            phone="5555555555",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        response = self.client.post(
            "/api/crm/activities/",
            {
                "lead": str(lead.id),
                "activity_type": "EMAIL",
                "outcome": "Sent brochure",
                "follow_up_date": "2026-09-01T10:00:00Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_activity_for_converted_lead_rejected(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Conv Lead",
            email="conv@x.com",
            phone="6666666666",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        CRMService.convert_lead(
            user=self.user,
            lead=lead,
            name="Conv Cust",
            email="conv@x.com",
            phone="6666666666",
        )
        response = self.client.post(
            "/api/crm/activities/",
            {
                "lead": str(lead.id),
                "activity_type": "CALL",
                "outcome": "Should fail",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_activities(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="List Lead",
            email="list@x.com",
            phone="7777777777",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        CRMService.create_activity(
            user=self.user,
            activity_type="DEMO",
            outcome="Demo completed",
            lead=lead,
        )
        response = self.client.get("/api/crm/activities/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_activity_creation_creates_audit_log(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Audit Act Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        activity = CRMService.create_activity(
            user=self.user,
            activity_type="CALL",
            outcome="Discussed pricing",
            lead=lead,
        )
        log = AuditLog.objects.filter(
            entity_type="Activity",
            entity_id=activity.id,
            action="ACTIVITY_CREATED",
        ).first()
        self.assertIsNotNone(log, "ACTIVITY_CREATED audit log should exist")


# ==============================================================================
# SECTION 5: QUOTATION CRUD & STATE TRANSITIONS
# ==============================================================================


class QuotationCRUDTests(CRMBaseTestCase):
    """Tests for Quotation create, read, update, and state transition validation."""

    def setUp(self):
        super().setUp()
        self.lead = CRMService.create_lead(
            user=self.user,
            name="QC Lead",
            email="qclead@example.com",
            phone="2828282828",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )

    # --- CRUD ---

    def test_create_retrieve_update_quotation(self):
        response = self.client.post(
            "/api/crm/quotations/",
            {
                "lead_id": str(self.lead.id),
                "terms": "Net 30",
                "notes": "Initial draft",
                "line_items": [
                    {"description": "Product A", "quantity": 2, "unit_price": "50.00"},
                    {"description": "Product B", "quantity": 1, "unit_price": "100.00"},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        qid = response.data["id"]

        resp = self.client.get(f"/api/crm/quotations/{qid}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "DRAFT")
        self.assertAlmostEqual(
            Decimal(resp.data["current_version_detail"]["total_amount"]),
            Decimal("200.00"),
            places=2,
        )

        resp = self.client.patch(
            f"/api/crm/quotations/{qid}/update-draft/",
            {
                "terms": "Net 15",
                "line_items": [
                    {"description": "Product A", "quantity": 3, "unit_price": "50.00"}
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertAlmostEqual(
            Decimal(resp.data["current_version_detail"]["total_amount"]),
            Decimal("150.00"),
            places=2,
        )

    def test_quotation_number_is_unique(self):
        q1 = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "A", "quantity": 1, "unit_price": 100}],
        )
        q2 = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "B", "quantity": 1, "unit_price": 200}],
        )
        self.assertNotEqual(q1.quotation_number, q2.quotation_number)

    def test_update_draft_replaces_all_line_items(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[
                {"description": "A", "quantity": 1, "unit_price": 100},
                {"description": "B", "quantity": 2, "unit_price": 50},
            ],
        )
        resp = self.client.patch(
            f"/api/crm/quotations/{q.id}/update-draft/",
            {
                "line_items": [
                    {"description": "Only", "quantity": 5, "unit_price": 20}
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        q.refresh_from_db()
        self.assertEqual(q.current_version.line_items.count(), 1)
        self.assertEqual(q.current_version.total_amount, Decimal("100.00"))

    def test_update_non_draft_quotation_rejected(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "A", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        resp = self.client.patch(
            f"/api/crm/quotations/{q.id}/update-draft/",
            {"terms": "Nope"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Edge Cases ---

    def test_create_quotation_with_empty_line_items(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[],
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.total_amount, Decimal("0.00"))
        self.assertEqual(q.current_version.line_items.count(), 0)

    def test_create_quotation_with_no_line_items(self):
        q = QuotationService.create_quotation(user=self.user, lead=self.lead)
        q.refresh_from_db()
        self.assertEqual(q.current_version.total_amount, Decimal("0.00"))

    def test_create_quotation_for_converted_lead_rejected(self):
        CRMService.convert_lead(
            user=self.user,
            lead=self.lead,
            name="Conv Cust",
            email="qclead@example.com",
            phone="2828282828",
        )
        with self.assertRaises(ValidationError):
            QuotationService.create_quotation(
                user=self.user,
                lead=self.lead,
                line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
            )

    def test_create_quotation_for_lost_lead_rejected(self):
        CRMService.mark_lead_lost(user=self.user, lead=self.lead, lost_reason="Budget")
        with self.assertRaises(ValidationError):
            QuotationService.create_quotation(
                user=self.user,
                lead=self.lead,
                line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
            )

    def test_revision_from_draft_creates_new_version(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Draft", "quantity": 1, "unit_price": 50}],
        )
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/revision/",
            {
                "terms": "Revised from draft",
                "line_items": [{"description": "Rev", "quantity": 2, "unit_price": 75}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        q.refresh_from_db()
        self.assertEqual(q.current_version.version_number, 2)

    def test_nonexistent_quotation_returns_404(self):
        fake = "00000000-0000-0000-0000-000000000099"
        self.assertEqual(
            self.client.get(f"/api/crm/quotations/{fake}/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.post(f"/api/crm/quotations/{fake}/submit/").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_reject_approval_returns_to_draft(self):
        pl, st = self._create_approval_pipeline("Reject Appr Pipeline")
        lead = CRMService.create_lead(
            user=self.user,
            name="RA Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertEqual(q.status, "PENDING_APPROVAL")

        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/reject-approval/",
            {
                "reason": "Budget exceeded",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        q.refresh_from_db()
        self.assertEqual(q.status, "DRAFT")

    def test_quotation_list_filter_by_lead(self):
        lead2 = CRMService.create_lead(
            user=self.user,
            name="Filter Lead",
            email="filter@x.com",
            phone="9999999999",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "A", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.create_quotation(
            user=self.user,
            lead=lead2,
            line_items=[{"description": "B", "quantity": 1, "unit_price": 200}],
        )
        response = self.client.get(f"/api/crm/quotations/?lead={self.lead.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    # --- Invalid state transitions ---

    def test_cannot_approve_draft_quotation(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        resp = self.client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_send_draft_quotation(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        resp = self.client.post(f"/api/crm/quotations/{q.id}/send/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_accept_draft_quotation(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        resp = self.client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_accept_pending_approval_quotation(self):
        pl, st = self._create_approval_pipeline("Pending Pipeline")
        lead = CRMService.create_lead(
            user=self.user,
            name="Pending Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        resp = self.client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_send_pending_approval_quotation(self):
        pl, st = self._create_approval_pipeline("Pending2 Pipeline")
        lead = CRMService.create_lead(
            user=self.user,
            name="Pending2 Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        resp = self.client.post(f"/api/crm/quotations/{q.id}/send/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_resubmit_approved_quotation(self):
        pl, st = self._create_approval_pipeline("Resubmit Pipeline")
        lead = CRMService.create_lead(
            user=self.user,
            name="Resubmit Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        resp = self.client.post(f"/api/crm/quotations/{q.id}/submit/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot be submitted for approval", resp.data["detail"])

    def test_full_invalid_transition_matrix(self):
        """DRAFT: reject/send/pdf blocked. PENDING: send/accept/pdf blocked."""
        pl, st = self._create_approval_pipeline("SM Pipeline")
        lead = CRMService.create_lead(
            user=self.user,
            name="SM Lead",
            email="sm@x.com",
            phone="5552223333",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )

        # DRAFT
        for action in ["accept", "reject", "send"]:
            self.assertEqual(
                self.client.post(
                    f"/api/crm/quotations/{q.id}/{action}/",
                    {"rejection_reason": "x"} if action == "reject" else {},
                    format="json",
                ).status_code,
                status.HTTP_400_BAD_REQUEST,
                f"Should reject {action} in DRAFT",
            )
        self.assertEqual(
            self.client.get(f"/api/crm/quotations/{q.id}/pdf/").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        # Verify status unchanged
        q.refresh_from_db()
        self.assertEqual(q.status, "DRAFT")

        # Submit -> PENDING_APPROVAL
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertEqual(q.status, "PENDING_APPROVAL")

        for action in ["send", "accept"]:
            self.assertEqual(
                self.client.post(f"/api/crm/quotations/{q.id}/{action}/").status_code,
                status.HTTP_400_BAD_REQUEST,
                f"Should reject {action} in PENDING_APPROVAL",
            )
        self.assertEqual(
            self.client.get(f"/api/crm/quotations/{q.id}/pdf/").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        # Approve -> APPROVED (must use a different user to avoid self-approval block)
        mgr_client, mgr_user, _ = self._create_manager_client()
        QuotationService.approve_quotation(
            reviewer_user=mgr_user,
            quotation=q,
        )
        q.refresh_from_db()
        self.assertEqual(q.status, "APPROVED")

        # Cannot re-submit APPROVED
        self.assertEqual(
            self.client.post(f"/api/crm/quotations/{q.id}/submit/").status_code,
            status.HTTP_400_BAD_REQUEST,
        )


# ==============================================================================
# SECTION 6: QUOTATION WORKFLOW (SUBMIT, APPROVE, SEND, ACCEPT, REJECT)
# ==============================================================================


class QuotationWorkflowTests(CRMBaseTestCase):
    """Tests for the full quotation lifecycle: submit, approve, send, accept, reject."""

    def setUp(self):
        super().setUp()
        self.lead = CRMService.create_lead(
            user=self.user,
            name="QW Lead",
            email="qwlead@example.com",
            phone="9876543210",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )

    def test_submit_approve_send_accept_full_lifecycle(self):
        pl, st = self._create_approval_pipeline("Lifecycle Pipeline")
        lead = CRMService.create_lead(
            user=self.user,
            name="LC Lead",
            email="lclead@example.com",
            phone="1234567890",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        resp_submit = self.client.post(f"/api/crm/quotations/{q.id}/submit/")
        self.assertEqual(resp_submit.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_submit.data["status"], "PENDING_APPROVAL")

        resp_approve = self.client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp_approve.status_code, status.HTTP_403_FORBIDDEN)

        mgr_client, _, _ = self._create_manager_client()
        resp_approve = mgr_client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp_approve.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_approve.data["status"], "APPROVED")

        resp_send = self.client.post(f"/api/crm/quotations/{q.id}/send/")
        self.assertEqual(resp_send.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_send.data["status"], "SENT")

        resp_accept = self.client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp_accept.status_code, status.HTTP_200_OK)
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.Status.CONVERTED)
        self.assertIsNotNone(Customer.objects.filter(lead=lead).first())

    def test_approval_workflow_requires_manager(self):
        pl, st = self._create_approval_pipeline()
        lead = CRMService.create_lead(
            user=self.user,
            name="Appr Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 500}],
        )

        # Cannot send before approval
        self.assertEqual(
            self.client.post(f"/api/crm/quotations/{q.id}/send/").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        # Submit -> PENDING_APPROVAL
        resp = self.client.post(f"/api/crm/quotations/{q.id}/submit/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "PENDING_APPROVAL")

        # Manager approves
        mgr_client, _, _ = self._create_manager_client()
        resp = mgr_client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "APPROVED")

        # Now send succeeds
        resp = self.client.post(f"/api/crm/quotations/{q.id}/send/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_accept_quotation_converts_lead(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q = QuotationService.send_quotation(user=self.user, quotation=q)
        resp = self.client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.CONVERTED)
        self.assertTrue(Customer.objects.filter(lead=self.lead).exists())

    def test_reject_quotation_marks_lead_lost(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q = QuotationService.send_quotation(user=self.user, quotation=q)
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/reject/",
            {
                "rejection_reason": "Too expensive",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.LOST)
        self.assertIn("Too expensive", self.lead.lost_reason)

    def test_double_accept_rejected(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        q.refresh_from_db()
        QuotationService.accept_quotation(user=self.user, quotation=q)
        resp = self.client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_already_rejected_quotation_rejected(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        q.refresh_from_db()
        QuotationService.reject_quotation(
            user=self.user,
            quotation=q,
            rejection_reason="Price",
        )
        q.refresh_from_db()
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/reject/",
            {
                "rejection_reason": "Still too high",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_send_prevented(self):
        q = QuotationService.create_quotation(user=self.user, lead=self.lead)
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        resp = self.client.post(f"/api/crm/quotations/{q.id}/send/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        event_count = QuotationIntegrationEvent.objects.filter(
            quotation=q,
            event_type="quotation.followup_required",
        ).count()
        self.assertEqual(event_count, 1, "Should only have one follow-up event")

    def test_integration_event_created_on_send(self):
        q = QuotationService.create_quotation(user=self.user, lead=self.lead)
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        event = QuotationIntegrationEvent.objects.filter(quotation=q).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "quotation.followup_required")
        self.assertEqual(event.payload["lead_id"], str(self.lead.id))
        self.assertEqual(event.payload["quotation_id"], str(q.id))

    def test_quotation_update_draft_creates_activity(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Original", "quantity": 1, "unit_price": 100}],
        )
        self.client.patch(
            f"/api/crm/quotations/{q.id}/update-draft/",
            {
                "terms": "Updated terms",
            },
            format="json",
        )
        act = Activity.objects.filter(
            quotation=q,
            activity_type="QUOTATION_UPDATED",
        ).first()
        self.assertIsNotNone(act, "QUOTATION_UPDATED activity should exist")

    def test_pipeline_stage_enforces_quotation_gate(self):
        pl, st = CRMService.create_pipeline(user=self.user, name="Gate Pipeline"), None
        st = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pl,
            name="Gate Stage",
            display_order=1,
            requires_quotation=True,
        )
        lead = CRMService.create_lead(
            user=self.user,
            name="Gate Lead",
            email="gate@x.com",
            phone="1112223333",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        with self.assertRaises(ValidationError):
            CRMService.convert_lead(
                user=self.user,
                lead=lead,
                name="Gate Cust",
                email="gate@x.com",
                phone="1112223333",
            )

        q = QuotationService.create_quotation(user=self.user, lead=lead)
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q = QuotationService.send_quotation(user=self.user, quotation=q)
        QuotationService.accept_quotation(user=self.user, quotation=q)
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.Status.CONVERTED)


# ==============================================================================
# SECTION 7: QUOTATION VERSIONING & REVISION HISTORY
# ==============================================================================


class QuotationVersioningTests(CRMBaseTestCase):
    """Tests for quotation versioning, revision history, and multi-version immutability."""

    def setUp(self):
        super().setUp()
        self.lead = CRMService.create_lead(
            user=self.user,
            name="Rev Lead",
            email="rev@example.com",
            phone="5553334444",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )

    def test_revision_increments_version_number(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "v1", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/revision/",
            {
                "terms": "Revised",
                "line_items": [{"description": "v2", "quantity": 2, "unit_price": 150}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["current_version_detail"]["version_number"], 2)
        self.assertEqual(len(resp.data["all_versions"]), 2)

    def test_v1_historical_immutability_after_revision(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            terms="Terms v1",
            notes="Notes v1",
            line_items=[{"description": "v1", "quantity": 2, "unit_price": 500}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation_email(
            user=self.user,
            quotation=q,
            recipient_email="rev@example.com",
        )
        q.refresh_from_db()
        v1 = q.current_version
        self.assertEqual(v1.sent_to, "rev@example.com")

        # Create v2
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/revision/",
            {
                "revision_reason": "Client discount",
                "terms": "Terms v2",
                "notes": "Notes v2",
                "line_items": [{"description": "v2", "quantity": 2, "unit_price": 400}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # v1 is immutable
        v1.refresh_from_db()
        self.assertEqual(v1.status, "REVISED")
        self.assertEqual(v1.terms, "Terms v1")
        self.assertEqual(v1.notes, "Notes v1")
        self.assertEqual(v1.sent_to, "rev@example.com")
        self.assertEqual(v1.total_amount, Decimal("1000.00"))
        self.assertEqual(v1.line_items.first().unit_price, Decimal("500.00"))

    def test_multi_version_v1_v2_v3_accept_specific_version(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            terms="v1",
            line_items=[{"description": "v1", "quantity": 2, "unit_price": 500}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)

        # v2
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/revision/",
            {
                "revision_reason": "Discount",
                "terms": "v2",
                "line_items": [{"description": "v2", "quantity": 2, "unit_price": 400}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        q.refresh_from_db()
        v1 = QuotationVersion.objects.get(quotation=q, version_number=1)
        v2 = q.current_version

        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)

        # v3
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/revision/",
            {
                "revision_reason": "Add service pack",
                "terms": "v3",
                "line_items": [
                    {"description": "v2", "quantity": 2, "unit_price": 400},
                    {"description": "Service Pack", "quantity": 1, "unit_price": 300},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        q.refresh_from_db()
        v3 = q.current_version
        self.assertEqual(v3.version_number, 3)

        # Accept v2
        v2.status = "SENT"
        v2.save()
        q.current_version = v2
        q.status = "SENT"
        q.save()
        resp = self.client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        q.refresh_from_db()
        self.assertEqual(q.accepted_version, v2)
        self.assertEqual(q.accepted_version.version_number, 2)

        # v1 and v3 unchanged
        v1.refresh_from_db()
        v3.refresh_from_db()
        self.assertEqual(v1.version_number, 1)
        self.assertEqual(v3.version_number, 3)
        self.assertNotEqual(v1.status, "ACCEPTED")

    def test_revision_reason_recorded(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/revision/",
            {
                "revision_reason": "Customer feedback on pricing",
                "line_items": [
                    {"description": "Item", "quantity": 1, "unit_price": 90}
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        q.refresh_from_db()
        self.assertEqual(
            q.current_version.revision_reason, "Customer feedback on pricing"
        )


# ==============================================================================
# SECTION 8: QUOTATION PDF & EMAIL
# ==============================================================================


class QuotationPDFAndEmailTests(CRMBaseTestCase):
    """Tests for quotation PDF generation and email delivery."""

    def setUp(self):
        super().setUp()
        self.lead = CRMService.create_lead(
            user=self.user,
            name="PDF Lead",
            email="pdf@example.com",
            phone="5551112222",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )

    def test_pdf_blocked_for_draft(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        resp = self.client.get(f"/api/crm/quotations/{q.id}/pdf/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pdf_blocked_for_pending_approval(self):
        pl, st = self._create_approval_pipeline("PDF Appr Pipeline")
        lead = CRMService.create_lead(
            user=self.user,
            name="PDF Pending Lead",
            email="pdfpending@x.com",
            phone="5551112222",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertEqual(q.status, "PENDING_APPROVAL")
        resp = self.client.get(f"/api/crm/quotations/{q.id}/pdf/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pdf_allowed_for_approved_quotation(self):
        pl, st = CRMService.create_pipeline(user=self.user, name="PDF Pipeline"), None
        st = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pl,
            name="PDF Stage",
            display_order=1,
            requires_quotation=True,
            quotation_approval_required=True,
        )
        lead = CRMService.create_lead(
            user=self.user,
            name="PDF Appr Lead",
            email="pdfappr@x.com",
            phone="5551112222",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            terms="Net 30",
            notes="PDF Test",
            line_items=[
                {"description": "Product A", "quantity": 2, "unit_price": 500},
                {"description": "Product B", "quantity": 1, "unit_price": 1000},
            ],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)

        mgr_client, _, _ = self._create_manager_client()
        # Need a manager with approve permission
        mgr_user = User.objects.create_user(
            username="pdf_mgr",
            email="pdfmgr@x.com",
            password="Password123!",
            role=self.role,
        )
        QuotationService.approve_quotation(reviewer_user=mgr_user, quotation=q)
        q.refresh_from_db()
        self.assertIsNotNone(q.current_version.approved_at)

        resp = self.client.get(f"/api/crm/quotations/{q.id}/pdf/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertIn(f"{q.quotation_number}_v1.pdf", resp["Content-Disposition"])
        self.assertTrue(len(resp.content) > 0)

        audit = AuditLog.objects.filter(
            entity_id=q.id,
            action="QUOTATION_PDF_GENERATED",
        ).first()
        self.assertIsNotNone(audit, "QUOTATION_PDF_GENERATED audit should exist")

    def test_pdf_specific_version(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "V1", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        resp = self.client.get(f"/api/crm/quotations/{q.id}/pdf/?version=1")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_pdf_nonexistent_version_returns_404(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        resp = self.client.get(f"/api/crm/quotations/{q.id}/pdf/?version=99")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_pdf_invalid_version_format_returns_400(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        resp = self.client.get(f"/api/crm/quotations/{q.id}/pdf/?version=abc")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_sends_with_pdf_attachment(self):
        from django.core import mail

        pl, st = CRMService.create_pipeline(user=self.user, name="Email Pipeline"), None
        st = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pl,
            name="Email Stage",
            display_order=1,
            requires_quotation=True,
        )
        lead = CRMService.create_lead(
            user=self.user,
            name="Email Lead",
            email="emaillead@x.com",
            phone="5553334444",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            terms="Initial Terms",
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 500}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertEqual(q.status, "APPROVED")

        mail.outbox = []
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/send-email/",
            {
                "recipient_email": "emaillead@x.com",
                "subject": "Custom Proposal",
                "body": "Please review the attached proposal.",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        q.refresh_from_db()
        self.assertEqual(q.status, "SENT")
        self.assertEqual(q.current_version.sent_to, "emaillead@x.com")
        self.assertIsNotNone(q.current_version.sent_at)

        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["emaillead@x.com"])
        self.assertEqual(msg.subject, "Custom Proposal")
        self.assertEqual(len(msg.attachments), 1)
        att_name, _, att_mime = msg.attachments[0]
        self.assertEqual(att_name, f"{q.quotation_number}_v1.pdf")
        self.assertEqual(att_mime, "application/pdf")

        audit = AuditLog.objects.filter(
            entity_id=q.id,
            action="QUOTATION_EMAIL_SENT",
        ).first()
        self.assertIsNotNone(audit, "QUOTATION_EMAIL_SENT audit should exist")
        act = Activity.objects.filter(
            quotation=q,
            activity_type="QUOTATION_EMAIL_SENT",
        ).first()
        self.assertIsNotNone(act, "QUOTATION_EMAIL_SENT activity should exist")

    def test_email_nonexistent_quotation_returns_404(self):
        fake = "00000000-0000-0000-0000-000000000099"
        resp = self.client.post(f"/api/crm/quotations/{fake}/send-email/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_pdf_nonexistent_quotation_returns_404(self):
        fake = "00000000-0000-0000-0000-000000000099"
        resp = self.client.get(f"/api/crm/quotations/{fake}/pdf/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_email_invalid_version_format_returns_400(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/send-email/",
            {
                "version": "xyz",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ==============================================================================
# SECTION 9: PERMISSIONS & RBAC
# ==============================================================================


class PermissionAndRBACTests(CRMBaseTestCase):
    """Tests for RBAC permission enforcement across all CRM endpoints."""

    def setUp(self):
        super().setUp()
        self.emp_client, self.employee, self.emp_role = self._create_employee_client(
            username="rbac_emp",
        )
        self.mgr_client, self.manager, self.mgr_role = self._create_manager_client(
            username="rbac_mgr",
        )

    def test_employee_cannot_approve_quotation(self):
        pl, st = self._create_approval_pipeline("Perm Appr")
        lead = CRMService.create_lead(
            user=self.employee,
            name="Emp Lead",
            source=self.source,
            assigned_to=self.employee,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(user=self.employee, lead=lead)
        QuotationService.submit_quotation_for_approval(user=self.employee, quotation=q)
        resp = self.emp_client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_reject_quotation(self):
        lead = CRMService.create_lead(
            user=self.employee,
            name="Emp Lead",
            source=self.source,
            assigned_to=self.employee,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        q = QuotationService.create_quotation(
            user=self.employee,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.employee, quotation=q)
        QuotationService.send_quotation(user=self.employee, quotation=q)
        resp = self.emp_client.post(
            f"/api/crm/quotations/{q.id}/reject/",
            {
                "rejection_reason": "Price",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_approve_quotation(self):
        pl, st = self._create_approval_pipeline("Mgr Appr")
        lead = CRMService.create_lead(
            user=self.employee,
            name="Mgr Lead",
            source=self.source,
            assigned_to=self.employee,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(user=self.employee, lead=lead)
        QuotationService.submit_quotation_for_approval(user=self.employee, quotation=q)
        resp = self.mgr_client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_manager_can_reject_quotation(self):
        lead = CRMService.create_lead(
            user=self.employee,
            name="Mgr Lead",
            source=self.source,
            assigned_to=self.employee,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        q = QuotationService.create_quotation(
            user=self.employee,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.employee, quotation=q)
        QuotationService.send_quotation(user=self.employee, quotation=q)
        resp = self.mgr_client.post(
            f"/api/crm/quotations/{q.id}/reject/",
            {
                "rejection_reason": "Too high",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_manager_can_accept_quotation(self):
        lead = CRMService.create_lead(
            user=self.employee,
            name="Mgr Lead",
            source=self.source,
            assigned_to=self.employee,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        q = QuotationService.create_quotation(
            user=self.employee,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.employee, quotation=q)
        QuotationService.send_quotation(user=self.employee, quotation=q)
        resp = self.mgr_client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_manager_can_view_audit_logs(self):
        resp = self.mgr_client.get("/api/crm/audit-logs/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_employee_cannot_view_audit_logs(self):
        resp = self.emp_client.get("/api/crm/audit-logs/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_self_approval_prevented(self):
        from rest_framework.exceptions import PermissionDenied

        pl, st = self._create_approval_pipeline("Self Appr")
        lead = CRMService.create_lead(
            user=self.user,
            name="Self Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(user=self.user, lead=lead)
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        with self.assertRaises((ValidationError, PermissionDenied)):
            QuotationService.approve_quotation(reviewer_user=self.user, quotation=q)

    def test_self_approval_via_api_returns_403(self):
        pl, st = self._create_approval_pipeline("Self Appr API")
        lead = CRMService.create_lead(
            user=self.user,
            name="Self Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(user=self.user, lead=lead)
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        resp = self.client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("submitting agent cannot approve", resp.data["detail"])

    def test_manager_approves_then_submitter_can_send(self):
        pl, st = self._create_approval_pipeline("Mgr Approve Send")
        lead = CRMService.create_lead(
            user=self.employee,
            name="Emp Lead",
            source=self.source,
            assigned_to=self.employee,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(user=self.employee, lead=lead)
        self.emp_client.post(f"/api/crm/quotations/{q.id}/submit/")
        self.mgr_client.post(f"/api/crm/quotations/{q.id}/approve/")
        resp = self.emp_client.post(f"/api/crm/quotations/{q.id}/send/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_employee_submits_manager_approves_full_cycle(self):
        pl, st = self._create_approval_pipeline("Full Cycle")
        lead = CRMService.create_lead(
            user=self.employee,
            name="FC Lead",
            source=self.source,
            assigned_to=self.employee,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.employee,
            lead=lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 800}],
        )
        self.emp_client.post(f"/api/crm/quotations/{q.id}/submit/")
        self.mgr_client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.emp_client.post(f"/api/crm/quotations/{q.id}/send/")
        resp = self.mgr_client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_dynamic_permission_revocation_blocks_approval(self):
        lead = CRMService.create_lead(
            user=self.employee,
            name="Dyn Lead",
            source=self.source,
            assigned_to=self.employee,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        q = QuotationService.create_quotation(
            user=self.employee,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        self.emp_client.post(f"/api/crm/quotations/{q.id}/submit/")
        self.mgr_client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.emp_client.post(f"/api/crm/quotations/{q.id}/send/")

        # Revoke approve permission
        self.mgr_role.permissions.remove(
            Permission.objects.get(codename="approve_quotation"),
        )

        q2 = QuotationService.create_quotation(
            user=self.employee,
            lead=lead,
            line_items=[{"description": "Y", "quantity": 1, "unit_price": 200}],
        )
        self.emp_client.post(f"/api/crm/quotations/{q2.id}/submit/")
        resp = self.mgr_client.post(f"/api/crm/quotations/{q2.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_rbac_case_employee_cannot_approve(self):
        """Employee without approve_quotation cannot approve."""
        resp = self.emp_client.post(
            "/api/crm/quotations/00000000-0000-0000-0000-000000000099/approve/",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_rbac_case_manager_without_own_permission_cannot_self_approve(self):
        """Manager without approve_own_quotation cannot approve own quotation."""
        mgr_c, mgr_u, _ = self._create_manager_client(
            permissions=[
                "view_quotation",
                "add_quotation",
                "submit_quotation",
                "approve_quotation",
            ],
            username="mno",
        )
        pl, st = self._create_approval_pipeline("MgrNoOwn Pipeline")
        lead = CRMService.create_lead(
            user=mgr_u,
            name="MgrNoOwn Lead",
            source=self.source,
            assigned_to=mgr_u,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(user=mgr_u, lead=lead)
        QuotationService.submit_quotation_for_approval(user=mgr_u, quotation=q)
        resp = mgr_c.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_rbac_case_manager_with_own_permission_can_self_approve(self):
        """Manager with approve_own_quotation can approve own quotation."""
        mgr_c, mgr_u, _ = self._create_manager_client(
            permissions=[
                "view_quotation",
                "add_quotation",
                "submit_quotation",
                "approve_quotation",
                "approve_own_quotation",
            ],
            username="mgr_own",
        )
        pl, st = self._create_approval_pipeline("MgrOwn Pipeline")
        lead = CRMService.create_lead(
            user=mgr_u,
            name="MgrOwn Lead",
            source=self.source,
            assigned_to=mgr_u,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(user=mgr_u, lead=lead)
        QuotationService.submit_quotation_for_approval(user=mgr_u, quotation=q)
        resp = mgr_c.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_rbac_case_manager_approves_other_users_quotation(self):
        """Manager can approve another user's quotation (not self)."""
        pl, st = self._create_approval_pipeline("MgrOther Pipeline")
        lead = CRMService.create_lead(
            user=self.employee,
            name="MgrOther Lead",
            source=self.source,
            assigned_to=self.employee,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(user=self.employee, lead=lead)
        QuotationService.submit_quotation_for_approval(user=self.employee, quotation=q)
        resp = self.mgr_client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_rbac_case_admin_approves_quotaion(self):
        """Admin (full-permission user) can approve any quotation."""
        pl, st = self._create_approval_pipeline("Admin Pipeline")
        lead = CRMService.create_lead(
            user=self.employee,
            name="Admin Lead",
            source=self.source,
            assigned_to=self.employee,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(user=self.employee, lead=lead)
        QuotationService.submit_quotation_for_approval(user=self.employee, quotation=q)
        resp = self.client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_superadmin_can_self_approve(self):
        """Superuser can self-approve their own quotation."""
        su = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.com",
            password="Password123!",
            phone_number="5555556666",
        )
        pl, st = self._create_approval_pipeline("SU Pipeline")
        lead = CRMService.create_lead(
            user=su,
            name="SU Lead",
            source=self.source,
            assigned_to=su,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(user=su, lead=lead)
        QuotationService.submit_quotation_for_approval(user=su, quotation=q)
        su_client = APIClient()
        su_client.force_authenticate(user=su)
        resp = su_client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_approval_persistence_records_submitted_by_and_reviewed_by(self):
        pl, st = self._create_approval_pipeline("Persist Pipeline")
        lead = CRMService.create_lead(
            user=self.user,
            name="Persist Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(user=self.user, lead=lead)
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        approval = QuotationApproval.objects.filter(
            version=q.current_version,
            decision="PENDING",
        ).first()
        self.assertEqual(approval.submitted_by, self.user)
        self.assertIsNone(approval.reviewed_by)

        mgr_client, mgr_user, _ = self._create_manager_client(username="pmgr")
        mgr_client.post(f"/api/crm/quotations/{q.id}/approve/")
        approval.refresh_from_db()
        self.assertEqual(approval.submitted_by, self.user)
        self.assertEqual(approval.reviewed_by, mgr_user)
        self.assertEqual(approval.decision, "APPROVED")

    def test_employee_full_quotation_permission_matrix(self):
        """Employee can: create/view/submit/send/edit drafts. Cannot: approve/reject/accept/delete."""
        pl, st = self._create_approval_pipeline("Matrix Pipeline")
        lead = CRMService.create_lead(
            user=self.employee,
            name="Matrix Lead",
            source=self.source,
            assigned_to=self.employee,
            pipeline=pl,
            current_stage=st,
        )
        resp = self.emp_client.post(
            "/api/crm/quotations/",
            {
                "lead": str(lead.id),
                "terms": "Emp Terms",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        qid = resp.data["id"]

        self.assertEqual(
            self.emp_client.get("/api/crm/quotations/").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.emp_client.get(f"/api/crm/quotations/{qid}/").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.emp_client.patch(
                f"/api/crm/quotations/{qid}/update-draft/",
                {"terms": "Updated"},
            ).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.emp_client.post(f"/api/crm/quotations/{qid}/submit/").status_code,
            status.HTTP_200_OK,
        )

        # Denied actions
        self.assertEqual(
            self.emp_client.post(f"/api/crm/quotations/{qid}/approve/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.emp_client.post(
                f"/api/crm/quotations/{qid}/reject-approval/"
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.emp_client.post(f"/api/crm/quotations/{qid}/accept/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.emp_client.post(
                f"/api/crm/quotations/{qid}/reject/",
                {"rejection_reason": "x"},
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.emp_client.delete(f"/api/crm/quotations/{qid}/").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_unauthenticated_access_rejected_for_all_endpoints(self):
        unauth = APIClient()
        endpoints = [
            ("/api/crm/leads/", "GET"),
            ("/api/crm/leads/", "POST"),
            ("/api/crm/quotations/", "GET"),
            ("/api/crm/quotations/", "POST"),
            ("/api/crm/customers/", "GET"),
            ("/api/crm/activities/", "GET"),
            ("/api/crm/audit-logs/", "GET"),
        ]
        for url, method in endpoints:
            resp = unauth.get(url) if method == "GET" else unauth.post(url, {})
            self.assertIn(
                resp.status_code,
                [
                    status.HTTP_401_UNAUTHORIZED,
                    status.HTTP_403_FORBIDDEN,
                ],
                f"Unauth {method} {url} should be rejected",
            )


# ==============================================================================
# SECTION 10: AUDIT LOG TESTS
# ==============================================================================


class AuditLogTests(CRMBaseTestCase):
    """Tests verifying audit logs are created for every CRM operation."""

    def test_lead_source_creation_logged(self):
        source = CRMService.create_lead_source(
            user=self.user,
            name="Audit Source",
            description="For audit",
        )
        log = AuditLog.objects.filter(
            entity_type="LeadSource",
            entity_id=source.id,
            action="LEAD_SOURCE_CREATED",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.new_value["name"], "Audit Source")

    def test_pipeline_creation_logged(self):
        pipeline = CRMService.create_pipeline(
            user=self.user,
            name="Audit Pipeline",
            description="For audit",
        )
        log = AuditLog.objects.filter(
            entity_type="Pipeline",
            entity_id=pipeline.id,
            action="PIPELINE_CREATED",
        ).first()
        self.assertIsNotNone(log)

    def test_pipeline_stage_creation_logged(self):
        stage = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=self.pipeline,
            name="Audit Stage",
            display_order=20,
        )
        log = AuditLog.objects.filter(
            entity_type="PipelineStage",
            entity_id=stage.id,
            action="PIPELINE_STAGE_CREATED",
        ).first()
        self.assertIsNotNone(log)

    def test_lead_creation_logged(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Audit Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        log = AuditLog.objects.filter(
            entity_type="Lead",
            entity_id=lead.id,
            action="LEAD_CREATED",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.new_value["name"], "Audit Lead")
        self.assertEqual(log.user, self.user)

    def test_lead_assignment_logged(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Assign Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        new_user = User.objects.create_user(
            username="assign_target",
            email="assign@x.com",
            password="Password123!",
            role=self.role,
        )
        CRMService.assign_lead(user=self.user, lead=lead, new_assignee=new_user)
        log = AuditLog.objects.filter(
            entity_type="Lead",
            entity_id=lead.id,
            action="LEAD_ASSIGNED",
        ).first()
        self.assertIsNotNone(log)
        self.assertIn("assigned_to", log.old_value)
        self.assertIn("assigned_to", log.new_value)

    def test_lead_stage_change_logged(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Stage Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        CRMService.progress_lead(user=self.user, lead=lead, stage_id=self.stage2.id)
        log = AuditLog.objects.filter(
            entity_type="Lead",
            entity_id=lead.id,
            action="STAGE_CHANGED",
        ).first()
        self.assertIsNotNone(log)

    def test_lead_conversion_logged(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Conv Lead",
            email="convlog@x.com",
            phone="3232323232",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        CRMService.convert_lead(
            user=self.user,
            lead=lead,
            name="Conv Cust",
            email="convlog@x.com",
            phone="3232323232",
        )
        log = AuditLog.objects.filter(
            entity_type="Lead",
            entity_id=lead.id,
            action="LEAD_CONVERTED",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.new_value["status"], Lead.Status.CONVERTED)

    def test_quotation_full_lifecycle_logged(self):
        pl, st = self._create_approval_pipeline("Lifecycle Audit Pipeline")
        lead = CRMService.create_lead(
            user=self.user,
            name="Lifecycle Lead",
            email="lc@x.com",
            phone="3333333333",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        self.assertIsNotNone(
            AuditLog.objects.filter(
                entity_type="Quotation",
                entity_id=q.id,
                action="QUOTATION_CREATED",
            ).first(),
            "QUOTATION_CREATED audit should exist",
        )

        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertEqual(q.status, "PENDING_APPROVAL")
        self.assertIsNotNone(
            AuditLog.objects.filter(
                entity_type="Quotation",
                entity_id=q.id,
                action="QUOTATION_SUBMITTED",
            ).first(),
            "QUOTATION_SUBMITTED audit should exist",
        )

        mgr = User.objects.create_user(
            username="lc_mgr",
            email="lc_mgr@x.com",
            password="Password123!",
            role=self.role,
        )
        QuotationService.approve_quotation(reviewer_user=mgr, quotation=q)
        q.refresh_from_db()
        self.assertIsNotNone(
            AuditLog.objects.filter(
                entity_type="Quotation",
                entity_id=q.id,
                action="QUOTATION_APPROVED",
            ).first(),
            "QUOTATION_APPROVED audit should exist",
        )

        QuotationService.send_quotation(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertIsNotNone(
            AuditLog.objects.filter(
                entity_type="Quotation",
                entity_id=q.id,
                action="QUOTATION_SENT",
            ).first(),
            "QUOTATION_SENT audit should exist",
        )

        QuotationService.accept_quotation(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertIsNotNone(
            AuditLog.objects.filter(
                entity_type="Quotation",
                entity_id=q.id,
                action="QUOTATION_ACCEPTED",
            ).first(),
            "QUOTATION_ACCEPTED audit should exist",
        )

    def test_quotation_rejection_logged(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Reject Lead",
            email="rej@x.com",
            phone="3434343434",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        q.refresh_from_db()
        QuotationService.reject_quotation(
            user=self.user,
            quotation=q,
            rejection_reason="Too expensive",
        )
        log = AuditLog.objects.filter(
            entity_type="Quotation",
            entity_id=q.id,
            action="QUOTATION_REJECTED",
        ).first()
        self.assertIsNotNone(log)
        self.assertIn("Too expensive", log.new_value["rejection_reason"])

    def test_quotation_revision_logged(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Rev Lead",
            email="revlog@x.com",
            phone="3535353535",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        QuotationService.create_revision(
            user=self.user,
            quotation=q,
            revision_reason="Client feedback",
        )
        log = AuditLog.objects.filter(
            entity_type="Quotation",
            entity_id=q.id,
            action="QUOTATION_VERSION_CREATED",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.new_value["version"], 2)

    def test_audit_logs_listed_via_api(self):
        CRMService.create_lead(
            user=self.user,
            name="List Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        response = self.client.get("/api/crm/audit-logs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)


# ==============================================================================
# SECTION 11: END-TO-END BUSINESS SCENARIOS
# ==============================================================================


class EndToEndScenarioTests(CRMBaseTestCase):
    """Real-world business scenario tests covering realistic CRM workflows."""

    def test_startup_solo_salesperson_full_cycle(self):
        solo_client, solo, _ = self._create_manager_client(
            permissions=[
                "view_lead",
                "add_lead",
                "change_lead",
                "view_quotation",
                "add_quotation",
                "change_quotation",
                "submit_quotation",
                "approve_quotation",
                "approve_own_quotation",
                "send_quotation",
                "accept_quotation",
                "reject_quotation",
                "request_quotation_revision",
                "generate_quotation_pdf",
                "view_customer",
                "add_customer",
                "view_activity",
                "add_activity",
                "manage_lead_source",
                "manage_pipeline",
                "manage_pipeline_stage",
            ],
            username="solo_sales",
            rolename="SoloSales",
        )
        pipeline = CRMService.create_pipeline(user=solo, name="Startup Pipeline")
        stage = CRMService.create_pipeline_stage(
            user=solo,
            pipeline=pipeline,
            name="Demo Stage",
            display_order=1,
            requires_quotation=True,
            quotation_approval_required=True,
        )
        lead = CRMService.create_lead(
            user=solo,
            name="Startup Prospect",
            email="startup@x.com",
            phone="4100000001",
            source=self.source,
            assigned_to=solo,
            pipeline=pipeline,
            current_stage=stage,
        )
        q = QuotationService.create_quotation(
            user=solo,
            lead=lead,
            line_items=[
                {"description": "Setup Fee", "quantity": 1, "unit_price": 500},
                {"description": "Monthly License", "quantity": 12, "unit_price": 100},
            ],
        )
        solo_client.post(f"/api/crm/quotations/{q.id}/submit/")
        solo_client.post(f"/api/crm/quotations/{q.id}/approve/")
        solo_client.post(f"/api/crm/quotations/{q.id}/send/")
        resp = solo_client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.Status.CONVERTED)
        self.assertTrue(Customer.objects.filter(lead=lead).exists())

    def test_enterprise_pipeline_with_revision_and_discount(self):
        pipeline = CRMService.create_pipeline(
            user=self.user, name="Enterprise Pipeline"
        )
        stage1 = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pipeline,
            name="Qualification",
            display_order=1,
            requires_quotation=True,
            quotation_approval_required=True,
        )
        lead = CRMService.create_lead(
            user=self.user,
            name="Enterprise Client",
            email="enterprise@x.com",
            phone="4200000001",
            source=self.source,
            assigned_to=self.user,
            pipeline=pipeline,
            current_stage=stage1,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            terms="Enterprise License",
            line_items=[
                {"description": "Enterprise Suite", "quantity": 1, "unit_price": 10000},
                {"description": "Implementation", "quantity": 1, "unit_price": 5000},
                {"description": "Training", "quantity": 3, "unit_price": 1000},
            ],
        )
        mgr_user = User.objects.create_user(
            username="ent_mgr",
            email="ent_mgr@x.com",
            password="Password123!",
            phone_number="4200000002",
            role=self.role,
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.approve_quotation(reviewer_user=mgr_user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertEqual(q.status, "SENT")
        self.assertEqual(q.current_version.total_amount, Decimal("18000.00"))

        # Revision with volume discount
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/revision/",
            {
                "revision_reason": "Volume discount",
                "terms": "Enterprise - Discounted",
                "line_items": [
                    {
                        "description": "Enterprise Suite",
                        "quantity": 1,
                        "unit_price": 8500,
                    },
                    {
                        "description": "Implementation",
                        "quantity": 1,
                        "unit_price": 5000,
                    },
                    {"description": "Training", "quantity": 3, "unit_price": 1000},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        q.refresh_from_db()
        self.assertEqual(q.current_version.version_number, 2)
        self.assertEqual(q.current_version.total_amount, Decimal("16500.00"))

        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.approve_quotation(reviewer_user=mgr_user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        q.refresh_from_db()
        QuotationService.accept_quotation(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertEqual(q.status, "ACCEPTED")
        self.assertEqual(q.accepted_version.version_number, 2)

    def test_lost_lead_reengagement_then_conversion(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Reengage Prospect",
            email="reengage@x.com",
            phone="4300000001",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        CRMService.mark_lead_lost(
            user=self.user,
            lead=lead,
            lost_reason="Budget constraints",
        )
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.Status.LOST)

        CRMService.reengage_lead(user=self.user, lead=lead)
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.Status.ACTIVE)
        self.assertIsNone(lead.lost_reason)

        CRMService.convert_lead(
            user=self.user,
            lead=lead,
            name="Reengage Customer",
            email="reengage@x.com",
            phone="4300000001",
        )
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.Status.CONVERTED)

    def test_quotation_email_with_custom_subject_and_body(self):
        from django.core import mail

        lead = CRMService.create_lead(
            user=self.user,
            name="Email Lead",
            email="emaillead@x.com",
            phone="4400000001",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "Service", "quantity": 1, "unit_price": 750}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertEqual(q.status, "APPROVED")

        mail.outbox = []
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/send-email/",
            {
                "recipient_email": "emaillead@x.com",
                "subject": "Custom Subject: Q4 Proposal",
                "body": "Dear Partner, please review our Q4 proposal.",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Custom Subject: Q4 Proposal")
        self.assertIn("Q4 proposal", mail.outbox[0].body)

    def test_pdf_for_specific_version_in_multi_version(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="PDF Ver Lead",
            email="pdfver@x.com",
            phone="4500000001",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "V1", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)

        QuotationService.create_revision(
            user=self.user,
            quotation=q,
            revision_reason="Updated pricing",
            line_items=[{"description": "V2", "quantity": 2, "unit_price": 150}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        resp = self.client.get(f"/api/crm/quotations/{q.id}/pdf/?version=1")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn(f"{q.quotation_number}_v1.pdf", resp["Content-Disposition"])

    def test_multiple_quotations_for_same_lead(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Multi Lead",
            email="multi@x.com",
            phone="4600000001",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        q1 = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[
                {"description": "Proposal A", "quantity": 1, "unit_price": 500}
            ],
        )
        q2 = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[
                {"description": "Proposal B", "quantity": 1, "unit_price": 800}
            ],
        )
        self.assertNotEqual(q1.id, q2.id)
        self.assertNotEqual(q1.quotation_number, q2.quotation_number)
        resp = self.client.get(f"/api/crm/quotations/?lead={lead.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_full_workflow_with_email_and_acceptance(self):
        from django.core import mail

        lead = CRMService.create_lead(
            user=self.user,
            name="Full WF Lead",
            email="fullwf@x.com",
            phone="4900000001",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            terms="Net 30",
            notes="Standard terms",
            line_items=[
                {"description": "Product", "quantity": 5, "unit_price": 200},
                {"description": "Installation", "quantity": 1, "unit_price": 500},
            ],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertEqual(q.status, "APPROVED")

        mail.outbox = []
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/send-email/",
            {
                "recipient_email": "fullwf@x.com",
                "subject": "Your Proposal",
                "body": "Please find attached our proposal.",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].attachments), 1)

        resp = self.client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        q.refresh_from_db()
        self.assertEqual(q.status, "ACCEPTED")
        self.assertIsNotNone(q.customer)
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.Status.CONVERTED)


# ==============================================================================
# SECTION 12: PERFORMANCE TESTS
# ==============================================================================


class PerformanceTests(CRMBaseTestCase):
    """Tests for query count and performance bounds."""

    def test_quotation_list_query_count_bounded(self):
        pipeline_perf = CRMService.create_pipeline(user=self.user, name="Perf Pipeline")
        stage_perf = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pipeline_perf,
            name="Perf Stage",
            display_order=1,
        )
        for i in range(15):
            lead = CRMService.create_lead(
                user=self.user,
                name=f"Perf Lead {i}",
                email=f"perf{i}@x.com",
                phone=f"555000{i:04d}",
                source=self.source,
                assigned_to=self.user,
                pipeline=pipeline_perf,
                current_stage=stage_perf,
            )
            QuotationService.create_quotation(
                user=self.user,
                lead=lead,
                line_items=[
                    {"description": f"Item A {i}", "quantity": 2, "unit_price": 500},
                    {"description": f"Item B {i}", "quantity": 1, "unit_price": 1500},
                ],
            )
        with self.assertNumQueries(7):
            resp = self.client.get("/api/crm/quotations/")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            self.assertGreaterEqual(len(resp.data), 15)


# ==============================================================================
# SECTION 13: MODEL CLEAN() AND __STR__ COVERAGE
# ==============================================================================


class ModelCleanAndStrTests(CRMBaseTestCase):
    """Direct model-level clean() and __str__() coverage."""

    def test_lead_clean_valid(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Clean Lead",
            email="clean@x.com",
            phone="1111111111",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        lead.full_clean()

    def test_lead_clean_wrong_stage_pipeline(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Mismatch Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        lead.current_stage = self.stage2_p2
        with self.assertRaises(ValidationError):
            lead.full_clean()

    def test_lead_clean_lost_without_reason(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="LostNoReason",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        lead.status = Lead.Status.LOST
        lead.lost_at = timezone.now()
        with self.assertRaises(ValidationError):
            lead.full_clean()

    def test_lead_clean_lost_without_timestamp(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="LostNoTS",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        lead.status = Lead.Status.LOST
        lead.lost_reason = "Budget"
        with self.assertRaises(ValidationError):
            lead.full_clean()

    def test_lead_clean_active_with_lost_reason(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="ActiveLostReason",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        lead.lost_reason = "should not be set"
        with self.assertRaises(ValidationError):
            lead.full_clean()

    def test_lead_clean_active_with_lost_at(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="ActiveLostAt",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        lead.lost_at = timezone.now()
        with self.assertRaises(ValidationError):
            lead.full_clean()

    def test_lead_clean_lost_with_both(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="LostBoth",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        lead.status = Lead.Status.LOST
        lead.lost_reason = "Budget"
        lead.lost_at = timezone.now()
        lead.full_clean()

    def test_lead_str(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Str Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        self.assertEqual(str(lead), "Str Lead")

    def test_leadsource_str(self):
        self.assertEqual(str(self.source), "Web Search")

    def test_pipeline_str(self):
        self.assertEqual(str(self.pipeline), "Sales Pipeline")

    def test_pipelinestage_str(self):
        self.assertEqual(str(self.stage1), "Sales Pipeline - Stage 1")

    def test_customer_str(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="CustStr",
            email="custstr@x.com",
            phone="1111111111",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        cust = CRMService.convert_lead(
            user=self.user,
            lead=lead,
            name="CustStr Customer",
            email="custstr@x.com",
            phone="1111111111",
        )
        self.assertEqual(str(cust), "CustStr Customer")

    def test_activity_clean_no_lead_no_customer(self):
        act = Activity(
            created_by=self.user,
            activity_type="CALL",
            outcome="test",
        )
        with self.assertRaises(ValidationError):
            act.full_clean()

    def test_activity_clean_both_lead_and_customer(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Both Lead",
            email="bothclean@x.com",
            phone="1111111111",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        cust = CRMService.convert_lead(
            user=self.user,
            lead=lead,
            name="Both Cust",
            email="bothclean@x.com",
            phone="1111111111",
        )
        act = Activity(
            lead=lead,
            customer=cust,
            created_by=self.user,
            activity_type="CALL",
            outcome="test",
        )
        with self.assertRaises(ValidationError):
            act.full_clean()

    def test_activity_clean_follow_up_required_no_date(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="FU Lead",
            email="fuclean@x.com",
            phone="1111111111",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        act = Activity(
            lead=lead,
            created_by=self.user,
            activity_type="CALL",
            outcome="test",
            follow_up_required=True,
        )
        with self.assertRaises(ValidationError):
            act.full_clean()

    def test_activity_clean_follow_up_date_without_flag(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="FUD Lead",
            email="fudclean@x.com",
            phone="1111111111",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        act = Activity(
            lead=lead,
            created_by=self.user,
            activity_type="CALL",
            outcome="test",
            follow_up_date=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            act.full_clean()

    def test_activity_str(self):
        act = Activity(
            created_by=self.user,
            activity_type="CALL",
            outcome="Initial call",
        )
        self.assertEqual(str(act), "CALL - Initial call")

    def test_auditlog_str(self):
        log = AuditLog(
            user=self.user,
            entity_type="Lead",
            entity_id=uuid4(),
            action="LEAD_CREATED",
        )
        self.assertEqual(str(log), "LEAD_CREATED - Lead")

    def test_quotation_str(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="QStr Lead",
            email="qstr@x.com",
            phone="1111111111",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        self.assertEqual(str(q), q.quotation_number)

    def test_quotationversion_str(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="QVStr Lead",
            email="qvstr@x.com",
            phone="1111111111",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        v = q.current_version
        self.assertIn("v1", str(v))

    def test_quotationlineitem_amount_and_str(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="QLI Lead",
            email="qli@x.com",
            phone="1111111111",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[
                {"description": "Test Item", "quantity": 3, "unit_price": "25.00"}
            ],
        )
        li = q.current_version.line_items.first()
        self.assertEqual(li.amount, Decimal("75.00"))
        self.assertEqual(str(li), "Test Item")

    def test_quotationapproval_str(self):
        pl, st = self._create_approval_pipeline("ApprStr Pipeline")
        lead = CRMService.create_lead(
            user=self.user,
            name="ApprStr Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(user=self.user, lead=lead)
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        approval = QuotationApproval.objects.filter(
            version=q.current_version,
        ).first()
        self.assertIn("PENDING", str(approval))

    def test_quotationintegrationevent_str(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="QIE Lead",
            email="qie@x.com",
            phone="1111111111",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        q = QuotationService.create_quotation(user=self.user, lead=lead)
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        event = QuotationIntegrationEvent.objects.filter(quotation=q).first()
        self.assertIn("quotation.followup_required", str(event))


# ==============================================================================
# SECTION 14: SERVICES EDGE CASES (JSON STRING PARSING, ERROR PATHS)
# ==============================================================================


class ServiceEdgeCaseTests(CRMBaseTestCase):
    """Tests for services.py edge cases: JSON string line_items, error paths, etc."""

    def setUp(self):
        super().setUp()
        self.lead = CRMService.create_lead(
            user=self.user,
            name="Edge Lead",
            email="edge@x.com",
            phone="5550000001",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )

    def test_create_quotation_with_json_string_line_items(self):
        import json

        items = json.dumps(
            [
                {"description": "JSON Item", "quantity": 2, "unit_price": "50.00"},
            ]
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=items,
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.line_items.count(), 1)
        self.assertEqual(q.current_version.total_amount, Decimal("100.00"))

    def test_create_quotation_with_invalid_json_string_line_items(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items="not json at all",
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.total_amount, Decimal("0.00"))

    def test_create_quotation_with_string_items_in_list(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=["invalid_item", 123],
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.total_amount, Decimal("0.00"))

    def test_create_quotation_line_item_with_zero_quantity(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Zero", "quantity": 0, "unit_price": "100.00"}],
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.total_amount, Decimal("0.00"))

    def test_create_quotation_with_default_quantity_and_price(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Defaults"}],
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.line_items.first().quantity, 1)
        self.assertEqual(q.current_version.total_amount, Decimal("0.00"))

    def test_update_draft_with_json_string_line_items(self):
        import json

        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Original", "quantity": 1, "unit_price": 50}],
        )
        items = json.dumps(
            [
                {"description": "Updated", "quantity": 3, "unit_price": "25.00"},
            ]
        )
        q = QuotationService.update_draft_quotation(
            user=self.user,
            quotation=q,
            line_items=items,
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.total_amount, Decimal("75.00"))

    def test_update_draft_with_invalid_json_string(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Original", "quantity": 1, "unit_price": 50}],
        )
        q = QuotationService.update_draft_quotation(
            user=self.user,
            quotation=q,
            line_items="invalid json",
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.line_items.count(), 0)

    def test_update_draft_with_string_items_in_list(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Original", "quantity": 1, "unit_price": 50}],
        )
        q = QuotationService.update_draft_quotation(
            user=self.user,
            quotation=q,
            line_items=["bad", 123],
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.line_items.count(), 0)

    def test_update_draft_only_terms(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "A", "quantity": 1, "unit_price": 100}],
        )
        q = QuotationService.update_draft_quotation(
            user=self.user,
            quotation=q,
            terms="New terms only",
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.terms, "New terms only")
        self.assertEqual(q.current_version.line_items.count(), 1)

    def test_update_draft_only_notes(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "A", "quantity": 1, "unit_price": 100}],
        )
        q = QuotationService.update_draft_quotation(
            user=self.user,
            quotation=q,
            notes="Some notes",
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.notes, "Some notes")

    def test_revision_with_json_string_line_items(self):
        import json

        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "V1", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        items = json.dumps(
            [
                {"description": "V2", "quantity": 2, "unit_price": "75.00"},
            ]
        )
        q = QuotationService.create_revision(
            user=self.user,
            quotation=q,
            line_items=items,
            revision_reason="JSON update",
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.version_number, 2)
        self.assertEqual(q.current_version.total_amount, Decimal("150.00"))

    def test_revision_with_invalid_json_string(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "V1", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        q = QuotationService.create_revision(
            user=self.user,
            quotation=q,
            line_items="not json",
            revision_reason="Bad JSON",
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.total_amount, Decimal("0.00"))

    def test_revision_with_string_items_in_list(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "V1", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        q = QuotationService.create_revision(
            user=self.user,
            quotation=q,
            line_items=["bad", 123],
            revision_reason="String items",
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.total_amount, Decimal("0.00"))

    def test_revision_without_line_items_copies_from_previous(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Original", "quantity": 2, "unit_price": 50}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        q = QuotationService.create_revision(
            user=self.user,
            quotation=q,
            revision_reason="Copy",
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.version_number, 2)
        self.assertEqual(q.current_version.line_items.count(), 1)
        self.assertEqual(q.current_version.total_amount, Decimal("100.00"))

    def test_revision_without_line_items_or_notes_copies_terms_and_notes(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            terms="Original Terms",
            notes="Original Notes",
            line_items=[{"description": "A", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        q = QuotationService.create_revision(
            user=self.user,
            quotation=q,
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.terms, "Original Terms")
        self.assertEqual(q.current_version.notes, "Original Notes")

    def test_revision_from_approved_status(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "A", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertEqual(q.status, "APPROVED")
        q = QuotationService.create_revision(
            user=self.user,
            quotation=q,
            line_items=[{"description": "Rev", "quantity": 1, "unit_price": 90}],
            revision_reason="From approved",
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.version_number, 2)

    def test_revision_from_draft_status(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "A", "quantity": 1, "unit_price": 100}],
        )
        q = QuotationService.create_revision(
            user=self.user,
            quotation=q,
            line_items=[{"description": "Draft Rev", "quantity": 1, "unit_price": 80}],
            revision_reason="From draft",
        )
        q.refresh_from_db()
        self.assertEqual(q.current_version.version_number, 2)

    def test_revision_invalid_status_rejected(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "A", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        QuotationService.accept_quotation(user=self.user, quotation=q)
        with self.assertRaises(ValidationError):
            QuotationService.create_revision(
                user=self.user,
                quotation=q,
                revision_reason="Should fail",
            )

    def test_revision_no_version_rejected(self):
        q = Quotation.objects.create(
            quotation_number="TEST-NO-VER",
            lead=self.lead,
            created_by=self.user,
            status="DRAFT",
        )
        with self.assertRaises(ValidationError):
            QuotationService.create_revision(
                user=self.user,
                quotation=q,
                revision_reason="No version",
            )

    def test_create_quotation_no_active_stages_rejected(self):
        pl = CRMService.create_pipeline(user=self.user, name="No Stage Pipeline")
        self.stage1.is_active = False
        self.stage1.save()
        with self.assertRaises(ValidationError):
            CRMService.create_lead(
                user=self.user,
                name="Should fail",
                source=self.source,
                assigned_to=self.user,
                pipeline=pl,
                current_stage=self.stage1,
            )
        self.stage1.is_active = True
        self.stage1.save()

    def test_create_lead_not_first_stage_rejected(self):
        with self.assertRaises(ValidationError):
            CRMService.create_lead(
                user=self.user,
                name="Not First",
                source=self.source,
                assigned_to=self.user,
                pipeline=self.pipeline,
                current_stage=self.stage2,
            )

    def test_assign_lead_same_user_no_change(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Same Assign",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        result = CRMService.assign_lead(
            user=self.user,
            lead=lead,
            new_assignee=self.user,
        )
        self.assertEqual(result.assigned_to, self.user)

    def test_progress_lead_no_next_stage_rejected(self):
        pl = CRMService.create_pipeline(user=self.user, name="Single Stage Pipeline")
        st = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pl,
            name="Only Stage",
            display_order=1,
        )
        lead = CRMService.create_lead(
            user=self.user,
            name="Last Stage",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        with self.assertRaises(ValidationError):
            CRMService.progress_lead(user=self.user, lead=lead)

    def test_progress_lead_inactive_stage_rejected(self):
        with self.assertRaises(ValidationError):
            CRMService.progress_lead(
                user=self.user,
                lead=self.lead,
                stage_id=str(self.inactive_stage.id),
            )

    def test_mark_lead_lost_empty_reason_rejected(self):
        with self.assertRaises(ValidationError):
            CRMService.mark_lead_lost(
                user=self.user,
                lead=self.lead,
                lost_reason="",
            )

    def test_mark_lead_lost_already_lost_rejected(self):
        CRMService.mark_lead_lost(
            user=self.user,
            lead=self.lead,
            lost_reason="Budget",
        )
        with self.assertRaises(ValidationError):
            CRMService.mark_lead_lost(
                user=self.user,
                lead=self.lead,
                lost_reason="Again",
            )

    def test_reengage_non_lost_lead_rejected(self):
        with self.assertRaises(ValidationError):
            CRMService.reengage_lead(user=self.user, lead=self.lead)

    def test_convert_lead_already_converted_rejected(self):
        CRMService.convert_lead(
            user=self.user,
            lead=self.lead,
            name="Conv",
            email="edge@x.com",
            phone="5550000001",
        )
        with self.assertRaises(ValidationError):
            CRMService.convert_lead(
                user=self.user,
                lead=self.lead,
                name="Conv2",
                email="edge@x.com",
                phone="5550000001",
            )

    def test_convert_lead_lost_rejected(self):
        CRMService.mark_lead_lost(
            user=self.user,
            lead=self.lead,
            lost_reason="Budget",
        )
        with self.assertRaises(ValidationError):
            CRMService.convert_lead(
                user=self.user,
                lead=self.lead,
                name="X",
                email="edge@x.com",
                phone="5550000001",
            )

    def test_convert_lead_duplicate_email_rejected(self):
        CRMService.convert_lead(
            user=self.user,
            lead=self.lead,
            name="First",
            email="edge@x.com",
            phone="5550000001",
        )
        lead2 = CRMService.create_lead(
            user=self.user,
            name="Lead2",
            email="lead2@x.com",
            phone="5550000002",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        with self.assertRaises(ValidationError):
            CRMService.convert_lead(
                user=self.user,
                lead=lead2,
                name="Second",
                email="edge@x.com",
                phone="5550000002",
            )

    def test_convert_lead_with_accepted_quotation(self):
        pl, st = self._create_approval_pipeline("ConvQ Pipeline")
        lead = CRMService.create_lead(
            user=self.user,
            name="ConvQ Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        mgr_client, mgr_user, _ = self._create_manager_client(username="convq_mgr")
        QuotationService.approve_quotation(reviewer_user=mgr_user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        QuotationService.accept_quotation(user=self.user, quotation=q)
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.Status.CONVERTED)

    def test_convert_lead_quotation_required_but_not_accepted_rejected(self):
        pl, st = self._create_approval_pipeline("ConvQReq Pipeline")
        lead = CRMService.create_lead(
            user=self.user,
            name="ConvQReq Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(user=self.user, lead=lead)
        with self.assertRaises(ValidationError):
            CRMService.convert_lead(
                user=self.user,
                lead=lead,
                name="X",
                email="convqreq@x.com",
                phone="5550000003",
            )

    def test_create_activity_follow_up_date_without_flag(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="FUActivity",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        with self.assertRaises(ValidationError):
            CRMService.create_activity(
                user=self.user,
                activity_type="CALL",
                outcome="Test",
                lead=lead,
                follow_up_date=timezone.now(),
            )

    def test_create_activity_follow_up_required_no_date(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="FUReqActivity",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        with self.assertRaises(ValidationError):
            CRMService.create_activity(
                user=self.user,
                activity_type="CALL",
                outcome="Test",
                lead=lead,
                follow_up_required=True,
            )

    def test_create_activity_for_converted_lead_rejected(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="ConvAct",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        CRMService.convert_lead(
            user=self.user,
            lead=lead,
            name="ConvActCust",
            email="convact@x.com",
            phone="5550000004",
        )
        with self.assertRaises(ValidationError):
            CRMService.create_activity(
                user=self.user,
                activity_type="CALL",
                outcome="Test",
                lead=lead,
            )

    def test_create_activity_no_lead_no_customer_rejected(self):
        with self.assertRaises(ValidationError):
            CRMService.create_activity(
                user=self.user,
                activity_type="CALL",
                outcome="Test",
            )

    def test_create_activity_both_lead_and_customer_rejected(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="BothAct",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        cust = CRMService.convert_lead(
            user=self.user,
            lead=lead,
            name="BothActCust",
            email="bothact@x.com",
            phone="5550000005",
        )
        with self.assertRaises(ValidationError):
            CRMService.create_activity(
                user=self.user,
                activity_type="CALL",
                outcome="Test",
                lead=lead,
                customer=cust,
            )

    def test_send_quotation_no_version_rejected(self):
        q = Quotation.objects.create(
            quotation_number="TEST-SEND-NOVER",
            lead=self.lead,
            created_by=self.user,
            status="APPROVED",
        )
        with self.assertRaises(ValidationError):
            QuotationService.send_quotation(user=self.user, quotation=q)

    def test_send_quotation_already_sent_rejected(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        with self.assertRaises(ValidationError):
            QuotationService.send_quotation(user=self.user, quotation=q)

    def test_accept_quotation_no_version_rejected(self):
        q = Quotation.objects.create(
            quotation_number="TEST-ACC-NOVER",
            lead=self.lead,
            created_by=self.user,
            status="SENT",
        )
        with self.assertRaises(ValidationError):
            QuotationService.accept_quotation(user=self.user, quotation=q)

    def test_accept_quotation_not_sent_rejected(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        with self.assertRaises(ValidationError):
            QuotationService.accept_quotation(user=self.user, quotation=q)

    def test_reject_quotation_no_version_rejected(self):
        q = Quotation.objects.create(
            quotation_number="TEST-REJ-NOVER",
            lead=self.lead,
            created_by=self.user,
            status="SENT",
        )
        with self.assertRaises(ValidationError):
            QuotationService.reject_quotation(
                user=self.user,
                quotation=q,
                rejection_reason="X",
            )

    def test_reject_quotation_not_sent_rejected(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        with self.assertRaises(ValidationError):
            QuotationService.reject_quotation(
                user=self.user,
                quotation=q,
                rejection_reason="X",
            )

    def test_reject_quotation_no_reason_rejected(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        with self.assertRaises(ValidationError):
            QuotationService.reject_quotation(
                user=self.user,
                quotation=q,
                rejection_reason="",
            )

    def test_reject_quotation_marks_lead_lost(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        QuotationService.reject_quotation(
            user=self.user,
            quotation=q,
            rejection_reason="Too expensive",
        )
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.LOST)

    def test_reject_quotation_lost_lead_no_reject(self):
        CRMService.mark_lead_lost(
            user=self.user,
            lead=self.lead,
            lost_reason="Already lost",
        )
        pl2 = CRMService.create_pipeline(user=self.user, name="RejectLost Pipeline")
        st2 = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pl2,
            name="Stage",
            display_order=1,
        )
        lead2 = CRMService.create_lead(
            user=self.user,
            name="RejectLost2",
            email="rl2@x.com",
            phone="5550000006",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl2,
            current_stage=st2,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead2,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        CRMService.mark_lead_lost(
            user=self.user,
            lead=lead2,
            lost_reason="Other reason",
        )
        q.refresh_from_db()
        QuotationService.reject_quotation(
            user=self.user,
            quotation=q,
            rejection_reason="Too expensive",
        )
        lead2.refresh_from_db()
        self.assertEqual(lead2.status, Lead.Status.LOST)

    def test_submit_quotation_no_version_rejected(self):
        q = Quotation.objects.create(
            quotation_number="TEST-SUB-NOVER",
            lead=self.lead,
            created_by=self.user,
            status="DRAFT",
        )
        with self.assertRaises(ValidationError):
            QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)

    def test_submit_quotation_wrong_status_rejected(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        with self.assertRaises(ValidationError):
            QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)

    def test_approve_quotation_no_version_rejected(self):
        q = Quotation.objects.create(
            quotation_number="TEST-APPR-NOVER",
            lead=self.lead,
            created_by=self.user,
            status="PENDING_APPROVAL",
        )
        with self.assertRaises(ValidationError):
            QuotationService.approve_quotation(
                reviewer_user=self.user,
                quotation=q,
            )

    def test_approve_quotation_wrong_status_rejected(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        with self.assertRaises(ValidationError):
            QuotationService.approve_quotation(
                reviewer_user=self.user,
                quotation=q,
            )

    def test_approve_quotation_no_pending_approval_rejected(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        with self.assertRaises(ValidationError):
            QuotationService.approve_quotation(
                reviewer_user=self.user,
                quotation=q,
            )

    def test_reject_approval_no_version_rejected(self):
        q = Quotation.objects.create(
            quotation_number="TEST-REJAPPR-NOVER",
            lead=self.lead,
            created_by=self.user,
            status="PENDING_APPROVAL",
        )
        with self.assertRaises(ValidationError):
            QuotationService.reject_quotation_approval(
                reviewer_user=self.user,
                quotation=q,
            )

    def test_reject_approval_wrong_status_rejected(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        with self.assertRaises(ValidationError):
            QuotationService.reject_quotation_approval(
                reviewer_user=self.user,
                quotation=q,
            )

    def test_reject_approval_no_pending_approval_rejected(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        with self.assertRaises(ValidationError):
            QuotationService.reject_quotation_approval(
                reviewer_user=self.user,
                quotation=q,
            )

    def test_generate_quotation_number_uniqueness(self):
        nums = set()
        for _ in range(5):
            nums.add(QuotationService.generate_quotation_number())
        self.assertEqual(len(nums), 5)

    def test_submit_auto_approved_when_no_approval_required(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        q = QuotationService.submit_quotation_for_approval(
            user=self.user,
            quotation=q,
        )
        q.refresh_from_db()
        self.assertEqual(q.status, "APPROVED")
        self.assertIsNotNone(q.current_version.approved_at)


# ==============================================================================
# SECTION 15: VIEWS EDGE CASES
# ==============================================================================


class ViewsEdgeCaseTests(CRMBaseTestCase):
    """Tests for views.py edge cases and error handling paths."""

    def setUp(self):
        super().setUp()
        self.lead = CRMService.create_lead(
            user=self.user,
            name="VE Lead",
            email="velead@x.com",
            phone="5550000001",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )

    def test_quotation_create_missing_lead_id(self):
        resp = self.client.post("/api/crm/quotations/", {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quotation_create_nonexistent_lead(self):
        fake = "00000000-0000-0000-0000-000000000099"
        resp = self.client.post(
            "/api/crm/quotations/",
            {
                "lead_id": fake,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_quotation_create_with_items_key(self):
        resp = self.client.post(
            "/api/crm/quotations/",
            {
                "lead_id": str(self.lead.id),
                "items": [
                    {"description": "Item", "quantity": 1, "unit_price": "100.00"}
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_quotation_update_draft_validation_error(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        resp = self.client.patch(
            f"/api/crm/quotations/{q.id}/update-draft/",
            {"terms": "Nope"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lead_assign_validation_error(self):
        resp = self.client.post(
            f"/api/crm/leads/{self.lead.id}/assign/",
            {"assigned_to": str(self.inactive_user.user_id)},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lead_progress_validation_error(self):
        CRMService.convert_lead(
            user=self.user,
            lead=self.lead,
            name="Conv",
            email="velead@x.com",
            phone="5550000001",
        )
        resp = self.client.post(f"/api/crm/leads/{self.lead.id}/progress/", {})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lead_lost_validation_error(self):
        CRMService.convert_lead(
            user=self.user,
            lead=self.lead,
            name="Conv",
            email="velead@x.com",
            phone="5550000001",
        )
        resp = self.client.post(
            f"/api/crm/leads/{self.lead.id}/lost/",
            {
                "lost_reason": "X",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lead_reengage_validation_error(self):
        resp = self.client.post(f"/api/crm/leads/{self.lead.id}/reengage/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lead_convert_validation_error(self):
        CRMService.convert_lead(
            user=self.user,
            lead=self.lead,
            name="Conv",
            email="velead@x.com",
            phone="5550000001",
        )
        resp = self.client.post(
            f"/api/crm/leads/{self.lead.id}/convert/",
            {
                "email": "velead@x.com",
                "phone": "5550000001",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activity_create_validation_error(self):
        resp = self.client.post(
            "/api/crm/activities/",
            {
                "activity_type": "CALL",
                "outcome": "Test",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lead_source_create_validation_error(self):
        CRMService.create_lead_source(user=self.user, name="Dup Source")
        resp = self.client.post(
            "/api/crm/lead-sources/",
            {
                "name": "Dup Source",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pipeline_create_validation_error(self):
        CRMService.create_pipeline(user=self.user, name="Dup Pipeline")
        resp = self.client.post(
            "/api/crm/pipelines/",
            {
                "name": "Dup Pipeline",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pipeline_stage_create_validation_error(self):
        resp = self.client.post(
            "/api/crm/pipeline-stages/",
            {
                "pipeline": str(self.inactive_pipeline.id),
                "name": "Fail Stage",
                "display_order": 1,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quotation_submit_validation_error(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        resp = self.client.post(f"/api/crm/quotations/{q.id}/submit/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quotation_approve_validation_error(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        resp = self.client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quotation_send_validation_error(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        resp = self.client.post(f"/api/crm/quotations/{q.id}/send/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quotation_accept_validation_error(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        resp = self.client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quotation_reject_validation_error(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/reject/",
            {
                "rejection_reason": "X",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quotation_reject_missing_reason(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/reject/", {}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quotation_reject_with_reason_key(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/reject/",
            {
                "reason": "Using reason key",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_quotation_revision_validation_error(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        QuotationService.accept_quotation(user=self.user, quotation=q)
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/revision/",
            {
                "revision_reason": "X",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quotation_reject_approval_validation_error(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/reject-approval/",
            {
                "reason": "X",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quotation_revision_with_reason_key(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/revision/",
            {
                "reason": "Using reason key",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_pdf_no_version(self):
        q = Quotation.objects.create(
            quotation_number="PDF-NOVER",
            lead=self.lead,
            created_by=self.user,
            status="APPROVED",
        )
        resp = self.client.get(f"/api/crm/quotations/{q.id}/pdf/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pdf_specific_version_invalid_format(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        resp = self.client.get(
            f"/api/crm/quotations/{q.id}/pdf/?version=abc",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_invalid_version_format(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/send-email/",
            {"version": "xyz"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_no_recipient(self):
        lead_no_email = CRMService.create_lead(
            user=self.user,
            name="No Email Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
            email=None,
        )
        q = QuotationService.create_quotation(user=self.user, lead=lead_no_email)
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        resp = self.client.post(f"/api/crm/quotations/{q.id}/send-email/", {})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_email_invalid_version_returns_400(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/send-email/",
            {
                "version": "abc",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_email_nonexistent_version_returns_400(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        resp = self.client.post(
            f"/api/crm/quotations/{q.id}/send-email/",
            {
                "version": "99",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quotation_list_no_filter(self):
        QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        resp = self.client.get("/api/crm/quotations/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_quotation_events_list(self):
        resp = self.client.get("/api/crm/quotation-events/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_customer_create_via_api(self):
        resp = self.client.post(
            "/api/crm/customers/",
            {
                "lead": str(self.lead.id),
                "name": "API Customer",
                "email": "apicust@x.com",
                "phone": "5550000099",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_lead_create_via_api(self):
        resp = self.client.post(
            "/api/crm/leads/",
            {
                "name": "New API Lead",
                "source": str(self.source.id),
                "assigned_to": str(self.user.user_id),
                "pipeline": str(self.pipeline.id),
                "current_stage": str(self.stage1.id),
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_activity_create_via_api(self):
        resp = self.client.post(
            "/api/crm/activities/",
            {
                "lead": str(self.lead.id),
                "activity_type": "EMAIL",
                "outcome": "Sent intro email",
                "notes": "Follow up next week",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_approve_own_quotation_via_api_returns_403(self):
        pl, st = self._create_approval_pipeline("Own Appr")
        lead = CRMService.create_lead(
            user=self.user,
            name="Own Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(user=self.user, lead=lead)
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        resp = self.client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ==============================================================================
# SECTION 16: PDF_UTILS COVERAGE
# ==============================================================================


class PDFUtilsTests(CRMBaseTestCase):
    """Tests for pdf_utils.py: customer branch and xhtml2pdf fallback."""

    def setUp(self):
        super().setUp()
        self.lead = CRMService.create_lead(
            user=self.user,
            name="PDF Utils Lead",
            email="pdfutils@x.com",
            phone="5550000001",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )

    def test_pdf_with_customer(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        q.refresh_from_db()
        QuotationService.accept_quotation(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertIsNotNone(q.customer)

        q2 = Quotation.objects.create(
            quotation_number="PDF-CUST-TEST",
            lead=self.lead,
            created_by=self.user,
            customer=q.customer,
            status="APPROVED",
        )
        v2 = QuotationVersion.objects.create(
            quotation=q2,
            version_number=1,
            status="APPROVED",
            created_by=self.user,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        QuotationLineItem.objects.create(
            version=v2,
            description="Item",
            quantity=1,
            unit_price=100,
        )
        q2.current_version = v2
        q2.save(update_fields=["current_version"])

        from customer_management.pdf_utils import generate_quotation_pdf

        pdf = generate_quotation_pdf(v2)
        self.assertIsInstance(pdf, bytes)
        self.assertTrue(len(pdf) > 0)

    def test_pdf_with_lead_no_customer(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        q.refresh_from_db()

        from customer_management.pdf_utils import generate_quotation_pdf

        pdf = generate_quotation_pdf(q.current_version)
        self.assertIsInstance(pdf, bytes)
        self.assertTrue(len(pdf) > 0)

    def test_pdf_lead_with_no_email_phone(self):
        lead_no_ep = CRMService.create_lead(
            user=self.user,
            name="No EP Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
            email=None,
            phone=None,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead_no_ep,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)

        from customer_management.pdf_utils import generate_quotation_pdf

        pdf = generate_quotation_pdf(q.current_version)
        self.assertIsInstance(pdf, bytes)

    def test_pdf_customer_with_no_company(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        q.refresh_from_db()
        QuotationService.accept_quotation(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertIsNotNone(q.customer)
        q.customer.company_name = None
        q.customer.save(update_fields=["company_name"])

        q2 = Quotation.objects.create(
            quotation_number="PDF-NOCOMP",
            lead=self.lead,
            created_by=self.user,
            customer=q.customer,
            status="APPROVED",
        )
        v2 = QuotationVersion.objects.create(
            quotation=q2,
            version_number=1,
            status="APPROVED",
            created_by=self.user,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        q2.current_version = v2
        q2.save(update_fields=["current_version"])

        from customer_management.pdf_utils import generate_quotation_pdf

        pdf = generate_quotation_pdf(v2)
        self.assertIsInstance(pdf, bytes)


# ==============================================================================
# SECTION 17: SERIALIZER VALIDATION COVERAGE
# ==============================================================================


class SerializerValidationTests(CRMBaseTestCase):
    """Tests for serializer validation edge cases."""

    def setUp(self):
        super().setUp()
        self.lead = CRMService.create_lead(
            user=self.user,
            name="Ser Lead",
            email="ser@x.com",
            phone="5550000001",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )

    def test_lead_serializer_inactive_source(self):
        from customer_management.serializers import LeadSerializer

        serializer = LeadSerializer(
            data={
                "name": "Test",
                "source": str(self.inactive_source.id),
                "assigned_to": str(self.user.user_id),
                "pipeline": str(self.pipeline.id),
                "current_stage": str(self.stage1.id),
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_lead_serializer_inactive_pipeline(self):
        from customer_management.serializers import LeadSerializer

        serializer = LeadSerializer(
            data={
                "name": "Test",
                "source": str(self.source.id),
                "assigned_to": str(self.user.user_id),
                "pipeline": str(self.inactive_pipeline.id),
                "current_stage": str(self.stage1.id),
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_lead_serializer_inactive_stage(self):
        from customer_management.serializers import LeadSerializer

        serializer = LeadSerializer(
            data={
                "name": "Test",
                "source": str(self.source.id),
                "assigned_to": str(self.user.user_id),
                "pipeline": str(self.pipeline.id),
                "current_stage": str(self.inactive_stage.id),
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_lead_serializer_wrong_stage_for_pipeline(self):
        from customer_management.serializers import LeadSerializer

        serializer = LeadSerializer(
            data={
                "name": "Test",
                "source": str(self.source.id),
                "assigned_to": str(self.user.user_id),
                "pipeline": str(self.pipeline.id),
                "current_stage": str(self.stage2_p2.id),
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_lead_serializer_inactive_assigned_to(self):
        from customer_management.serializers import LeadSerializer

        serializer = LeadSerializer(
            data={
                "name": "Test",
                "source": str(self.source.id),
                "assigned_to": str(self.inactive_user.user_id),
                "pipeline": str(self.pipeline.id),
                "current_stage": str(self.stage1.id),
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_lead_serializer_update_terminal_status_rejected(self):
        from customer_management.serializers import LeadSerializer

        CRMService.convert_lead(
            user=self.user,
            lead=self.lead,
            name="Conv",
            email="ser@x.com",
            phone="5550000001",
        )
        self.lead.refresh_from_db()
        serializer = LeadSerializer(
            self.lead,
            data={"name": "Updated"},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())

    def test_lead_serializer_lost_reason_on_non_lost_lead(self):
        from customer_management.serializers import LeadSerializer

        serializer = LeadSerializer(
            self.lead,
            data={"lost_reason": "test"},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())

    def test_pipeline_stage_serializer_inactive_pipeline(self):
        from customer_management.serializers import PipelineStageSerializer

        serializer = PipelineStageSerializer(
            data={
                "pipeline": str(self.inactive_pipeline.id),
                "name": "Test",
                "display_order": 1,
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_pipeline_stage_serializer_low_display_order(self):
        from customer_management.serializers import PipelineStageSerializer

        serializer = PipelineStageSerializer(
            data={
                "pipeline": str(self.pipeline.id),
                "name": "Test",
                "display_order": 0,
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_activity_serializer_no_lead_no_customer(self):
        from customer_management.serializers import ActivitySerializer

        serializer = ActivitySerializer(
            data={
                "activity_type": "CALL",
                "outcome": "Test",
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_activity_serializer_both_lead_and_customer(self):
        from customer_management.serializers import ActivitySerializer

        serializer = ActivitySerializer(
            data={
                "lead": str(self.lead.id),
                "customer": str(self.lead.id),
                "activity_type": "CALL",
                "outcome": "Test",
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_activity_serializer_converted_lead(self):
        from customer_management.serializers import ActivitySerializer

        CRMService.convert_lead(
            user=self.user,
            lead=self.lead,
            name="Conv",
            email="ser@x.com",
            phone="5550000001",
        )
        self.lead.refresh_from_db()
        serializer = ActivitySerializer(
            data={
                "lead": str(self.lead.id),
                "activity_type": "CALL",
                "outcome": "Test",
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_activity_serializer_follow_up_no_date(self):
        from customer_management.serializers import ActivitySerializer

        serializer = ActivitySerializer(
            data={
                "lead": str(self.lead.id),
                "activity_type": "CALL",
                "outcome": "Test",
                "follow_up_required": True,
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_activity_serializer_date_without_flag(self):
        from customer_management.serializers import ActivitySerializer

        serializer = ActivitySerializer(
            data={
                "lead": str(self.lead.id),
                "activity_type": "CALL",
                "outcome": "Test",
                "follow_up_date": "2026-09-01T10:00:00Z",
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_quotation_line_item_serializer(self):
        from customer_management.serializers import QuotationLineItemSerializer

        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Test", "quantity": 2, "unit_price": "50.00"}],
        )
        li = q.current_version.line_items.first()
        serializer = QuotationLineItemSerializer(li)
        self.assertEqual(serializer.data["amount"], "100.00")

    def test_quotation_version_serializer(self):
        from customer_management.serializers import QuotationVersionSerializer

        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Test", "quantity": 1, "unit_price": 100}],
        )
        serializer = QuotationVersionSerializer(q.current_version)
        self.assertIn("line_items", serializer.data)
        self.assertIn("approvals", serializer.data)

    def test_quotation_serializer(self):
        from customer_management.serializers import QuotationSerializer

        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Test", "quantity": 1, "unit_price": 100}],
        )
        serializer = QuotationSerializer(q)
        self.assertIn("current_version_detail", serializer.data)
        self.assertIn("all_versions", serializer.data)

    def test_quotation_integration_event_serializer(self):
        from customer_management.serializers import QuotationIntegrationEventSerializer

        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        event = QuotationIntegrationEvent.objects.filter(quotation=q).first()
        serializer = QuotationIntegrationEventSerializer(event)
        self.assertEqual(serializer.data["event_type"], "quotation.followup_required")

    def test_audit_log_serializer(self):
        from customer_management.serializers import AuditLogSerializer

        log = CRMService.create_audit_log(
            user=self.user,
            entity_type="Test",
            entity_id=uuid4(),
            action="TEST_ACTION",
        )
        serializer = AuditLogSerializer(log)
        self.assertEqual(serializer.data["action"], "TEST_ACTION")

    def test_quotation_approval_serializer(self):
        from customer_management.serializers import QuotationApprovalSerializer

        pl, st = self._create_approval_pipeline("ApprSer Pipeline")
        lead = CRMService.create_lead(
            user=self.user,
            name="ApprSer Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(user=self.user, lead=lead)
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        approval = QuotationApproval.objects.filter(
            version=q.current_version,
        ).first()
        serializer = QuotationApprovalSerializer(approval)
        self.assertEqual(serializer.data["decision"], "PENDING")


# ==============================================================================
# SECTION 18: SERVICE-LEVEL VALIDATION BRANCH TESTS
# Target uncovered lines in services.py for create_pipeline_stage / create_lead
# ==============================================================================


class ServiceValidationBranchTests(CRMBaseTestCase):
    """Direct CRMService calls to hit uncovered validation branches."""

    def test_create_pipeline_stage_inactive_pipeline(self):
        """services.py:133 — inactive pipeline raises ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            CRMService.create_pipeline_stage(
                user=self.user,
                pipeline=self.inactive_pipeline,
                name="Bad Stage",
                display_order=1,
            )
        self.assertIn("inactive", str(ctx.exception).lower())

    def test_create_pipeline_stage_display_order_zero(self):
        """services.py:138 — display_order < 1 raises ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            CRMService.create_pipeline_stage(
                user=self.user,
                pipeline=self.pipeline,
                name="Zero Stage",
                display_order=0,
            )
        self.assertIn("at least 1", str(ctx.exception).lower())

    def test_create_pipeline_stage_display_order_negative(self):
        """services.py:138 — negative display_order raises ValidationError."""
        with self.assertRaises(ValidationError):
            CRMService.create_pipeline_stage(
                user=self.user,
                pipeline=self.pipeline,
                name="Neg Stage",
                display_order=-5,
            )

    def test_create_lead_inactive_source(self):
        """services.py:185 — inactive lead source raises ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            CRMService.create_lead(
                user=self.user,
                name="Bad Lead",
                source=self.inactive_source,
                assigned_to=self.user,
                pipeline=self.pipeline,
                current_stage=self.stage1,
            )
        self.assertIn("inactive", str(ctx.exception).lower())

    def test_create_lead_inactive_pipeline(self):
        """services.py:190 — inactive pipeline raises ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            CRMService.create_lead(
                user=self.user,
                name="Bad Lead",
                source=self.source,
                assigned_to=self.user,
                pipeline=self.inactive_pipeline,
                current_stage=self.stage1,
            )
        self.assertIn("inactive", str(ctx.exception).lower())

    def test_create_lead_inactive_stage(self):
        """services.py:195 — inactive stage raises ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            CRMService.create_lead(
                user=self.user,
                name="Bad Lead",
                source=self.source,
                assigned_to=self.user,
                pipeline=self.pipeline,
                current_stage=self.inactive_stage,
            )
        self.assertIn("inactive", str(ctx.exception).lower())

    def test_create_lead_stage_wrong_pipeline(self):
        """services.py:200 — stage from different pipeline raises ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            CRMService.create_lead(
                user=self.user,
                name="Bad Lead",
                source=self.source,
                assigned_to=self.user,
                pipeline=self.pipeline,
                current_stage=self.stage2_p2,
            )
        self.assertIn("does not belong", str(ctx.exception).lower())

    def test_create_lead_inactive_assigned_to(self):
        """services.py:205 — inactive assigned_to raises ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            CRMService.create_lead(
                user=self.user,
                name="Bad Lead",
                source=self.source,
                assigned_to=self.inactive_user,
                pipeline=self.pipeline,
                current_stage=self.stage1,
            )
        self.assertIn("inactive", str(ctx.exception).lower())

    def test_create_lead_no_active_stages(self):
        """services.py:220 — pipeline with no active stages raises ValidationError."""
        pl = CRMService.create_pipeline(user=self.user, name="Empty PL")
        stage_only = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pl,
            name="Only",
            display_order=1,
            requires_quotation=False,
        )
        # Reload the stage from DB so it has is_active=True in ORM cache
        stage_only.refresh_from_db()
        # Now deactivate all stages in DB behind the ORM's back
        PipelineStage.objects.filter(pipeline=pl).update(is_active=False)
        # stage_only ORM object still has is_active=True from cache,
        # so the line-194 check passes, but the line-209 query finds none
        with self.assertRaises(ValidationError) as ctx:
            CRMService.create_lead(
                user=self.user,
                name="Bad Lead",
                source=self.source,
                assigned_to=self.user,
                pipeline=pl,
                current_stage=stage_only,
            )
        self.assertIn("no active stages", str(ctx.exception).lower())


# ==============================================================================
# SECTION 19: QUOTATION NUMBER COLLISION TEST
# ==============================================================================


class QuotationNumberCollisionTest(CRMBaseTestCase):
    """Test the while-loop in generate_quotation_number when a collision occurs."""

    def test_generate_quotation_number_retries_on_collision(self):
        """services.py:645-646 — collision loop regenerates number."""
        original_exists = Quotation.objects.filter().exists

        call_count = [0]

        def fake_exists(self_or_filter, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 1:
                return True  # first call collides
            return False

        with mock.patch.object(
            Quotation.objects, "filter", wraps=Quotation.objects.filter
        ):
            # We mock uuid4 to control the suffix
            suffixes = ["AAAAAA", "BBBBBB"]
            uuid_idx = [0]
            original_uuid4 = uuid4

            def controlled_uuid4():
                val = original_uuid4()
                # Just let it generate normally, we test the retry by
                # patching the Quotation filter
                return val

            # Better approach: mock filter().exists() to return True once
            with mock.patch(
                "customer_management.services.Quotation.objects"
            ) as mock_qs:
                # The generate method does: Quotation.objects.filter(quotation_number=number).exists()
                mock_filter = mock_qs.filter.return_value
                mock_filter.exists.side_effect = [True, False]
                result = QuotationService.generate_quotation_number()
                self.assertTrue(result.startswith("Q-"))
                self.assertEqual(mock_filter.exists.call_count, 2)


# ==============================================================================
# SECTION 20: APPROVE / REJECT QUOTATION EDGE CASES
# ==============================================================================


class QuotationApprovalEdgeCaseTests(CRMBaseTestCase):
    """Edge cases in approve_quotation and reject_quotation_approval."""

    def _make_sent_quotation(self, approval_required=False):
        """Helper: create a quotation that has been submitted (pending)."""
        if approval_required:
            pl, st = self._create_approval_pipeline("Edge Appr PL")
            lead = CRMService.create_lead(
                user=self.user,
                name="Edge Lead",
                source=self.source,
                assigned_to=self.user,
                pipeline=pl,
                current_stage=st,
            )
        else:
            lead = CRMService.create_lead(
                user=self.user,
                name="Edge Lead",
                source=self.source,
                assigned_to=self.user,
                pipeline=self.pipeline,
                current_stage=self.stage1,
            )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        return q

    def test_approve_no_pending_approval_record(self):
        """services.py:917 — approve when no pending approval record exists."""
        q = self._make_sent_quotation(approval_required=True)
        # Manually delete the pending approval record
        QuotationApproval.objects.filter(
            version=q.current_version,
            decision=QuotationApproval.Decision.PENDING,
        ).delete()
        with self.assertRaises(ValidationError) as ctx:
            QuotationService.approve_quotation(
                reviewer_user=self.user,
                quotation=q,
            )
        self.assertIn("No pending approval", str(ctx.exception))

    def test_reject_approval_no_pending_record(self):
        """services.py:986 — reject approval when no pending approval exists."""
        q = self._make_sent_quotation(approval_required=True)
        QuotationApproval.objects.filter(
            version=q.current_version,
            decision=QuotationApproval.Decision.PENDING,
        ).delete()
        with self.assertRaises(ValidationError) as ctx:
            QuotationService.reject_quotation_approval(
                reviewer_user=self.user,
                quotation=q,
            )
        self.assertIn("No pending approval", str(ctx.exception))

    def test_approve_already_approved(self):
        """services.py:908-909 — approving an already-approved quotation."""
        q = self._make_sent_quotation(approval_required=True)
        # Use a different reviewer to avoid self-approval check
        reviewer_client, reviewer_user, _ = self._create_manager_client(
            permissions=["approve_quotation", "view_quotation"],
            username="approver2",
        )
        QuotationService.approve_quotation(reviewer_user=reviewer_user, quotation=q)
        # Now try to approve again — version is no longer PENDING_APPROVAL
        with self.assertRaises(ValidationError) as ctx:
            QuotationService.approve_quotation(reviewer_user=reviewer_user, quotation=q)
        self.assertIn("Only quotations pending approval", str(ctx.exception))


# ==============================================================================
# SECTION 21: SEND_QUOTATION_EMAIL EDGE CASES
# ==============================================================================


class SendQuotationEmailEdgeCaseTests(CRMBaseTestCase):
    """Edge cases in QuotationService.send_quotation_email (services.py:1323+)."""

    def test_send_email_no_version(self):
        """services.py:1349 — quotation with no version raises ValidationError."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        # Delete all versions
        q.versions.all().delete()
        q.refresh_from_db()
        with self.assertRaises(ValidationError) as ctx:
            QuotationService.send_quotation_email(
                user=self.user,
                quotation=q,
                recipient_email="test@example.com",
            )
        self.assertIn("no active version", str(ctx.exception))

    def test_send_email_draft_version(self):
        """services.py:1351-1353 — DRAFT version blocked from email."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        with self.assertRaises(ValidationError) as ctx:
            QuotationService.send_quotation_email(
                user=self.user,
                quotation=q,
                recipient_email="test@example.com",
            )
        self.assertIn("blocked", str(ctx.exception))

    def test_send_email_pending_approval_version(self):
        """services.py:1351-1353 — PENDING_APPROVAL version blocked from email."""
        pl, st = self._create_approval_pipeline("Email Appr PL")
        lead = CRMService.create_lead(
            user=self.user,
            name="Email Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        with self.assertRaises(ValidationError) as ctx:
            QuotationService.send_quotation_email(
                user=self.user,
                quotation=q,
                recipient_email="test@example.com",
            )
        self.assertIn("blocked", str(ctx.exception))

    def test_send_email_invalid_version_number(self):
        """services.py:1343-1344 — invalid version number raises ValidationError."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        # Submit/approve so we can email
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        if q.current_version.approval_required:
            QuotationService.approve_quotation(reviewer_user=self.user, quotation=q)
        with self.assertRaises(ValidationError) as ctx:
            QuotationService.send_quotation_email(
                user=self.user,
                quotation=q,
                version_number=999,
                recipient_email="test@example.com",
            )
        self.assertIn("does not exist", str(ctx.exception))

    def test_send_email_no_recipient(self):
        """services.py:1363-1364 — no email on customer/lead raises ValidationError."""
        lead = self._make_lead(email=None)
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        # Stage without approval so it auto-approves on submit
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        with self.assertRaises(ValidationError) as ctx:
            QuotationService.send_quotation_email(
                user=self.user,
                quotation=q,
            )
        self.assertIn("email is required", str(ctx.exception).lower())

    def test_send_email_customer_email_fallback(self):
        """services.py:1358-1359 — uses customer email when no recipient specified."""
        lead = self._make_lead(email=None)
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        # Manually set customer on the quotation
        customer = CRMService.convert_lead(
            user=self.user,
            lead=lead,
            name="Cust Fallback",
            email="custfallback@example.com",
            phone="9999999999",
        )
        q.customer = customer
        q.save(update_fields=["customer"])
        q.refresh_from_db()
        # Approve the quotation so we can email
        q.current_version.status = QuotationStatus.APPROVED
        q.current_version.save(update_fields=["status"])
        q.status = QuotationStatus.APPROVED
        q.save(update_fields=["status"])

        with mock.patch("django.core.mail.EmailMessage") as MockEmail:
            mock_instance = MockEmail.return_value
            mock_instance.send.return_value = None
            q, v = QuotationService.send_quotation_email(
                user=self.user,
                quotation=q,
            )
            mock_instance.send.assert_called_once()
            args, kwargs = MockEmail.call_args
            self.assertEqual(kwargs["to"], ["custfallback@example.com"])

    def test_send_email_lead_email_fallback(self):
        """services.py:1360-1361 — uses lead email when no customer and no recipient."""
        lead = self._make_lead(email="leadfallback@example.com")
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        # Ensure no customer
        self.assertIsNone(q.customer)
        # Approve
        q.current_version.status = QuotationStatus.APPROVED
        q.current_version.save(update_fields=["status"])
        q.status = QuotationStatus.APPROVED
        q.save(update_fields=["status"])

        with mock.patch("django.core.mail.EmailMessage") as MockEmail:
            mock_instance = MockEmail.return_value
            mock_instance.send.return_value = None
            q, v = QuotationService.send_quotation_email(
                user=self.user,
                quotation=q,
            )
            args, kwargs = MockEmail.call_args
            self.assertEqual(kwargs["to"], ["leadfallback@example.com"])

    def test_send_email_smtp_exception(self):
        """services.py:1391-1404 — SMTPException creates audit log and raises."""
        lead = self._make_lead(email="smtp@example.com")
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        q.current_version.status = QuotationStatus.APPROVED
        q.current_version.save(update_fields=["status"])
        q.status = QuotationStatus.APPROVED
        q.save(update_fields=["status"])

        from smtplib import SMTPException

        with mock.patch("django.core.mail.EmailMessage") as MockEmail:
            mock_instance = MockEmail.return_value
            mock_instance.send.side_effect = SMTPException("Connection refused")
            with self.assertRaises(ValidationError) as ctx:
                QuotationService.send_quotation_email(
                    user=self.user,
                    quotation=q,
                )
            self.assertIn("Email delivery failed", str(ctx.exception))
            # Verify audit log was created
            audit = AuditLog.objects.filter(
                entity_type="Quotation",
                action="QUOTATION_EMAIL_FAILED",
            ).first()
            self.assertIsNotNone(audit)

    def test_send_email_customer_activity_branch(self):
        """services.py:1420-1422 — activity logged with customer when quotation has customer."""
        lead = self._make_lead(email="act@example.com")
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        # Convert lead so quotation gets a customer
        customer = CRMService.convert_lead(
            user=self.user,
            lead=lead,
            name="Act Customer",
            email="act@example.com",
            phone="1111111111",
        )
        q.customer = customer
        q.save(update_fields=["customer"])
        q.refresh_from_db()
        q.current_version.status = QuotationStatus.APPROVED
        q.current_version.save(update_fields=["status"])
        q.status = QuotationStatus.APPROVED
        q.save(update_fields=["status"])

        with mock.patch("django.core.mail.EmailMessage") as MockEmail:
            mock_instance = MockEmail.return_value
            mock_instance.send.return_value = None
            q, v = QuotationService.send_quotation_email(
                user=self.user,
                quotation=q,
            )
            # Activity should have customer set, not lead
            activity = Activity.objects.filter(
                activity_type=Activity.ActivityType.QUOTATION_EMAIL_SENT,
                customer=customer,
            ).first()
            self.assertIsNotNone(activity)
            self.assertIsNone(activity.lead)

    def test_send_email_lead_activity_branch(self):
        """services.py:1423-1425 — activity logged with lead when no customer."""
        lead = self._make_lead(email="leadact@example.com")
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        q.current_version.status = QuotationStatus.APPROVED
        q.current_version.save(update_fields=["status"])
        q.status = QuotationStatus.APPROVED
        q.save(update_fields=["status"])

        with mock.patch("django.core.mail.EmailMessage") as MockEmail:
            mock_instance = MockEmail.return_value
            mock_instance.send.return_value = None
            q, v = QuotationService.send_quotation_email(
                user=self.user,
                quotation=q,
            )
            activity = Activity.objects.filter(
                activity_type=Activity.ActivityType.QUOTATION_EMAIL_SENT,
                lead=lead,
            ).first()
            self.assertIsNotNone(activity)
            self.assertIsNone(activity.customer)

    def _make_lead(self, email="test@example.com"):
        """Helper: create an active lead on the default pipeline."""
        return CRMService.create_lead(
            user=self.user,
            name="Test Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
            email=email,
        )


# ==============================================================================
# SECTION 22: VIEW-LEVEL DjangoValidationError HANDLER TESTS
# ==============================================================================


class ViewValidationErrorHandlerTests(CRMBaseTestCase):
    """Tests that hit DjangoValidationError catch blocks in views.py."""

    def test_lead_source_create_duplicate_name(self):
        """views.py:69-70 — duplicate lead source name triggers 400."""
        CRMService.create_lead_source(user=self.user, name="Dup Source")
        response = self.client.post(
            "/api/crm/lead-sources/",
            {
                "name": "Dup Source",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pipeline_create_duplicate_name(self):
        """views.py:106-107 — duplicate pipeline name triggers 400."""
        CRMService.create_pipeline(user=self.user, name="Dup Pipeline")
        response = self.client.post(
            "/api/crm/pipelines/",
            {
                "name": "Dup Pipeline",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pipeline_stage_create_inactive_pipeline(self):
        """views.py:153-154 — creating stage on inactive pipeline triggers 400."""
        response = self.client.post(
            "/api/crm/pipeline-stages/",
            {
                "pipeline": str(self.inactive_pipeline.id),
                "name": "Bad Stage",
                "display_order": 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lead_create_inactive_source(self):
        """views.py:214-215 — creating lead with inactive source triggers 400."""
        response = self.client.post(
            "/api/crm/leads/",
            {
                "name": "Bad Lead",
                "source": str(self.inactive_source.id),
                "assigned_to": str(self.user.user_id),
                "pipeline": str(self.pipeline.id),
                "current_stage": str(self.stage1.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activity_create_invalid_data(self):
        """views.py:498-499 — creating activity with bad data triggers 400."""
        response = self.client.post(
            "/api/crm/activities/",
            {
                "activity_type": "CALL",
                "outcome": "Test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quotation_create_non_active_lead(self):
        """views.py:638-639 — creating quotation for non-active lead triggers 400."""
        lead = CRMService.create_lead(
            user=self.user,
            name="Lost Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        CRMService.mark_lead_lost(
            user=self.user,
            lead=lead,
            lost_reason="Budget",
        )
        response = self.client.post(
            "/api/crm/quotations/",
            {
                "lead": str(lead.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ==============================================================================
# SECTION 23: PDF GENERATION FAILURE VIEW TEST
# ==============================================================================


class QuotationPDFFailureViewTest(CRMBaseTestCase):
    """views.py:960-962 — PDF generation failure returns 500."""

    def test_pdf_generation_failure_returns_500(self):
        """When generate_quotation_pdf raises, view returns 500."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        # Approve so version status allows PDF
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        q.current_version.refresh_from_db()
        if q.current_version.status != QuotationStatus.APPROVED:
            QuotationService.approve_quotation(reviewer_user=self.user, quotation=q)

        with mock.patch(
            "customer_management.views.generate_quotation_pdf",
            side_effect=RuntimeError("PDF rendering crashed"),
        ):
            response = self.client.get(f"/api/crm/quotations/{q.id}/pdf/")
            self.assertEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            self.assertIn("Failed to generate PDF", response.data["detail"])

    def test_pdf_invalid_version_param(self):
        """views.py:938-941 — invalid version query param returns 400."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        response = self.client.get(f"/api/crm/quotations/{q.id}/pdf/?version=abc")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pdf_version_not_found(self):
        """views.py:933-937 — non-existent version returns 404."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        response = self.client.get(f"/api/crm/quotations/{q.id}/pdf/?version=99")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def _make_lead(self, email="pdf@example.com"):
        return CRMService.create_lead(
            user=self.user,
            name="PDF Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
            email=email,
        )


# ==============================================================================
# SECTION 24: SEND EMAIL VIEW EDGE CASES
# ==============================================================================


class SendEmailViewEdgeCaseTests(CRMBaseTestCase):
    """View-level tests for QuotationSendEmailView."""

    def test_send_email_invalid_version_param(self):
        """views.py:1000-1005 — invalid version query param returns 400."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        response = self.client.post(
            f"/api/crm/quotations/{q.id}/send-email/",
            {"version": "abc", "recipient_email": "test@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid version", response.data["detail"])

    def test_send_email_draft_version(self):
        """views.py:1017-1021 — sending email on draft triggers 400."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        response = self.client.post(
            f"/api/crm/quotations/{q.id}/send-email/",
            {"recipient_email": "test@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def _make_lead(self, email="viewemail@example.com"):
        return CRMService.create_lead(
            user=self.user,
            name="EmailView Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
            email=email,
        )


# ==============================================================================
# SECTION 25: XHTML2PDF FALLBACK TEST
# ==============================================================================


class PDFUtilsFallbackTest(CRMBaseTestCase):
    """pdf_utils.py:51-60 — xhtml2pdf fallback when weasyprint fails."""

    def test_xhtml2pdf_fallback(self):
        """When weasyprint is not installed, falls back to xhtml2pdf."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[
                {"description": "Widget", "quantity": 3, "unit_price": "25.00"}
            ],
        )
        version = q.current_version

        mock_weasyprint = mock.MagicMock()
        mock_weasyprint.HTML.side_effect = Exception("No weasyprint for you")

        mock_pisa = mock.MagicMock()
        mock_pisa.status.err = 0

        # The pisa.CreatePDF writes to a BytesIO dest
        def fake_create_pdf(src, dest):
            dest.write(b"%PDF-1.4 fake pdf content")
            return mock_pisa.status

        mock_pisa.CreatePDF.side_effect = fake_create_pdf

        with mock.patch.dict(
            "sys.modules",
            {
                "weasyprint": mock_weasyprint,
            },
        ):
            from customer_management import pdf_utils

            with mock.patch.object(pdf_utils, "pisa", mock_pisa, create=True):
                result = pdf_utils.generate_quotation_pdf(version)
                self.assertIsInstance(result, bytes)
                self.assertTrue(len(result) > 0)

    def test_xhtml2pdf_error_raises(self):
        """pdf_utils.py:58-59 — xhtml2pdf error raises RuntimeError."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "Thing", "quantity": 1, "unit_price": 10}],
        )
        version = q.current_version

        mock_weasyprint = mock.MagicMock()
        mock_weasyprint.HTML.side_effect = Exception("No weasyprint")

        mock_pisa = mock.MagicMock()
        mock_pisa.status.err = 1  # error

        with mock.patch.dict(
            "sys.modules",
            {
                "weasyprint": mock_weasyprint,
            },
        ):
            from customer_management import pdf_utils

            with mock.patch.object(pdf_utils, "pisa", mock_pisa, create=True):
                with self.assertRaises(RuntimeError) as ctx:
                    pdf_utils.generate_quotation_pdf(version)
                self.assertIn("xhtml2pdf", str(ctx.exception))

    def _make_lead(self):
        return CRMService.create_lead(
            user=self.user,
            name="PDF Utils Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
            email="pdf@example.com",
        )


# ==============================================================================
# SECTION 26: ADDITIONAL VIEW ERROR PATHS
# ==============================================================================


class ViewAdditionalErrorPathTests(CRMBaseTestCase):
    """Additional view-level error paths not covered elsewhere."""

    def test_submit_already_submitted_quotation(self):
        """views.py:714-718 — submitting a PENDING quotation triggers 400."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        response = self.client.post(
            f"/api/crm/quotations/{q.id}/submit/",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approve_draft_quotation(self):
        """views.py:745-749 — approving a draft quotation triggers 400."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        response = self.client.post(
            f"/api/crm/quotations/{q.id}/approve/",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_draft_quotation(self):
        """views.py:799-803 — sending a draft quotation triggers 400."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        response = self.client.post(
            f"/api/crm/quotations/{q.id}/send/",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accept_draft_quotation(self):
        """views.py:859-863 — accepting a draft quotation triggers 400."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        response = self.client.post(
            f"/api/crm/quotations/{q.id}/accept/",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_draft_quotation(self):
        """views.py:896-900 — rejecting a draft quotation triggers 400."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        response = self.client.post(
            f"/api/crm/quotations/{q.id}/reject/",
            {"rejection_reason": "Too expensive"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_approval_draft_quotation(self):
        """views.py:773-777 — rejecting approval on draft triggers 400."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        response = self.client.post(
            f"/api/crm/quotations/{q.id}/reject-approval/",
            {"reason": "Nope"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_revision_no_version(self):
        """views.py:833-837 — revision when quotation has no version triggers 400."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        q.versions.all().delete()
        q.refresh_from_db()
        response = self.client.post(
            f"/api/crm/quotations/{q.id}/revision/",
            {"terms": "New terms"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_email_not_found(self):
        """views.py — sending email for non-existent quotation triggers 404."""
        fake_id = uuid4()
        response = self.client.post(
            f"/api/crm/quotations/{fake_id}/send-email/",
            {"recipient_email": "test@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reject_without_reason(self):
        """views.py:884-888 — reject without reason triggers 400."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        response = self.client.post(
            f"/api/crm/quotations/{q.id}/reject/",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("rejection_reason", response.data)

    def test_update_draft_invalid_status(self):
        """views.py:688-692 — updating non-draft quotation triggers 400."""
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self._make_lead(),
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        response = self.client.patch(
            f"/api/crm/quotations/{q.id}/update-draft/",
            {"terms": "New terms"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_email_auto_approves(self):
        """views.py — send_email on APPROVED quotation auto-sends first."""
        lead = CRMService.create_lead(
            user=self.user,
            name="AutoAppr Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
            email="auto@example.com",
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        # Should be APPROVED (no approval_required on stage1)
        self.assertEqual(q.current_version.status, QuotationStatus.APPROVED)

        with mock.patch("django.core.mail.EmailMessage") as MockEmail:
            mock_instance = MockEmail.return_value
            mock_instance.send.return_value = None
            response = self.client.post(
                f"/api/crm/quotations/{q.id}/send-email/",
                {"recipient_email": "auto@example.com"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            # After email, quotation should be SENT (auto-send triggered)
            q.refresh_from_db()
            self.assertEqual(q.status, QuotationStatus.SENT)

    def _make_lead(self):
        return CRMService.create_lead(
            user=self.user,
            name="ErrorPath Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
            email="err@example.com",
        )


# ==============================================================================
# SECTION 27: AUDIT LOG DETAIL TESTS
# ==============================================================================


class AuditLogDetailTests(CRMBaseTestCase):
    """Verify audit logs are created for each major action with correct content."""

    def test_lead_source_created_audit(self):
        source = CRMService.create_lead_source(
            user=self.user,
            name="Audit Source",
        )
        log = AuditLog.objects.filter(
            entity_type="LeadSource",
            action="LEAD_SOURCE_CREATED",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.new_value["name"], "Audit Source")

    def test_pipeline_created_audit(self):
        pipeline = CRMService.create_pipeline(
            user=self.user,
            name="Audit Pipeline",
        )
        log = AuditLog.objects.filter(
            entity_type="Pipeline",
            action="PIPELINE_CREATED",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.new_value["name"], "Audit Pipeline")

    def test_pipeline_stage_created_audit(self):
        stage = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=self.pipeline,
            name="Audit Stage",
            display_order=10,
        )
        log = AuditLog.objects.filter(
            entity_type="PipelineStage",
            action="PIPELINE_STAGE_CREATED",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.new_value["name"], "Audit Stage")

    def test_lead_created_audit(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Audit Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )
        log = AuditLog.objects.filter(
            entity_type="Lead",
            action="LEAD_CREATED",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.new_value["name"], "Audit Lead")

    def test_quotation_approved_audit(self):
        pl, st = self._create_approval_pipeline("Audit Appr PL")
        reviewer = User.objects.create_user(
            username="reviewer",
            email="reviewer@example.com",
            password="Password123!",
            phone_number="5555555555",
            role=self.role,
        )
        lead = CRMService.create_lead(
            user=self.user,
            name="Audit Appr Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pl,
            current_stage=st,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.approve_quotation(reviewer_user=reviewer, quotation=q)
        log = AuditLog.objects.filter(
            entity_type="Quotation",
            action="QUOTATION_APPROVED",
        ).first()
        self.assertIsNotNone(log)

    def test_quotation_rejected_audit(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Rej Audit Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
            email="rej@example.com",
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        QuotationService.reject_quotation(
            user=self.user,
            quotation=q,
            rejection_reason="Too expensive",
        )
        log = AuditLog.objects.filter(
            entity_type="Quotation",
            action="QUOTATION_REJECTED",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.new_value["rejection_reason"], "Too expensive")

    def test_quotation_version_created_audit(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Ver Audit Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
            email="ver@example.com",
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)
        QuotationService.create_revision(
            user=self.user,
            quotation=q,
            line_items=[{"description": "Y", "quantity": 2, "unit_price": 50}],
        )
        log = AuditLog.objects.filter(
            entity_type="Quotation",
            action="QUOTATION_VERSION_CREATED",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.new_value["version"], 2)

    def test_quotation_email_sent_audit(self):
        lead = CRMService.create_lead(
            user=self.user,
            name="Email Audit Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
            email="emaill@example.com",
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()

        with mock.patch("django.core.mail.EmailMessage") as MockEmail:
            mock_instance = MockEmail.return_value
            mock_instance.send.return_value = None
            QuotationService.send_quotation_email(
                user=self.user,
                quotation=q,
                recipient_email="emaill@example.com",
            )
        log = AuditLog.objects.filter(
            entity_type="Quotation",
            action="QUOTATION_EMAIL_SENT",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.new_value["sent_to"], "emaill@example.com")

    def test_quotation_email_failed_audit(self):
        from smtplib import SMTPException

        lead = CRMService.create_lead(
            user=self.user,
            name="Fail Audit Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
            email="fail@example.com",
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead,
            line_items=[{"description": "X", "quantity": 1, "unit_price": 100}],
        )
        q.current_version.status = QuotationStatus.APPROVED
        q.current_version.save(update_fields=["status"])
        q.status = QuotationStatus.APPROVED
        q.save(update_fields=["status"])

        with mock.patch("django.core.mail.EmailMessage") as MockEmail:
            mock_instance = MockEmail.return_value
            mock_instance.send.side_effect = SMTPException("Server down")
            with self.assertRaises(ValidationError):
                QuotationService.send_quotation_email(
                    user=self.user,
                    quotation=q,
                )
        log = AuditLog.objects.filter(
            entity_type="Quotation",
            action="QUOTATION_EMAIL_FAILED",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.new_value["error"], "Server down")
