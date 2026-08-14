from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status
from customer_management.models import (
    LeadSource, Pipeline, PipelineStage, Lead, Customer, Activity, AuditLog,
    Quotation, QuotationVersion, QuotationStatus, QuotationIntegrationEvent, QuotationApproval
)
from customer_management.services import CRMService, QuotationService
from accounts.models import Role

User = get_user_model()


class CRMBaseTestCase(TestCase):
    def setUp(self):
        # Create permissions and role
        self.role = Role.objects.create(rolename="Manager")
        all_perms = Permission.objects.filter(
            codename__in=[
                "view_leadsource", "manage_lead_source",
                "view_pipeline", "manage_pipeline",
                "view_pipelinestage", "manage_pipeline_stage",
                "view_lead", "add_lead", "change_lead", "delete_lead",
                "assign_lead", "progress_lead", "mark_lead_lost",
                "reengage_lead", "convert_lead",
                "view_customer", "add_customer",
                "view_activity", "add_activity",
                "view_auditlog",
                "submit_quotation", "approve_quotation", "send_quotation",
                "accept_quotation", "reject_quotation", "request_quotation_revision",
                "add_quotation", "change_quotation", "view_quotation", "delete_quotation"
            ]
        )
        self.role.permissions.set(all_perms)

        # Create active user
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="Password123!",
            phone_number="1234567890",
            role=self.role
        )

        # Create inactive user
        self.inactive_user = User.objects.create_user(
            username="inactiveuser",
            email="inactive@example.com",
            password="Password123!",
            phone_number="0987654321",
            is_active=False
        )

        # Set up API Client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Basic CRM Setup
        self.source = CRMService.create_lead_source(
            user=self.user, name="Web Search", description="Organic search"
        )
        self.inactive_source = LeadSource.objects.create(
            name="Inactive Source", created_by=self.user, is_active=False
        )

        self.pipeline = CRMService.create_pipeline(
            user=self.user, name="Sales Pipeline"
        )
        self.pipeline2 = CRMService.create_pipeline(
            user=self.user, name="Second Pipeline"
        )
        self.inactive_pipeline = Pipeline.objects.create(
            name="Inactive Pipeline", created_by=self.user, is_active=False
        )

        self.stage1 = CRMService.create_pipeline_stage(
            user=self.user, pipeline=self.pipeline, name="Stage 1", display_order=1
        )
        self.stage2 = CRMService.create_pipeline_stage(
            user=self.user, pipeline=self.pipeline, name="Stage 2", display_order=2
        )

        self.stage2_p2 = CRMService.create_pipeline_stage(
            user=self.user, pipeline=self.pipeline2, name="Pipeline 2 Stage 1", display_order=1
        )

        self.inactive_stage = PipelineStage.objects.create(
            pipeline=self.pipeline, name="Inactive Stage", display_order=3, is_active=False
        )


class CRMRegressionTests(CRMBaseTestCase):

    def test_1_unauthenticated_customer_list_rejected(self):
        unauth_client = APIClient()
        response = unauth_client.get("/api/crm/customers/")
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_15_lead_update_creates_lead_updated_audit_event(self):
        lead = CRMService.create_lead(
            user=self.user, name="Audit Lead", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        response = self.client.patch(f"/api/crm/leads/{lead.id}/", {
            "name": "Updated Audit Lead Name"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        audit_log = AuditLog.objects.filter(entity_id=lead.id, action="LEAD_UPDATED").first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.new_value["name"], "Updated Audit Lead Name")

    def test_16_lost_lead_creates_lead_lost_audit_event(self):
        lead = CRMService.create_lead(
            user=self.user, name="Lost Audit Lead", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        CRMService.mark_lead_lost(user=self.user, lead=lead, lost_reason="Budget cut")
        audit_log = AuditLog.objects.filter(entity_id=lead.id, action="LEAD_LOST").first()
        self.assertIsNotNone(audit_log)

    def test_17_reengagement_creates_lead_reengaged_audit_event(self):
        lead = CRMService.create_lead(
            user=self.user, name="Reengage Audit Lead", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        lost = CRMService.mark_lead_lost(user=self.user, lead=lead, lost_reason="Budget cut")
        CRMService.reengage_lead(user=self.user, lead=lost)
        audit_log = AuditLog.objects.filter(entity_id=lead.id, action="LEAD_REENGAGED").first()
        self.assertIsNotNone(audit_log)

    def test_18_patch_on_converted_lead_is_rejected(self):
        lead = CRMService.create_lead(
            user=self.user, name="Conv Patch Lead", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        CRMService.convert_lead(
            user=self.user, lead=lead,
            name="Cust", email="patchconv@example.com", phone="123",
        )
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.Status.CONVERTED)

        response = self.client.patch(
            f"/api/crm/leads/{lead.id}/", {"current_stage": str(self.stage2.id)}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        lead.refresh_from_db()
        self.assertEqual(lead.current_stage, self.stage1)

    def test_19_patch_lost_reason_on_active_lead_is_rejected(self):
        lead = CRMService.create_lead(
            user=self.user, name="Lost Reason Lead", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        response = self.client.patch(
            f"/api/crm/leads/{lead.id}/", {"lost_reason": "not actually lost"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_20_patch_with_inactive_source_is_rejected(self):
        lead = CRMService.create_lead(
            user=self.user, name="Inactive Source Lead", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        response = self.client.patch(
            f"/api/crm/leads/{lead.id}/", {"source": str(self.inactive_source.id)}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_21_unauthenticated_lead_list_rejected(self):
        unauth_client = APIClient()
        response = unauth_client.get("/api/crm/leads/")
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class QuotationWorkflowTestCase(CRMBaseTestCase):

    def setUp(self):
        super().setUp()

        self.lead = CRMService.create_lead(
            user=self.user,
            name="Quotation Lead",
            email="quotationlead@example.com",
            phone="9876543210",
            source=self.source,
            assigned_to=self.user,
            pipeline=self.pipeline,
            current_stage=self.stage1,
        )

    def test_01_create_retrieve_update_quotation(self):
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
        quotation_id = response.data["id"]

        resp_get = self.client.get(f"/api/crm/quotations/{quotation_id}/")
        self.assertEqual(resp_get.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_get.data["status"], "DRAFT")
        self.assertEqual(Decimal(resp_get.data["current_version_detail"]["total_amount"]), Decimal("200.00"))

        resp_patch = self.client.patch(
            f"/api/crm/quotations/{quotation_id}/update-draft/",
            {
                "terms": "Net 15",
                "line_items": [
                    {"description": "Product A", "quantity": 3, "unit_price": "50.00"},
                ],
            },
            format="json",
        )
        self.assertEqual(resp_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(resp_patch.data["current_version_detail"]["total_amount"]), Decimal("150.00"))

    def test_02_approval_workflow_required(self):
        pipeline_app = CRMService.create_pipeline(
            user=self.user, name="Approval Pipeline"
        )
        stage_approval = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pipeline_app,
            name="Stage Approval",
            display_order=1,
            requires_quotation=True,
            quotation_approval_required=True,
        )

        lead_app = CRMService.create_lead(
            user=self.user,
            name="Approval Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pipeline_app,
            current_stage=stage_approval,
        )

        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead_app,
            line_items=[{"description": "Item 1", "quantity": 1, "unit_price": "500.00"}],
        )

        resp_send_fail = self.client.post(f"/api/crm/quotations/{q.id}/send/")
        self.assertEqual(resp_send_fail.status_code, status.HTTP_400_BAD_REQUEST)

        resp_submit = self.client.post(f"/api/crm/quotations/{q.id}/submit/")
        self.assertEqual(resp_submit.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_submit.data["status"], "PENDING_APPROVAL")

        # Approve using a distinct manager user
        manager_user = User.objects.create_user(
            username="manager_approver",
            email="approver@example.com",
            password="Password123!",
            role=self.role,
        )
        manager_client = APIClient()
        manager_client.force_authenticate(user=manager_user)

        resp_approve = manager_client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp_approve.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_approve.data["status"], "APPROVED")

        resp_send = self.client.post(f"/api/crm/quotations/{q.id}/send/")
        self.assertEqual(resp_send.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_send.data["status"], "SENT")

    def test_03_versioning_revision_history(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "v1 Item", "quantity": 1, "unit_price": "100.00"}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)

        resp_rev = self.client.post(
            f"/api/crm/quotations/{q.id}/revision/",
            {
                "terms": "Revised Terms",
                "line_items": [{"description": "v2 Item", "quantity": 2, "unit_price": "150.00"}],
            },
            format="json",
        )
        self.assertEqual(resp_rev.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp_rev.data["current_version_detail"]["version_number"], 2)
        self.assertEqual(len(resp_rev.data["all_versions"]), 2)

    def test_04_followup_integration_event_on_send(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": "100.00"}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)

        event = QuotationIntegrationEvent.objects.filter(quotation=q).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "quotation.followup_required")
        self.assertEqual(event.payload["lead_id"], str(self.lead.id))
        self.assertEqual(event.payload["quotation_id"], str(q.id))

    def test_05_accept_quotation_converts_lead(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": "100.00"}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q = QuotationService.send_quotation(user=self.user, quotation=q)

        resp_accept = self.client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp_accept.status_code, status.HTTP_200_OK)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.CONVERTED)
        self.assertIsNotNone(Customer.objects.filter(lead=self.lead).first())

    def test_06_reject_quotation_marks_lead_lost(self):
        q = QuotationService.create_quotation(
            user=self.user,
            lead=self.lead,
            line_items=[{"description": "Item", "quantity": 1, "unit_price": "100.00"}],
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q = QuotationService.send_quotation(user=self.user, quotation=q)

        resp_rej = self.client.post(
            f"/api/crm/quotations/{q.id}/reject/",
            {"rejection_reason": "Too expensive"},
            format="json",
        )
        self.assertEqual(resp_rej.status_code, status.HTTP_200_OK)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.LOST)
        self.assertIn("Too expensive", self.lead.lost_reason)

    def test_07_dynamic_pipeline_quotation_stage_enforcement(self):
        pipeline_q = CRMService.create_pipeline(
            user=self.user, name="Quotation Pipeline"
        )
        stage_q = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pipeline_q,
            name="Quotation Required Stage",
            display_order=1,
            requires_quotation=True,
        )

        lead_q = CRMService.create_lead(
            user=self.user,
            name="Gated Lead",
            email="gated@example.com",
            phone="1112223333",
            source=self.source,
            assigned_to=self.user,
            pipeline=pipeline_q,
            current_stage=stage_q,
        )

        with self.assertRaises(ValidationError):
            CRMService.convert_lead(
                user=self.user,
                lead=lead_q,
                name=lead_q.name,
                email="gated@example.com",
                phone="1112223333",
            )

        q = QuotationService.create_quotation(user=self.user, lead=lead_q)
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q = QuotationService.send_quotation(user=self.user, quotation=q)
        QuotationService.accept_quotation(user=self.user, quotation=q)

        lead_q.refresh_from_db()
        self.assertEqual(lead_q.status, Lead.Status.CONVERTED)

    def test_08_duplicate_send_prevented(self):
        q = QuotationService.create_quotation(user=self.user, lead=self.lead)
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation(user=self.user, quotation=q)

        # Re-sending an already SENT quotation should fail
        resp_resend = self.client.post(f"/api/crm/quotations/{q.id}/send/")
        self.assertEqual(resp_resend.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify only 1 event was generated
        event_count = QuotationIntegrationEvent.objects.filter(
            quotation=q,
            quotation_version_number=1,
            event_type="quotation.followup_required",
        ).count()
        self.assertEqual(event_count, 1)

    def test_09_self_approval_prevented(self):
        pipeline_app = CRMService.create_pipeline(
            user=self.user, name="Approval Pipeline 2"
        )
        stage_approval = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pipeline_app,
            name="Stage Approval 2",
            display_order=1,
            requires_quotation=True,
            quotation_approval_required=True,
        )
        lead_app = CRMService.create_lead(
            user=self.user,
            name="Approval Lead 2",
            source=self.source,
            assigned_to=self.user,
            pipeline=pipeline_app,
            current_stage=stage_approval,
        )
        q = QuotationService.create_quotation(user=self.user, lead=lead_app)

        # Agent submits quotation for approval
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)

        # Submitting agent (non-superuser) attempting to approve their own quotation should fail
        with self.assertRaises(ValidationError):
            QuotationService.approve_quotation(reviewer_user=self.user, quotation=q)

    def test_10_complete_self_approval_and_resubmit_rules(self):
        pipeline_app = CRMService.create_pipeline(user=self.user, name="Approval Pipeline 3")
        stage_approval = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pipeline_app,
            name="Stage Approval 3",
            display_order=1,
            requires_quotation=True,
            quotation_approval_required=True,
        )
        lead_app = CRMService.create_lead(
            user=self.user,
            name="Approval Lead 3",
            source=self.source,
            assigned_to=self.user,
            pipeline=pipeline_app,
            current_stage=stage_approval,
        )
        q = QuotationService.create_quotation(user=self.user, lead=lead_app)

        # User A submits quotation for approval
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)

        # User A attempts to approve -> Must be rejected (400 Bad Request)
        resp_self_approve = self.client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp_self_approve.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("submitting agent cannot approve their own quotation", resp_self_approve.data["detail"])

        # User B (Manager) approves User A's quotation -> Must succeed
        user_b = User.objects.create_user(
            username="manager_b",
            email="manager_b@example.com",
            password="Password123!",
            phone_number="5551112222",
            role=self.role,
        )
        client_b = APIClient()
        client_b.force_authenticate(user=user_b)

        resp_manager_b_approve = client_b.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp_manager_b_approve.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_manager_b_approve.data["status"], "APPROVED")

        # An already APPROVED quotation cannot be submitted again -> Must be rejected (400 Bad Request)
        resp_resubmit = self.client.post(f"/api/crm/quotations/{q.id}/submit/")
        self.assertEqual(resp_resubmit.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot be submitted for approval", resp_resubmit.data["detail"])

    def test_11_token_identity_and_approval_persistence(self):
        pipeline_app = CRMService.create_pipeline(user=self.user, name="Approval Pipeline 4")
        stage_approval = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pipeline_app,
            name="Stage Approval 4",
            display_order=1,
            requires_quotation=True,
            quotation_approval_required=True,
        )
        lead_app = CRMService.create_lead(
            user=self.user,
            name="Approval Lead 4",
            source=self.source,
            assigned_to=self.user,
            pipeline=pipeline_app,
            current_stage=stage_approval,
        )
        q = QuotationService.create_quotation(user=self.user, lead=lead_app)

        # 1. User A (self.user) submits
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        approval = QuotationApproval.objects.filter(version=q.current_version, decision="PENDING").first()
        self.assertEqual(approval.submitted_by, self.user)
        self.assertIsNone(approval.reviewed_by)

        # 2. User B (Manager) approves
        user_b = User.objects.create_user(
            username="manager_c",
            email="manager_c@example.com",
            password="Password123!",
            phone_number="5553334444",
            role=self.role,
        )
        client_b = APIClient()
        client_b.force_authenticate(user=user_b)
        resp_approve = client_b.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp_approve.status_code, status.HTTP_200_OK)

        approval.refresh_from_db()
        self.assertEqual(approval.submitted_by, self.user)
        self.assertEqual(approval.reviewed_by, user_b)
        self.assertEqual(approval.decision, "APPROVED")

        # 3. Superuser self-approval override test
        superuser = User.objects.create_superuser(
            username="super_admin",
            email="superadmin@example.com",
            password="Password123!",
            phone_number="5555556666",
        )
        q_super = QuotationService.create_quotation(user=superuser, lead=lead_app)
        QuotationService.submit_quotation_for_approval(user=superuser, quotation=q_super)
        client_super = APIClient()
        client_super.force_authenticate(user=superuser)

        resp_super_self = client_super.post(f"/api/crm/quotations/{q_super.id}/approve/")
        self.assertEqual(resp_super_self.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_super_self.data["status"], "APPROVED")

    def test_12_employee_and_manager_quotation_permission_matrix(self):
        pipeline_matrix = CRMService.create_pipeline(user=self.user, name="Matrix Pipeline")
        stage_matrix = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pipeline_matrix,
            name="Matrix Stage",
            display_order=1,
            requires_quotation=True,
            quotation_approval_required=True,
        )
        lead_matrix = CRMService.create_lead(
            user=self.user,
            name="Matrix Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pipeline_matrix,
            current_stage=stage_matrix,
        )

        # 1. Create Employee role with ONLY Employee permissions
        emp_role = Role.objects.create(rolename="EmployeeRole")
        emp_perms = Permission.objects.filter(
            codename__in=[
                "view_lead", "add_lead", "change_lead",
                "view_quotation", "add_quotation", "change_quotation", "submit_quotation",
            ]
        )
        emp_role.permissions.set(emp_perms)

        employee = User.objects.create_user(
            username="emp_user",
            email="emp_user@example.com",
            password="Password123!",
            phone_number="5559990001",
            role=emp_role,
        )

        client_emp = APIClient()
        client_emp.force_authenticate(user=employee)

        # Employee creates quotation -> Allowed (201)
        resp_emp_create = client_emp.post("/api/crm/quotations/", {"lead": str(lead_matrix.id), "terms": "Emp Terms"})
        self.assertEqual(resp_emp_create.status_code, status.HTTP_201_CREATED)
        q_id = resp_emp_create.data["id"]

        # Employee views quotation list & detail -> Allowed (200)
        resp_emp_list = client_emp.get("/api/crm/quotations/")
        self.assertEqual(resp_emp_list.status_code, status.HTTP_200_OK)

        resp_emp_detail = client_emp.get(f"/api/crm/quotations/{q_id}/")
        self.assertEqual(resp_emp_detail.status_code, status.HTTP_200_OK)

        # Employee patches draft quotation -> Allowed (200)
        resp_emp_patch = client_emp.patch(f"/api/crm/quotations/{q_id}/update-draft/", {"terms": "Updated Terms"})
        self.assertEqual(resp_emp_patch.status_code, status.HTTP_200_OK)

        # Employee submits quotation -> Allowed (200)
        resp_emp_submit = client_emp.post(f"/api/crm/quotations/{q_id}/submit/")
        self.assertEqual(resp_emp_submit.status_code, status.HTTP_200_OK)

        # Employee Manager-only actions -> DENIED (403 Forbidden)
        self.assertEqual(client_emp.post(f"/api/crm/quotations/{q_id}/approve/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(client_emp.post(f"/api/crm/quotations/{q_id}/reject-approval/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(client_emp.post(f"/api/crm/quotations/{q_id}/send/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(client_emp.post(f"/api/crm/quotations/{q_id}/revision/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(client_emp.post(f"/api/crm/quotations/{q_id}/accept/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(client_emp.post(f"/api/crm/quotations/{q_id}/reject/", {"rejection_reason": "Price"}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(client_emp.delete(f"/api/crm/quotations/{q_id}/").status_code, status.HTTP_403_FORBIDDEN)

        # 2. Manager Role with Manager permissions
        mgr_role = Role.objects.create(rolename="ManagerRole")
        mgr_perms = Permission.objects.filter(
            codename__in=[
                "view_lead", "add_lead", "change_lead",
                "view_quotation", "add_quotation", "change_quotation", "submit_quotation",
                "approve_quotation", "send_quotation", "request_quotation_revision",
                "accept_quotation", "reject_quotation", "delete_quotation",
            ]
        )
        mgr_role.permissions.set(mgr_perms)

        manager = User.objects.create_user(
            username="mgr_user",
            email="mgr_user@example.com",
            password="Password123!",
            phone_number="5559990002",
            role=mgr_role,
        )

        client_mgr = APIClient()
        client_mgr.force_authenticate(user=manager)

        # Manager approves Employee's submitted quotation -> Allowed (200)
        resp_mgr_approve = client_mgr.post(f"/api/crm/quotations/{q_id}/approve/")
        self.assertEqual(resp_mgr_approve.status_code, status.HTTP_200_OK)

        # Manager sends quotation -> Allowed (200)
        resp_mgr_send = client_mgr.post(f"/api/crm/quotations/{q_id}/send/")
        self.assertEqual(resp_mgr_send.status_code, status.HTTP_200_OK)

        # Manager accepts quotation -> Allowed (200)
        resp_mgr_accept = client_mgr.post(f"/api/crm/quotations/{q_id}/accept/")
        self.assertEqual(resp_mgr_accept.status_code, status.HTTP_200_OK)
