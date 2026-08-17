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
                "add_quotation", "change_quotation", "view_quotation", "delete_quotation",
                "generate_quotation_pdf"
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

        from rest_framework.exceptions import PermissionDenied
        with self.assertRaises((ValidationError, PermissionDenied)):
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

        # User A attempts to approve -> Must be rejected (403 Forbidden without approve_own_quotation)
        resp_self_approve = self.client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp_self_approve.status_code, status.HTTP_403_FORBIDDEN)
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

        # 1. Create Employee role with Employee permissions
        emp_role = Role.objects.create(rolename="EmployeeRole")
        emp_perms = Permission.objects.filter(
            codename__in=[
                "view_lead", "add_lead", "change_lead",
                "view_quotation", "add_quotation", "change_quotation", "submit_quotation",
                "send_quotation", "request_quotation_revision", "generate_quotation_pdf",
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

        # Employee Approval-related actions -> DENIED (403 Forbidden)
        self.assertEqual(client_emp.post(f"/api/crm/quotations/{q_id}/approve/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(client_emp.post(f"/api/crm/quotations/{q_id}/reject-approval/").status_code, status.HTTP_403_FORBIDDEN)
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
                "generate_quotation_pdf",
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

        # Employee can send quotation AFTER approval -> Allowed (200)
        resp_emp_send = client_emp.post(f"/api/crm/quotations/{q_id}/send/")
        self.assertEqual(resp_emp_send.status_code, status.HTTP_200_OK)

        # Employee can create revision AFTER customer negotiation -> Allowed (201)
        resp_emp_rev = client_emp.post(f"/api/crm/quotations/{q_id}/revision/", {"revision_reason": "Customer discount"})
        self.assertEqual(resp_emp_rev.status_code, status.HTTP_201_CREATED)

        # Submit v2 -> Manager approves v2 -> Employee sends v2 -> Manager accepts v2
        client_emp.post(f"/api/crm/quotations/{q_id}/submit/")
        client_mgr.post(f"/api/crm/quotations/{q_id}/approve/")
        client_emp.post(f"/api/crm/quotations/{q_id}/send/")
        resp_mgr_accept = client_mgr.post(f"/api/crm/quotations/{q_id}/accept/")
        self.assertEqual(resp_mgr_accept.status_code, status.HTTP_200_OK)

    def test_13_unauthenticated_requests_rejection(self):
        client_anon = APIClient()

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
            if method == "GET":
                resp = client_anon.get(url)
            else:
                resp = client_anon.post(url, {})
            self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_14_invalid_state_transitions_and_locked_versions(self):
        pipeline_inv = CRMService.create_pipeline(user=self.user, name="Invalid Pipeline")
        stage_inv = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pipeline_inv,
            name="Invalid Stage",
            display_order=1,
            requires_quotation=True,
            quotation_approval_required=True,
        )
        lead_inv = CRMService.create_lead(
            user=self.user,
            name="Invalid Lead",
            source=self.source,
            assigned_to=self.user,
            pipeline=pipeline_inv,
            current_stage=stage_inv,
        )

        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead_inv,
            line_items=[{"description": "Item 1", "quantity": 1, "unit_price": 1000}],
        )

        client = APIClient()
        client.force_authenticate(user=self.user)

        # 1. Cannot approve DRAFT quotation
        resp_app = client.post(f"/api/crm/quotations/{q.id}/approve/")
        self.assertEqual(resp_app.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Cannot send DRAFT quotation
        resp_send = client.post(f"/api/crm/quotations/{q.id}/send/")
        self.assertEqual(resp_send.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Cannot accept DRAFT quotation
        resp_acc = client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp_acc.status_code, status.HTTP_400_BAD_REQUEST)

        # Submit -> PENDING_APPROVAL
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)

        # 4. Cannot accept PENDING_APPROVAL quotation
        resp_acc_pending = client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp_acc_pending.status_code, status.HTTP_400_BAD_REQUEST)

    def test_15_query_count_and_large_dataset_performance(self):
        pipeline_perf = CRMService.create_pipeline(user=self.user, name="Perf Pipeline")
        stage_perf = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pipeline_perf,
            name="Perf Stage",
            display_order=1,
        )

        # Bulk create 15 leads and 15 quotations
        for i in range(15):
            l = CRMService.create_lead(
                user=self.user,
                name=f"Perf Lead {i}",
                email=f"perf{i}@example.com",
                phone=f"555000{i:04d}",
                source=self.source,
                assigned_to=self.user,
                pipeline=pipeline_perf,
                current_stage=stage_perf,
            )
            QuotationService.create_quotation(
                user=self.user,
                lead=l,
                line_items=[
                    {"description": f"Item A {i}", "quantity": 2, "unit_price": 500},
                    {"description": f"Item B {i}", "quantity": 1, "unit_price": 1500},
                ],
            )

        client = APIClient()
        client.force_authenticate(user=self.user)

        # Fetch quotation list and verify bounded query count (7 queries for 15+ items)
        with self.assertNumQueries(7):
            resp = client.get("/api/crm/quotations/")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            self.assertGreaterEqual(len(resp.data), 15)

    def test_16_quotation_pdf_export_and_validation(self):
        pipeline_pdf = CRMService.create_pipeline(user=self.user, name="PDF Pipeline")
        stage_pdf = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pipeline_pdf,
            name="PDF Stage",
            display_order=1,
            requires_quotation=True,
            quotation_approval_required=True,
        )
        lead_pdf = CRMService.create_lead(
            user=self.user,
            name="PDF Lead",
            email="pdflead@example.com",
            phone="5551112222",
            source=self.source,
            assigned_to=self.user,
            pipeline=pipeline_pdf,
            current_stage=stage_pdf,
        )
        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead_pdf,
            terms="Net 30",
            notes="PDF Test Notes",
            line_items=[
                {"description": "Product A", "quantity": 2, "unit_price": 500},
                {"description": "Product B", "quantity": 1, "unit_price": 1000},
            ],
        )

        client = APIClient()
        client.force_authenticate(user=self.user)

        # 1. DRAFT PDF generation should be blocked (HTTP 400)
        resp_draft_pdf = client.get(f"/api/crm/quotations/{q.id}/pdf/")
        self.assertEqual(resp_draft_pdf.status_code, status.HTTP_400_BAD_REQUEST)

        # Submit -> PENDING_APPROVAL
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)

        # 2. PENDING_APPROVAL PDF generation should be blocked (HTTP 400)
        resp_pending_pdf = client.get(f"/api/crm/quotations/{q.id}/pdf/")
        self.assertEqual(resp_pending_pdf.status_code, status.HTTP_400_BAD_REQUEST)

        # Approve -> APPROVED
        mgr_role = Role.objects.create(rolename="PDFRole")
        mgr_role.permissions.set(Permission.objects.filter(codename__in=["approve_quotation", "generate_quotation_pdf"]))
        mgr = User.objects.create_user(username="pdf_mgr", email="pdfmgr@example.com", password="Password123!", role=mgr_role)
        QuotationService.approve_quotation(reviewer_user=mgr, quotation=q)

        q.refresh_from_db()
        self.assertIsNotNone(q.current_version.approved_at)

        # 3. APPROVED PDF generation allowed (HTTP 200)
        resp_pdf = client.get(f"/api/crm/quotations/{q.id}/pdf/")
        self.assertEqual(resp_pdf.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_pdf["Content-Type"], "application/pdf")
        self.assertIn(f"{q.quotation_number}_v1.pdf", resp_pdf["Content-Disposition"])
        self.assertTrue(len(resp_pdf.content) > 0)

        # Verify AuditLog created for PDF generation
        pdf_audit = AuditLog.objects.filter(entity_id=q.id, action="QUOTATION_PDF_GENERATED").first()
        self.assertIsNotNone(pdf_audit)

        # 4. Generate PDF for specific version parameter
        resp_spec_pdf = client.get(f"/api/crm/quotations/{q.id}/pdf/?version=1")
        self.assertEqual(resp_spec_pdf.status_code, status.HTTP_200_OK)

        # Invalid version parameter -> 404
        resp_inv_v = client.get(f"/api/crm/quotations/{q.id}/pdf/?version=99")
        self.assertEqual(resp_inv_v.status_code, status.HTTP_404_NOT_FOUND)

    def test_17_quotation_email_delivery_and_revision_tracking(self):
        from django.core import mail

        pipeline_email = CRMService.create_pipeline(user=self.user, name="Email Pipeline")
        stage_email = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pipeline_email,
            name="Email Stage",
            display_order=1,
            requires_quotation=True,
            quotation_approval_required=False,
        )
        lead_email = CRMService.create_lead(
            user=self.user,
            name="Email Lead",
            email="cust_email@example.com",
            phone="5553334444",
            source=self.source,
            assigned_to=self.user,
            pipeline=pipeline_email,
            current_stage=stage_email,
        )

        q = QuotationService.create_quotation(
            user=self.user,
            lead=lead_email,
            terms="Initial Terms",
            line_items=[{"description": "Item 1", "quantity": 1, "unit_price": 500}],
        )

        # Auto-approve
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertEqual(q.status, "APPROVED")
        self.assertIsNotNone(q.current_version.approved_at)

        client = APIClient()
        client.force_authenticate(user=self.user)

        # Send email API
        mail.outbox = []
        resp_email = client.post(
            f"/api/crm/quotations/{q.id}/send-email/",
            {
                "recipient_email": "cust_email@example.com",
                "subject": "Custom Proposal Subject",
                "body": "Here is your proposal.",
            }
        )
        self.assertEqual(resp_email.status_code, status.HTTP_200_OK)
        q.refresh_from_db()
        self.assertEqual(q.status, "SENT")
        self.assertEqual(q.current_version.sent_to, "cust_email@example.com")
        self.assertIsNotNone(q.current_version.sent_at)

        # Verify email outbox
        self.assertEqual(len(mail.outbox), 1)
        sent_msg = mail.outbox[0]
        self.assertEqual(sent_msg.to, ["cust_email@example.com"])
        self.assertEqual(sent_msg.subject, "Custom Proposal Subject")
        self.assertEqual(len(sent_msg.attachments), 1)
        att_name, att_bytes, att_mime = sent_msg.attachments[0]
        self.assertEqual(att_name, f"{q.quotation_number}_v1.pdf")
        self.assertEqual(att_mime, "application/pdf")

        # Verify AuditLog & Activity
        email_audit = AuditLog.objects.filter(entity_id=q.id, action="QUOTATION_EMAIL_SENT").first()
        self.assertIsNotNone(email_audit)

        email_act = Activity.objects.filter(quotation=q, activity_type="QUOTATION_EMAIL_SENT").first()
        self.assertIsNotNone(email_act)

        # Create Revision with revision_reason
        resp_rev = client.post(
            f"/api/crm/quotations/{q.id}/revision/",
            {
                "revision_reason": "Customer requested discount",
                "terms": "Revised Terms",
                "line_items": [{"description": "Item 1", "quantity": 1, "unit_price": 450}],
            },
            format="json",
        )
        self.assertEqual(resp_rev.status_code, status.HTTP_201_CREATED)
        q.refresh_from_db()
        self.assertEqual(q.current_version.version_number, 2)
        self.assertEqual(q.current_version.revision_reason, "Customer requested discount")

        # Auto-approve v2 and email v2
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        client.post(f"/api/crm/quotations/{q.id}/send-email/", {})

        # Accept v2
        resp_accept = client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp_accept.status_code, status.HTTP_200_OK)
        q.refresh_from_db()
        self.assertEqual(q.status, "ACCEPTED")
        self.assertEqual(q.accepted_version.version_number, 2)

    def test_18_quotation_self_approval_and_rbac_cases(self):
        """
        Covers RBAC cases A, B, C, D, E and dynamic permission changes.
        """
        # Pipeline requiring approval
        pipeline = CRMService.create_pipeline(user=self.user, name="RBAC Pipeline")
        stage = CRMService.create_pipeline_stage(
            user=self.user,
            pipeline=pipeline,
            name="RBAC Stage",
            display_order=1,
            requires_quotation=True,
            quotation_approval_required=True,
        )
        lead = CRMService.create_lead(
            user=self.user, name="RBAC Lead", email="rbac@example.com", phone="5550001111",
            source=self.source, assigned_to=self.user, pipeline=pipeline, current_stage=stage,
        )

        # 1. Employee setup (without approve_quotation or approve_own_quotation)
        emp_role = Role.objects.create(rolename="EmpRBAC")
        emp_role.permissions.set(Permission.objects.filter(codename__in=["view_quotation", "add_quotation", "submit_quotation", "send_quotation"]))
        emp = User.objects.create_user(username="emp_rbac", email="emp_rbac@example.com", password="Password123!", phone_number="5558880001", role=emp_role)

        # Employee creates & submits quotation
        q_emp = QuotationService.create_quotation(user=emp, lead=lead, line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}])
        QuotationService.submit_quotation_for_approval(user=emp, quotation=q_emp)

        client_emp = APIClient()
        client_emp.force_authenticate(user=emp)

        # CASE A: Employee tries to approve -> 403 Forbidden
        resp_case_a = client_emp.post(f"/api/crm/quotations/{q_emp.id}/approve/")
        self.assertEqual(resp_case_a.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Manager without approve_own_quotation
        mgr_no_own_role = Role.objects.create(rolename="MgrNoOwn")
        mgr_no_own_role.permissions.set(Permission.objects.filter(codename__in=["view_quotation", "add_quotation", "submit_quotation", "approve_quotation"]))
        mgr_no_own = User.objects.create_user(username="mgr_no_own", email="mgr_no_own@example.com", password="Password123!", phone_number="5558880002", role=mgr_no_own_role)

        # Manager creates & submits their OWN quotation
        q_mgr = QuotationService.create_quotation(user=mgr_no_own, lead=lead, line_items=[{"description": "Item", "quantity": 1, "unit_price": 200}])
        QuotationService.submit_quotation_for_approval(user=mgr_no_own, quotation=q_mgr)

        client_mgr_no_own = APIClient()
        client_mgr_no_own.force_authenticate(user=mgr_no_own)

        # CASE B: Manager tries self-approval without approve_own_quotation -> 403 Forbidden
        resp_case_b = client_mgr_no_own.post(f"/api/crm/quotations/{q_mgr.id}/approve/")
        self.assertEqual(resp_case_b.status_code, status.HTTP_403_FORBIDDEN)

        # CASE D: Manager approves Employee's quotation (not self) -> 200 OK
        resp_case_d = client_mgr_no_own.post(f"/api/crm/quotations/{q_emp.id}/approve/")
        self.assertEqual(resp_case_d.status_code, status.HTTP_200_OK)

        # 3. Manager WITH approve_own_quotation
        mgr_own_role = Role.objects.create(rolename="MgrOwn")
        mgr_own_role.permissions.set(Permission.objects.filter(codename__in=["view_quotation", "add_quotation", "submit_quotation", "approve_quotation", "approve_own_quotation"]))
        mgr_own = User.objects.create_user(username="mgr_own", email="mgr_own@example.com", password="Password123!", phone_number="5558880003", role=mgr_own_role)

        q_mgr_own = QuotationService.create_quotation(user=mgr_own, lead=lead, line_items=[{"description": "Item", "quantity": 1, "unit_price": 300}])
        QuotationService.submit_quotation_for_approval(user=mgr_own, quotation=q_mgr_own)

        client_mgr_own = APIClient()
        client_mgr_own.force_authenticate(user=mgr_own)

        # CASE C: Manager with approve_own_quotation approves their OWN quotation -> 200 OK
        resp_case_c = client_mgr_own.post(f"/api/crm/quotations/{q_mgr_own.id}/approve/")
        self.assertEqual(resp_case_c.status_code, status.HTTP_200_OK)

        # CASE E: Admin (superuser) approves another quotation
        q_admin_target = QuotationService.create_quotation(user=emp, lead=lead, line_items=[{"description": "Item", "quantity": 1, "unit_price": 400}])
        QuotationService.submit_quotation_for_approval(user=emp, quotation=q_admin_target)

        client_admin = APIClient()
        client_admin.force_authenticate(user=self.user)
        resp_case_e = client_admin.post(f"/api/crm/quotations/{q_admin_target.id}/approve/")
        self.assertEqual(resp_case_e.status_code, status.HTTP_200_OK)

        # 4. Dynamic Permission Change Test (Removing approve_own_quotation immediately blocks)
        q_dynamic = QuotationService.create_quotation(user=mgr_own, lead=lead, line_items=[{"description": "Item", "quantity": 1, "unit_price": 500}])
        QuotationService.submit_quotation_for_approval(user=mgr_own, quotation=q_dynamic)

        # Remove approve_own_quotation permission from mgr_own_role
        mgr_own_role.permissions.remove(Permission.objects.get(codename="approve_own_quotation"))

        # Self-approval attempt should now be DENIED (403)
        resp_dynamic = client_mgr_own.post(f"/api/crm/quotations/{q_dynamic.id}/approve/")
        self.assertEqual(resp_dynamic.status_code, status.HTTP_403_FORBIDDEN)

    def test_19_invalid_state_transitions_and_data_integrity(self):
        """
        Verifies invalid state machine transitions return HTTP 400 and do not mutate DB.
        """
        pipeline_sm = CRMService.create_pipeline(user=self.user, name="SM Pipeline")
        stage_sm = CRMService.create_pipeline_stage(
            user=self.user, pipeline=pipeline_sm, name="SM Stage", display_order=1, quotation_approval_required=True,
        )
        lead_sm = CRMService.create_lead(
            user=self.user, name="SM Lead", email="sm@example.com", phone="5552223333",
            source=self.source, assigned_to=self.user, pipeline=pipeline_sm, current_stage=stage_sm,
        )
        q = QuotationService.create_quotation(
            user=self.user, lead=lead_sm, line_items=[{"description": "Base", "quantity": 1, "unit_price": 100}]
        )

        client = APIClient()
        client.force_authenticate(user=self.user)

        # DRAFT state -> invalid actions
        self.assertEqual(client.post(f"/api/crm/quotations/{q.id}/accept/").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(client.post(f"/api/crm/quotations/{q.id}/reject/", {"rejection_reason": "No"}).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(client.post(f"/api/crm/quotations/{q.id}/send/").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(client.get(f"/api/crm/quotations/{q.id}/pdf/").status_code, status.HTTP_400_BAD_REQUEST)

        # DB status should still be DRAFT
        q.refresh_from_db()
        self.assertEqual(q.status, "DRAFT")

        # Submit -> PENDING_APPROVAL
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()
        self.assertEqual(q.status, "PENDING_APPROVAL")

        # PENDING_APPROVAL -> invalid actions
        self.assertEqual(client.post(f"/api/crm/quotations/{q.id}/send/").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(client.post(f"/api/crm/quotations/{q.id}/accept/").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(client.get(f"/api/crm/quotations/{q.id}/pdf/").status_code, status.HTTP_400_BAD_REQUEST)

        # Approve -> APPROVED
        mgr_role = Role.objects.create(rolename="MgrSM")
        mgr_role.permissions.set(Permission.objects.filter(codename__in=["approve_quotation"]))
        mgr = User.objects.create_user(username="mgr_sm", email="mgr_sm@example.com", password="Password123!", phone_number="5558880004", role=mgr_role)
        QuotationService.approve_quotation(reviewer_user=mgr, quotation=q)
        q.refresh_from_db()
        self.assertEqual(q.status, "APPROVED")

        # APPROVED -> submit again is invalid
        self.assertEqual(client.post(f"/api/crm/quotations/{q.id}/submit/").status_code, status.HTTP_400_BAD_REQUEST)

    def test_20_multi_version_historical_immutability_and_revision_chain(self):
        """
        Verifies v1 -> v2 -> v3 lifecycle, historical immutability of line items/totals/sent_to,
        and that accepting v2 sets accepted_version strictly to v2 without corrupting v1/v3.
        """
        lead_rev = CRMService.create_lead(
            user=self.user, name="Rev Lead", email="rev@example.com", phone="5553334444",
            source=self.source, assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1,
        )
        q = QuotationService.create_quotation(
            user=self.user, lead=lead_rev, terms="Terms v1", notes="Notes v1",
            line_items=[{"description": "Item v1", "quantity": 2, "unit_price": 500}],
        )

        client = APIClient()
        client.force_authenticate(user=self.user)

        # Approve and send v1
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation_email(user=self.user, quotation=q, recipient_email="rev@example.com")
        q.refresh_from_db()
        self.assertEqual(q.status, "SENT")
        v1 = q.current_version
        self.assertEqual(v1.version_number, 1)
        self.assertEqual(v1.sent_to, "rev@example.com")

        # Employee creates v2 revision
        resp_v2 = client.post(
            f"/api/crm/quotations/{q.id}/revision/",
            {
                "revision_reason": "Discount requested by client",
                "terms": "Terms v2",
                "notes": "Notes v2",
                "line_items": [{"description": "Item v2", "quantity": 2, "unit_price": 400}],
            },
            format="json",
        )
        self.assertEqual(resp_v2.status_code, status.HTTP_201_CREATED)
        q.refresh_from_db()
        v2 = q.current_version
        self.assertEqual(v2.version_number, 2)
        self.assertEqual(v2.revision_reason, "Discount requested by client")

        # Verify v1 historical immutability
        v1.refresh_from_db()
        self.assertEqual(v1.status, "REVISED")
        self.assertEqual(v1.terms, "Terms v1")
        self.assertEqual(v1.notes, "Notes v1")
        self.assertEqual(v1.sent_to, "rev@example.com")
        self.assertEqual(v1.total_amount, Decimal("1000.00"))
        self.assertEqual(v1.line_items.first().unit_price, Decimal("500.00"))

        # v2 cannot be sent before approval (400)
        self.assertEqual(client.post(f"/api/crm/quotations/{q.id}/send-email/").status_code, status.HTTP_400_BAD_REQUEST)

        # Approve and send v2
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        QuotationService.send_quotation_email(user=self.user, quotation=q)
        q.refresh_from_db()

        # Employee creates v3 revision from v2
        resp_v3 = client.post(
            f"/api/crm/quotations/{q.id}/revision/",
            {
                "revision_reason": "Add service pack",
                "terms": "Terms v3",
                "line_items": [
                    {"description": "Item v2", "quantity": 2, "unit_price": 400},
                    {"description": "Service Pack", "quantity": 1, "unit_price": 300},
                ],
            },
            format="json",
        )
        self.assertEqual(resp_v3.status_code, status.HTTP_201_CREATED)
        q.refresh_from_db()
        v3 = q.current_version
        self.assertEqual(v3.version_number, 3)

        # Accept v2 explicitly
        v2.status = "SENT"
        v2.save()
        q.current_version = v2
        q.status = "SENT"
        q.save()

        resp_accept = client.post(f"/api/crm/quotations/{q.id}/accept/")
        self.assertEqual(resp_accept.status_code, status.HTTP_200_OK)
        q.refresh_from_db()
        self.assertEqual(q.accepted_version, v2)
        self.assertEqual(q.accepted_version.version_number, 2)

        # Verify historical v1 and v3 were not corrupted
        v1.refresh_from_db()
        v3.refresh_from_db()
        self.assertEqual(v1.version_number, 1)
        self.assertEqual(v3.version_number, 3)
        self.assertNotEqual(v1.status, "ACCEPTED")

    def test_21_edge_cases_email_pdf_and_api_validation(self):
        """
        Tests API validation, malformed inputs, nonexistent resources, and AuditLog records.
        """
        client = APIClient()
        client.force_authenticate(user=self.user)

        # 404 for non-existent quotation
        fake_uuid = "00000000-0000-0000-0000-000000000099"
        self.assertEqual(client.get(f"/api/crm/quotations/{fake_uuid}/pdf/").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(client.post(f"/api/crm/quotations/{fake_uuid}/send-email/").status_code, status.HTTP_404_NOT_FOUND)

        # Create valid quotation for validation tests
        lead_val = CRMService.create_lead(
            user=self.user, name="Val Lead", email="val@example.com", phone="5554445555",
            source=self.source, assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1,
        )
        q = QuotationService.create_quotation(
            user=self.user, lead=lead_val, line_items=[{"description": "Item", "quantity": 1, "unit_price": 100}]
        )
        QuotationService.submit_quotation_for_approval(user=self.user, quotation=q)
        q.refresh_from_db()

        # PDF download with invalid version format -> 400
        self.assertEqual(client.get(f"/api/crm/quotations/{q.id}/pdf/?version=abc").status_code, status.HTTP_400_BAD_REQUEST)
        # PDF download with nonexistent version number -> 404
        self.assertEqual(client.get(f"/api/crm/quotations/{q.id}/pdf/?version=99").status_code, status.HTTP_404_NOT_FOUND)

        # Send email with invalid version format parameter -> 400
        self.assertEqual(client.post(f"/api/crm/quotations/{q.id}/send-email/", {"version": "xyz"}).status_code, status.HTTP_400_BAD_REQUEST)

    def test_22_real_life_business_scenarios(self):
        """
        Tests realistic end-to-end sales business scenarios 1 through 12.
        """
        client = APIClient()

        # SCENARIO 1: Single Manager small company with approve_own_quotation
        sm_mgr_role = Role.objects.create(rolename="SmMgrRole")
        sm_mgr_role.permissions.set(Permission.objects.filter(
            codename__in=["view_quotation", "add_quotation", "submit_quotation", "approve_quotation", "approve_own_quotation", "send_quotation"]
        ))
        sm_mgr = User.objects.create_user(username="sm_mgr", email="smmgr@example.com", password="Password123!", phone_number="5558880005", role=sm_mgr_role)
        client.force_authenticate(user=sm_mgr)

        pipeline_sc1 = CRMService.create_pipeline(user=sm_mgr, name="Pipeline SC1")
        stage_app_sc = CRMService.create_pipeline_stage(
            user=sm_mgr, pipeline=pipeline_sc1, name="Stage App SC", display_order=1, quotation_approval_required=True
        )

        lead_sc1 = CRMService.create_lead(
            user=sm_mgr, name="Sc1 Lead", email="sc1@example.com", phone="5556667777",
            source=self.source, assigned_to=sm_mgr, pipeline=pipeline_sc1, current_stage=stage_app_sc,
        )
        q1 = QuotationService.create_quotation(user=sm_mgr, lead=lead_sc1, line_items=[{"description": "Widget", "quantity": 2, "unit_price": 250}])
        client.post(f"/api/crm/quotations/{q1.id}/submit/")

        # Self-approval succeeds
        resp_sc1_app = client.post(f"/api/crm/quotations/{q1.id}/approve/")
        self.assertEqual(resp_sc1_app.status_code, status.HTTP_200_OK)

        # Send succeeds
        resp_sc1_send = client.post(f"/api/crm/quotations/{q1.id}/send/")
        self.assertEqual(resp_sc1_send.status_code, status.HTTP_200_OK)
        q1.refresh_from_db()
        self.assertEqual(q1.status, "SENT")

        # SCENARIO 2: Admin revokes approve_own_quotation from sm_mgr_role
        sm_mgr_role.permissions.remove(Permission.objects.get(codename="approve_own_quotation"))
        q2 = QuotationService.create_quotation(user=sm_mgr, lead=lead_sc1, line_items=[{"description": "Gadget", "quantity": 1, "unit_price": 500}])
        client.post(f"/api/crm/quotations/{q2.id}/submit/")

        # Self-approval fails (403)
        resp_sc2_app = client.post(f"/api/crm/quotations/{q2.id}/approve/")
        self.assertEqual(resp_sc2_app.status_code, status.HTTP_403_FORBIDDEN)

        # SCENARIO 3: Employee creates -> Manager approves -> Employee sends
        emp_role = Role.objects.create(rolename="SalesEmp")
        emp_role.permissions.set(Permission.objects.filter(
            codename__in=["view_quotation", "add_quotation", "submit_quotation", "send_quotation", "request_quotation_revision", "generate_quotation_pdf"]
        ))
        sales_emp = User.objects.create_user(username="sales_emp", email="salesemp@example.com", password="Password123!", phone_number="5558880006", role=emp_role)

        client_emp = APIClient()
        client_emp.force_authenticate(user=sales_emp)

        q3 = QuotationService.create_quotation(user=sales_emp, lead=lead_sc1, line_items=[{"description": "Tool", "quantity": 1, "unit_price": 800}])
        client_emp.post(f"/api/crm/quotations/{q3.id}/submit/")

        # Manager approves Employee quotation
        client_admin = APIClient()
        client_admin.force_authenticate(user=self.user)
        client_admin.post(f"/api/crm/quotations/{q3.id}/approve/")

        # Employee sends approved quotation
        resp_sc3_send = client_emp.post(f"/api/crm/quotations/{q3.id}/send/")
        self.assertEqual(resp_sc3_send.status_code, status.HTTP_200_OK)
        q3.refresh_from_db()
        self.assertEqual(q3.status, "SENT")
