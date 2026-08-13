from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status
from customer_management.models import (
    LeadSource, Pipeline, PipelineStage, Lead, Customer, Activity, AuditLog
)
from customer_management.services import CRMService
from accounts.models import Role

User = get_user_model()


class CRMBaseTestCase(TestCase):
    def setUp(self):
        # Create permissions and role
        self.role, _ = Role.objects.get_or_create(rolename="Manager")
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
                "view_auditlog"
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

    # ---------------------------------------------------------
    # TEST 1-4: Customer API Security Tests
    # ---------------------------------------------------------

    def test_1_unauthenticated_customer_list_rejected(self):
        unauth_client = APIClient()
        response = unauth_client.get("/api/crm/customers/")
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_2_unauthenticated_customer_creation_rejected(self):
        unauth_client = APIClient()
        response = unauth_client.post("/api/crm/customers/", {
            "lead": str(self.source.id),
            "name": "Unauth Cust",
            "email": "unauth@example.com",
            "phone": "111"
        })
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_3_unauthenticated_customer_detail_rejected(self):
        lead = CRMService.create_lead(
            user=self.user, name="Cust Detail Lead", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        cust = CRMService.convert_lead(
            user=self.user, lead=lead, name="Cust", email="custdetail@example.com", phone="123"
        )
        unauth_client = APIClient()
        response = unauth_client.get(f"/api/crm/customers/{cust.id}/")
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_4_unauthenticated_customer_activity_endpoint_rejected(self):
        lead = CRMService.create_lead(
            user=self.user, name="Cust Act Lead", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        cust = CRMService.convert_lead(
            user=self.user, lead=lead, name="Cust", email="custact@example.com", phone="123"
        )
        unauth_client = APIClient()
        response = unauth_client.get(f"/api/crm/customers/{cust.id}/activities/")
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    # ---------------------------------------------------------
    # TEST 5-8: Lead Conversion Tests
    # ---------------------------------------------------------

    def test_5_duplicate_email_lead_conversion_fails_with_validation_error(self):
        lead1 = CRMService.create_lead(
            user=self.user, name="Lead 1", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        CRMService.convert_lead(
            user=self.user, lead=lead1, name="Cust 1", email="dup@example.com", phone="123"
        )

        lead2 = CRMService.create_lead(
            user=self.user, name="Lead 2", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        with self.assertRaises(ValidationError):
            CRMService.convert_lead(
                user=self.user, lead=lead2, name="Cust 2", email="dup@example.com", phone="123"
            )

    def test_6_duplicate_email_conversion_leaves_lead_not_converted(self):
        lead1 = CRMService.create_lead(
            user=self.user, name="Lead 1", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        CRMService.convert_lead(
            user=self.user, lead=lead1, name="Cust 1", email="dup2@example.com", phone="123"
        )

        lead2 = CRMService.create_lead(
            user=self.user, name="Lead 2", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        try:
            CRMService.convert_lead(
                user=self.user, lead=lead2, name="Cust 2", email="dup2@example.com", phone="123"
            )
        except ValidationError:
            pass

        lead2.refresh_from_db()
        self.assertEqual(lead2.status, Lead.Status.ACTIVE)

    def test_7_duplicate_email_conversion_does_not_create_duplicate_customer(self):
        lead1 = CRMService.create_lead(
            user=self.user, name="Lead 1", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        CRMService.convert_lead(
            user=self.user, lead=lead1, name="Cust 1", email="dup3@example.com", phone="123"
        )

        initial_customer_count = Customer.objects.filter(email="dup3@example.com").count()

        lead2 = CRMService.create_lead(
            user=self.user, name="Lead 2", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        try:
            CRMService.convert_lead(
                user=self.user, lead=lead2, name="Cust 2", email="dup3@example.com", phone="123"
            )
        except ValidationError:
            pass

        final_customer_count = Customer.objects.filter(email="dup3@example.com").count()
        self.assertEqual(initial_customer_count, final_customer_count)

    def test_8_successful_normal_lead_conversion_still_works(self):
        lead = CRMService.create_lead(
            user=self.user, name="Normal Lead", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        cust = CRMService.convert_lead(
            user=self.user, lead=lead, name="Normal Cust", email="normal@example.com", phone="123"
        )
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.Status.CONVERTED)
        self.assertEqual(cust.lead, lead)

    # ---------------------------------------------------------
    # TEST 9-11: Pipeline & Stage Consistency Tests
    # ---------------------------------------------------------

    def test_9_patch_lead_with_stage_from_another_pipeline_fails(self):
        lead = CRMService.create_lead(
            user=self.user, name="Patch Lead", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        response = self.client.patch(f"/api/crm/leads/{lead.id}/", {
            "current_stage": str(self.stage2_p2.id)
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_10_patch_lead_with_stage_from_same_pipeline_succeeds(self):
        lead = CRMService.create_lead(
            user=self.user, name="Patch Same Lead", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        response = self.client.patch(f"/api/crm/leads/{lead.id}/", {
            "current_stage": str(self.stage2.id)
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lead.refresh_from_db()
        self.assertEqual(lead.current_stage, self.stage2)

    def test_11_patch_pipeline_and_mismatched_stage_fails(self):
        lead = CRMService.create_lead(
            user=self.user, name="Patch Both Lead", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        response = self.client.patch(f"/api/crm/leads/{lead.id}/", {
            "pipeline": str(self.pipeline2.id),
            "current_stage": str(self.stage2.id)  # belongs to pipeline 1
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------------------------------------------------------
    # TEST 12-14: Service Activity Tests
    # ---------------------------------------------------------

    def test_12_direct_crm_service_create_activity_against_converted_lead_fails(self):
        lead = CRMService.create_lead(
            user=self.user, name="Conv Activity Lead", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        CRMService.convert_lead(
            user=self.user, lead=lead, name="Cust", email="convact@example.com", phone="123"
        )
        with self.assertRaises(ValidationError):
            CRMService.create_activity(
                user=self.user, activity_type="CALL", outcome="Talked", lead=lead
            )

    def test_13_direct_crm_service_create_activity_against_active_lead_succeeds(self):
        lead = CRMService.create_lead(
            user=self.user, name="Active Activity Lead", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        act = CRMService.create_activity(
            user=self.user, activity_type="CALL", outcome="Talked", lead=lead
        )
        self.assertIsNotNone(act.id)

    def test_14_customer_activity_after_lead_conversion_succeeds(self):
        lead = CRMService.create_lead(
            user=self.user, name="Cust Act Lead 2", source=self.source,
            assigned_to=self.user, pipeline=self.pipeline, current_stage=self.stage1
        )
        cust = CRMService.convert_lead(
            user=self.user, lead=lead, name="Cust", email="custact2@example.com", phone="123"
        )
        act = CRMService.create_activity(
            user=self.user, activity_type="MEETING", outcome="Closed deal", customer=cust
        )
        self.assertIsNotNone(act.id)

    # ---------------------------------------------------------
    # TEST 15-17: Audit Logging Tests
    # ---------------------------------------------------------

    def test_15_lead_update_generates_expected_audit_record(self):
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

    # ---------------------------------------------------------
    # TEST 18-21: Terminal-state & negative PATCH guards
    # ---------------------------------------------------------

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
