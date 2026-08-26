# API_CONTRACT

> Source of truth: actual `urls.py` files in `backend/crm/*/urls.py`, mounted via
> `backend/crm/crm/urls.py`. Every path below was read from code, not guessed.
>
> **Base URL:** frontend `.env` sets `VITE_API_BASE_URL=http://127.0.0.1:8000/api`.
> The base already includes `/api`, therefore every endpoint in this file is a
> **suffix** (e.g. `/login/`), never re-prefixed with `/api` (see G14).
>
> Re-verify against live `/schema/` (drf-spectacular) whenever this file changes.

## Conventions

- **Pagination** (where used): `{ count, next, previous, results }`,
  page_size default 10, max 100 — params `?page=` and `?page_size=`
  (`CRMPageNumberPagination` in Task/FollowUp apps).
- **Error shapes are NOT standardized (G11).** Known shapes:
  - DRF field errors: `{"field_name": ["message"]}`
  - Detail style: `{"detail": "..."}`
  - Custom business errors: `{"error": "..."}` or `{"detail": "..."}` (varies per app)
  - All are normalized client-side by `src/utils/errors.js` → `normalizeApiError`.
- **Auth header:** `Authorization: Bearer <access_token>` (SimpleJWT only).

---

## Accounts (`backend/crm/accounts/urls.py`)

| Method | Path | View | Auth | Notes |
|---|---|---|---|---|
| POST | `/register/` | RegisterAPIView | AllowAny | `{username,email,phone_number,password}` → 201 |
| POST | `/login/` | LoginAPIView | AllowAny | `{email,password}` → 200 `{message, refresh_token, access_token}` |
| POST | `/logout/` | LogoutAPIView | JWT + `logout` perm | `{refresh_token}` → blacklists token |
| POST | `/refresh/` | RefreshTokenAPIView | AllowAny | `{refresh_token}` → 200 `{access_token}` |
| POST | `/change-password/` | ChangePasswordAPIView | JWT | `{old_password,new_password}` |
| GET | `/profile/<uuid:user_id>/` | ProfileAPIView | JWT (self or Admin/Manager) | ProfileSerializer — role is FK id, NOT expanded codenames |
| GET/POST | `/roles/` | RoleListCreateAPIView | JWT (`view_role` / `add_role`) | Admin/Manager only in practice |
| PUT/PATCH/DELETE | `/roles/<int:role_id>/` | RoleDetailAPIView | JWT (`change_role`/`delete_role`) | Admin role protected from rename/delete |
| GET/POST | `/permissions/` | PermissionListCreateAPIView | JWT (`view_permission`/`add_permission`) | |
| PUT/PATCH/DELETE | `/permissions/<int:permission_id>/` | PermissionDetailAPIView | JWT | |
| PUT | `/assign-role/<uuid:user_id>/` | AssignRoleAPIView | JWT (`assign_role`) | `{role_id}` required |
| POST | `/forgot-password/` | ForgotPasswordAPIView | AllowAny | `{email}` → OTP emailed |
| POST | `/reset-password/` | ResetPasswordAPIView | AllowAny | `{email,otp,new_password}` |

No `GET /users/` list exists (G6). No `/auth/me/` exists (G4) — current-user
resolution is documented in `AUTH_CONTRACT.md`.

## Customer Management (`backend/crm/customer_management/urls.py`) — prefix `/crm/`

| Method | Path | View | Perm codename(s) |
|---|---|---|---|
| GET | `/crm/customers/smart-lookup/?query=` or `?email=&phone=&gst=&company=` | SmartCustomerLookupView | view_customer |
| GET/POST | `/crm/accounts/` | CustomerAccountListCreateView | view_customeraccount / manage_customer_account |
| GET/POST | `/crm/contacts/` | CustomerContactListCreateView | view_customercontact / manage_customer_contact |
| GET/POST | `/crm/lead-sources/` | LeadSourceListCreateView | view_leadsource / manage_lead_source |
| GET/POST | `/crm/pipelines/` | PipelineListCreateView | view_pipeline / manage_pipeline |
| GET/POST | `/crm/pipeline-stages/?pipeline=` | PipelineStageListCreateView | view_pipelinestage / manage_pipeline_stage |
| GET/POST | `/crm/leads/?search=&ordering=&pipeline=&current_stage=&assigned_to=&status=` | LeadListCreateView | view_lead / add_lead |
| GET/PATCH | `/crm/leads/<uuid:pk>/` | LeadDetailView | view_lead / change_lead — direct status edit blocked |
| POST | `/crm/leads/<uuid:pk>/assign/` | LeadAssignView | assign_lead — `{assigned_to}` |
| POST | `/crm/leads/<uuid:pk>/progress/` | LeadProgressView | progress_lead — `{stage_id?}` optional |
| POST | `/crm/leads/<uuid:pk>/lost/` | LeadLostView | mark_lead_lost — `{lost_reason}` required |
| POST | `/crm/leads/<uuid:pk>/reengage/` | LeadReengageView | reengage_lead — LOST only |
| POST | `/crm/leads/<uuid:pk>/convert/` | LeadConvertView | convert_lead — see AUTH/workflow notes below |
| GET/POST | `/crm/activities/?lead=&customer=` | ActivityListCreateView | view_activity / add_activity — lead XOR customer |
| GET | `/crm/audit-logs/` | AuditLogListView | view_auditlog |
| GET/POST | `/crm/customers/?search=` | CustomerListCreateView | view_customer / add_customer |
| GET | `/crm/customers/<uuid:pk>/` | CustomerDetailView | view_customer |
| GET | `/crm/customers/<uuid:pk>/activities/` | CustomerActivityListView | view_activity |
| GET/POST | `/crm/quotations/?lead=` | QuotationListCreateView | view_quotation / add_quotation |
| GET | `/crm/quotations/<uuid:pk>/` | QuotationDetailView | view_quotation |
| GET | `/crm/quotations/<uuid:pk>/pdf/?version=` | QuotationPDFView | view_quotation — blocked for DRAFT/PENDING |
| PATCH | `/crm/quotations/<uuid:pk>/update-draft/` | QuotationUpdateDraftView | change_quotation — DRAFT only |
| POST | `/crm/quotations/<uuid:pk>/submit/` | QuotationSubmitView | submit_quotation — DRAFT/REVISED only |
| POST | `/crm/quotations/<uuid:pk>/approve/` | QuotationApproveView | approve_quotation — self-approval guarded |
| POST | `/crm/quotations/<uuid:pk>/reject-approval/` | QuotationRejectApprovalView | approve_quotation |
| POST | `/crm/quotations/<uuid:pk>/send/` | QuotationSendView | send_quotation — APPROVED only |
| POST | `/crm/quotations/<uuid:pk>/send-email/` | QuotationSendEmailView | send_quotation |
| POST | `/crm/quotations/<uuid:pk>/revision/` | QuotationRevisionView | request_quotation_revision — new DRAFT version |
| POST | `/crm/quotations/<uuid:pk>/accept/` | QuotationAcceptView | accept_quotation — auto-converts lead |
| POST | `/crm/quotations/<uuid:pk>/reject/` | QuotationRejectView | reject_quotation — `{rejection_reason}`, auto-marks lead LOST |
| GET | `/crm/quotation-events/` | QuotationIntegrationEventListView | view_quotation |

## Tasks / Meetings / Reminders (`backend/crm/Task/urls.py`) — prefix `/tasks/`

| Method | Path | View | Perm codename(s) |
|---|---|---|---|
| GET/POST | `/tasks/?status=&priority=&category=&assigned_to=&lead=&customer=&search=&ordering=&page=` | TaskListCreateView | view_task / add_task — Employee sees own only |
| GET/PATCH/DELETE | `/tasks/<int:task_id>/` | TaskDetailView | view/change/delete_task — DELETE is soft delete |
| POST | `/tasks/<int:task_id>/assign/` | TaskAssignView | assign_task — `{assigned_to}` required |
| PATCH | `/tasks/<int:task_id>/status/` | TaskStatusUpdateView | change_taskstatus — `{status_id}` int |
| POST | `/tasks/meetings/` | MeetingCreateView | add_meeting — manager must have Manager role |
| GET | `/tasks/meetings/<int:meeting_id>/` | MeetingDetailView | IsAuthenticated (+CanCommunicate) |
| PATCH | `/tasks/meetings/<int:meeting_id>/approval/` | MeetingApprovalView | change_meeting + owner/Manager/PENDING check |
| PATCH | `/tasks/meetings/<int:meeting_id>/reschedule/` | MeetingRescheduleView | created_by only, REJECTED only |
| PATCH | `/tasks/meetings/<int:meeting_id>/status/` | MeetingStatusUpdateView | change_meeting — `{meeting_status_id}` |
| POST | `/tasks/meetings/<int:meeting_id>/participants/` | MeetingParticipantAddView | add_meetingparticipant |
| DELETE | `/tasks/meetings/<int:meeting_id>/participants/<str:user_id>/` | MeetingParticipantRemoveView | delete_meetingparticipant |
| POST | `/tasks/reminders/` | ReminderCreateView | add_reminder |
| GET/PATCH/DELETE | `/tasks/reminders/<int:reminder_id>/` | ReminderDetailView | view/change/delete_reminder |
| PATCH | `/tasks/reminders/<int:reminder_id>/status/` | ReminderStatusUpdateView | change_reminderstatus |

**Known gaps:** no `GET /tasks/meetings/` list, no `GET /tasks/reminders/` list
(G8). Duplicate URL entries exist in `Task/urls.py` lines 51–60 (G9, cosmetic).

## FollowUps (`backend/crm/FollowUp/urls.py`) — prefix `/followups/`

| Method | Path | View | Perm codename(s) |
|---|---|---|---|
| GET/POST | `/followups/?followup_status=&followup_type=&task_id=&created_by=&search=&ordering=` | FollowUpListCreateView | view_followup / **change_followup for POST (not add_followup — G13)** |
| GET/PATCH/DELETE | `/followups/<int:followup_id>/` | FollowUpDetailView | view/change/delete_followup — DELETE is hard delete |
| PATCH | `/followups/<int:followup_id>/status/` | FollowUpStatusUpdateView | change_followupstatus |

Field gotcha: description field is named `decription` (typo, G12) — send that key.

## Notifications (`backend/crm/Notification/urls.py`) — prefix `/api/` root

| Method | Path | View | Perm |
|---|---|---|---|
| GET/POST | `/notification-templates/?event_type=&is_active=` | NotificationTemplateListView | view/add_notificationtemplate |
| GET/PATCH/DELETE | `/notification-templates/<int:pk>/` | NotificationTemplateDetailView | template perms — soft delete |
| POST | `/notifications/send/` | ManualNotificationSendView | send_notification — recipient_id XOR recipient_ids |
| GET | `/notifications/?is_read=true/false` | UserNotificationListView | IsAuthenticated — own only |
| GET | `/notifications/<int:pk>/` | UserNotificationDetailView | owner only |
| PUT/PATCH | `/notifications/<int:pk>/read/` | NotificationMarkReadView | owner only — idempotent |

## CallForms (`backend/crm/CallForms/urls.py`) — prefix `/callforms/` (DRF DefaultRouter)

Registered viewsets: `templates`, `versions`, `fields`, `stage-activities`,
`attempts`, `submissions`, `trigger-rules`, `adhoc-proposals`, `indexed-values`.

Custom actions beyond standard CRUD:

| Method | Path |
|---|---|
| POST | `/callforms/templates/<uuid:pk>/set-primary/` — `{version_id}` |
| POST | `/callforms/templates/<uuid:pk>/create-version/` — `{from_version_id?, version_label?}` |
| POST | `/callforms/versions/<uuid:pk>/clone/` — `{version_label?, set_primary?}` |
| POST | `/callforms/fields/reorder/` — `{template_version_id, orders:[{field_id, display_order}]}` |
| GET | `/callforms/stage-activities/for-stage/?stage_id=<uuid>` |
| GET | `/callforms/stage-activities/lead-primary-form/?lead_id=<uuid>` |
| GET | `/callforms/attempts/lead-history/?lead_id=<uuid>` |
| GET | `/callforms/submissions/lead-timeline/?lead_id=&account_id=&contact_id=` |
| GET | `/callforms/submissions/analytics/?template_version_id=<uuid>` |
| POST | `/callforms/adhoc-proposals/<uuid:pk>/review/` — `{status, rejection_reason?}` |

Version locking: a `TemplateVersion` with submissions is locked — field/version
mutations return 400.

## Schema / Docs endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `http://127.0.0.1:8000/schema/` | OpenAPI JSON — used to re-verify this file |
| GET | `http://127.0.0.1:8000/docs/` | Swagger UI |
| GET | `http://127.0.0.1:8000/redoc/` | ReDoc |

---

## Verification status

- [x] All paths above read directly from `urls.py` files (2026-08-26)
- [x] Diffed against live `GET /schema/` on the running Docker backend (2026-08-26)
      — all 96 schema routes match this document. Two notes:
      1. The schema document renders paths with a doubled `/api/api/` prefix
         (drf-spectacular path-prefix artifact). Live probe confirmed real
         routes are single-prefixed (`POST /api/login/ → 400` with DRF field
         errors; `POST /api/api/login/ → 404`). Suffix convention in
         `endpoints.js` is correct.
      2. `permissions/{permission_id}/` supports **PUT, DELETE only** (no PATCH).
- [x] Auth payload shapes verified via live schema components (see AUTH_CONTRACT.md):
      login `{message, refresh_token, access_token}`, refresh adds `message`,
      profile response is nested under `profile`, 401s use `{"error": ...}`.
