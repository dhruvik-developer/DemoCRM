# CRM System — Complete Read-Only Analysis Report

> **Mode:** READ-ONLY — No files modified, no packages installed, no migrations run.
> **Date:** 2026-08-26
> **Workspace:** `C:/Users/developer/Downloads/CRM/DemoCRM`
> **Git:** yes (`CRM/.git`)
> **Backend stack:** Django 5.2.7 + DRF 3.17.2 + SimpleJWT 5.5.1 + drf-spectacular 0.30.0 + PostgreSQL (psycopg2-binary 2.9.12) + Celery 5.6.3 + Redis 8.1 + Google Calendar API + WeasyPrint/xhtml2pdf/reportlab
> **Frontend stack (scaffold only):** React 19.2.8 + Vite 8.2.2 + ESLint 10 + React Compiler (babel-plugin-react-compiler 1.0) + react-router-dom 7.18.2 + axios 1.19 + TanStack Query 5.102.4 + react-hook-form 7.86 + zod 4.4 + recharts 3.10

---

## Table of Contents
1. Executive Summary
2. Backend Architecture
3. Backend Modules
4. Database / Data Model Understanding
5. Authentication
6. Authorization & Permissions
7. Validation Rules
8. Complete API Inventory
9. Important Business Workflows
10. Existing Backend Tests
11. Current Frontend State
12. Backend ↔ Frontend API Mapping
13. Recommended Frontend Architecture
14. Required Frontend Screens
15. Required Reusable Components
16. Frontend State/API Strategy
17. Frontend Validation Strategy
18. Frontend Permission Strategy
19. Important Business Rules for UI
20. Gaps/Risks
21. Recommended Implementation Order
22. Files That Will Need Changes Later
— Ready-for-Frontend Assessment

---

## 1. Executive Summary

The project is a **DemoCRM** monorepo with a **mature, heavily-tested Django backend** (~7 domain apps, ~150+ endpoints counting router-generated ones, ~25+ models, JWT auth, dynamic RBAC, Celery beat, PDF generation, Google Meet integration) and a **bare-bones Vite+React scaffold** (8 source files, all feature folders empty, no router, no auth state, no components).

**Backend maturity:** All 7 apps have models/serializers/views/urls/permissions/admin; `customer_management` alone is ~698-line models + 2017-line services + 1799-line views; `CallForms` is a full dynamic form engine with template versioning, trigger rules, analytics. Test coverage is extensive (accounts ~1400 lines, Task ~1407, FollowUp 491, Notification 1400+, customer_management 2000+, CallForms very large). Docker + postgres:18 + redis:7 + celery + celery-beat are configured.

**Frontend maturity:** `src/main.jsx:1-23` only mounts `QueryClientProvider(retry:1, refetchOnWindowFocus:false)` around a static `App.jsx:1-10` (`<h1>CRM</h1>`). `src/api/axios.js:1-10` creates an axios instance with `VITE_API_BASE_URL` but no interceptors, no auth header injection, no refresh logic. `src/api/endpoints.js:1-31` contains only 6 placeholder list paths (`/auth/*`, `/leads/`, `/customers/` etc.) that **do not match any real backend URL** (see §8). All of `src/components/{common,forms,tables,ui}`, `src/features/*`, `src/hooks`, `src/layouts`, `src/pages`, `src/router`, `src/schemas`, `src/utils` are **empty directories (0 files each)**. No Tailwind, no shadcn/ui, no Vitest, no Testing Library, no Playwright are installed despite §6 recommendation — they are requested but absent (package.json:1-37 has no tailwind/shadcn/vitest).

**Key finding:** The frontend cannot talk to the backend as-is. Auth wiring, route mapping, permission handling, and every feature screen need to be built. The backend is **ready for frontend implementation** subject to a handful of pre-flight fixes listed in §20 (CORS missing, endpoint map wrong, token storage strategy undecided, duplicate URL entries, inconsistent error shapes, OTP config drift, no CORS middleware).

---

## 2. Backend Architecture

### 2.1 Project Layout
```
backend/
  .env / .env.example
  .flake8           # max-line 88, ignores E501 etc.
  pytest.ini        # DJANGO_SETTINGS_MODULE=crm.settings, --reuse-db
  requirements.txt  # 97 pinned deps
  crm/
    manage.py
    crm/
      settings.py:1-321
      urls.py:1-40
      celery.py
      wsgi.py / asgi.py
    accounts/          # Auth + RBAC
    audit_log/         # AuditLog + Activity (managed=False, existing tables)
    Task/              # Tasks, Meetings, Reminders + Celery beat jobs
    FollowUp/          # Followups
    customer_management/ # Leads, Pipelines, Customers, Quotations, Activities
    Notification/      # Templates + In-app/Email notifications
    CallForms/         # Dynamic call-form engine (the largest subsystem)
```

`Dockerfile:1-~30` — `python:3.12-slim-bookworm`, installs cairo/pango/libffi for WeasyPrint, copies `backend/crm` → `/app`, `python manage.py migrate && runserver 0.0.0.0:8000`.
`docker-compose.yml:1-~40` — `db: postgres:18-alpine` port `5433:5432`, `redis:7-alpine`, `web` (migrates + runserver), `celery`, `celery-beat`.

### 2.2 Django Configuration `crm/settings.py:1-321`
- `BASE_DIR = Path(__file__).parent.parent` and `load_dotenv(BASE_DIR.parent / ".env", override=True)` — note `.env` lives at `backend/.env`, not `backend/crm/.env`.
- DB: `postgresql` `NAME/USER/PASS/HOST/PORT` from env defaults `CRM/postgres/12345/db/5432`; in docker `HOST=db`.
- `INSTALLED_APPS:27-72` — 6 contrib + `rest_framework`, `drf_spectacular`, 5 domain apps + `rest_framework_simplejwt.token_blacklist`.
- `MIDDLEWARE:74-82` — **No `corsheaders`**, no `CorsMiddleware` → browser frontend on different origin will be blocked unless added.
- `REST_FRAMEWORK:142-156` — `JWTAuthentication` only, `IsAuthenticated` default, throttles `1000/day` user / `100/day` anon, `AutoSchema`.
- `SPECTACULAR_SETTINGS:162-207` — Title `DemoCRM API v1.0.0`, 15 tags (Accounts, Leads … CallForms Indexed Values).
- `SIMPLE_JWT:210-217` — `ACCESS 15m`, `REFRESH 7d`, `USER_ID_FIELD=user_id` (UUID, not `id`), `BLACKLIST_AFTER_ROTATION True`, `ROTATE False`.
- `AUTH_USER_MODEL = "accounts.CustomUser"`:220
- `CALL_FORMS_MAX_FAILED_ATTEMPTS = 5` (settings):228 fallback `os.getenv`.
- Email: `smtp.EmailBackend` Gmail TLS 587, credentials from env; `.env` currently `console` in example but settings forces `smtp` (hard-coded).
- Logging: verbose to console; loggers for 5 apps at INFO.
- Celery: `redis://redis:6379/0`, timezone `Asia/Kolkata`, beat: `task_due_reminder_job` 09:00 daily, `meeting_reminder_job` every minute.

### 2.3 Root URLConf `crm/urls.py:26-40`
```py
admin/                -> admin.site.urls
api/                  -> accounts.urls
api/tasks/            -> Task.urls
api/followups/        -> FollowUp.urls
api/                  -> Notification.urls      # note: shares /api/ prefix
api/crm/              -> customer_management.urls
api/callforms/        -> CallForms.urls
schema/ /docs/ /redoc/-> spectacular
```
`Notification` mounted at bare `api/` means its paths are `api/notifications/` and `api/notification-templates/` — distinct, no collision.

### 2.4 Cross-cutting concerns
- **Permissions everywhere** via `HasDynamicPermission` (`accounts/permissions.py:1-61`) — checks `role.permissions.filter(codename=...)` or superuser bypass.
- **Auditing** via `audit_log/services.py:1-141` — `log_audit`/`log_activity` never raise, use `uuid5` namespace for integer PKs.
- **Notifications** via `Notification/notification_utils.py:1-213` — `trigger_notification_event` renders `{{var}}` placeholders, respects channel IN_APP/EMAIL/BOTH.
- **No CORS, no pagination default** — each app defines its own `CRMPageNumberPagination` (Task/FollowUp) page_size 10.

---

## 3. Backend Modules

| App | Purpose | Key Files | Models |
|-----|---------|-----------|--------|
| **accounts** | Auth, users, roles, OTP | `models.py:1-62`, `views.py:1-1195`, `serializers.py:1-106`, `permissions.py:1-61`, `signals.py:1-152` | `Role`, `CustomUser`, `PasswordResetOTP` |
| **audit_log** | Audit trail | `models.py:1-180`, `services.py:1-141` | `AuditLog` (UUID PK, managed False), `Activity` (30+ types, lead XOR customer) |
| **customer_management** | CRM core — leads→customers→quotations | `models.py:1-698`, `services.py:1-2017`, `views.py:1-1799`, `pdf_utils.py:1-61` | `LeadSource`, `Pipeline`, `PipelineStage`, `Lead`, `Customer`, `CustomerAccount`, `CustomerContact`, `Quotation`, `QuotationVersion`, `QuotationLineItem`, `QuotationApproval`, `QuotationIntegrationEvent` |
| **Task** | Tasks, meetings, reminders + Celery | `models.py:1-293`, `services.py:1-2053`, `tasks.py:1-561`, `views.py:~3000` | `Task`, `TaskStatus/Priority/Category`, `Meeting`, `MeetingStatus/Type`, `MeetingParticipant`, `Reminder`, `ReminderType/Status` |
| **FollowUp** | Follow-ups linked to tasks | `models.py:1-49`, `views.py:1-659` | `FollowUp`, `FollowUpStatus`, `FollowUpTypes` |
| **Notification** | Templates + inbox | `models.py:1-158`, `notification_utils.py:1-213`, `views.py:1-605` | `NotificationTemplate`, `Notification`, enums `NotificationEventType` (40+), `NotificationChannel` |
| **CallForms** | Dynamic call forms engine | `models.py:1-508`, `services.py:1-1325`, `views.py:1-603` | `CallTemplate`, `TemplateVersion`, `TemplateField`, `PipelineStageActivity`, `CallAttempt`, `FormSubmission`, `TaskTriggerRule`, `AdhocFieldProposal`, `IndexedSubmissionValue` |

---

## 4. Database / Data Model Understanding

### 4.1 Accounts `accounts/models.py:1-62`
- **Role** `role_id AutoField PK`, `rolename CharField(13) unique` — values seeded `Admin/Manager/Employee`, `permissions M2M Permission blank`, `created_at/updated_at`.
- **CustomUser** extends `AbstractUser`:
  - `user_id UUID PK default uuid4 editable False` — **primary key is UUID, not id**; `USER_ID_FIELD=user_id` in JWT.
  - `username CharField(100)` **not unique** (overridden), `email EmailField unique`, `phone_number CharField(10) unique`, `role FK Role SET_NULL blank null`, `is_active/is_staff`, `created_at/updated_at`.
  - `USERNAME_FIELD = "email"` — login by email.
- **PasswordResetOTP** `user FK CASCADE`, `otp_hash CharField(64) sha256`, `expires_at`, `is_used`, `attempts PositiveSmall`, index `[user,is_used,expires_at]`, ordering `-created_at`.

### 4.2 Customer Management `customer_management/models.py:1-698`
- **LeadSource** UUID PK, `name unique`, `is_active`, `created_by PROTECT`.
- **Pipeline** UUID PK, `name unique`, `entity_label default "Deal"`, `is_active`.
- **CustomerAccount** UUID PK, `company_name db_index`, `gst_number unique db_index blank null`, `website`, `primary_phone`, `billing_address`.
- **CustomerContact** UUID PK, `account FK SET_NULL`, `name`, `email db_index`, `phone db_index`, `designation`, `is_primary`.
- **PipelineStage** UUID PK, `pipeline FK PROTECT`, `name`, `display_order`, `requires_quotation`, `quotation_approval_required`, constraints `unique(pipeline,name)` and `unique(pipeline,display_order)`, ordering `[pipeline,display_order]`.
- **Lead** UUID PK, `name`, `email/phone/company_name`, `source FK PROTECT`, `assigned_to FK PROTECT`, `pipeline FK PROTECT`, `current_stage FK PROTECT`, `customer_account/contact FK SET_NULL`, `financial_status Choices NO_DUES/PARTIALLY_PAID/PAYMENT_OVERDUE`, `total_value/paid_amount/due_amount Decimal(12,2)`, `metadata JSON default dict`, `status Choices ACTIVE/LOST/CONVERTED default ACTIVE`, `lost_reason`, `lost_at`, indexes `[assigned_to,status]`, `[pipeline,current_stage]`, `[created_at]`; **clean** validates `stage.pipeline == pipeline`, LOST requires reason+timestamp.
- **Customer** UUID PK, `lead OneToOne SET_NULL`, `name`, `email`, `phone`, `company_name`, constraints `unique email` / `unique phone`.
- **Quotation** UUID PK, `quotation_number unique` (`Q-YYYYMM-hex6`), `lead FK PROTECT`, `customer FK PROTECT nullable`, `current_version/accepted_version FK SET_NULL`, `status Choices DRAFT/PENDING_APPROVAL/APPROVED/SENT/ACCEPTED/REJECTED/REVISION_REQUESTED/REVISED`.
- **QuotationVersion** UUID PK, `quotation FK CASCADE`, `version_number`, `status`, `approval_required bool snapshot`, `total_amount Decimal(18,2)`, `terms/notes`, timestamps `approved_at/sent_at/accepted_at/rejected_at`; **clean** validates `sum(line_items quantity*unit_price) == total_amount`.
- **QuotationLineItem** UUID PK, `version FK CASCADE`, `description`, `quantity`, `unit_price Min 0.01`, `amount property`.
- **QuotationApproval** UUID PK, `version FK CASCADE`, `submitted_by PROTECT`, `reviewed_by PROTECT nullable`, `decision PENDING/APPROVED/REJECTED`.
- **QuotationIntegrationEvent** UUID PK, `event_type`, `lead/customer/quotation SET_NULL`, `payload JSON`, `status PENDING/CONSUMED`.

### 4.3 Task `Task/models.py:1-293`
- **TaskStatus/Priority/Category** each `*_id AutoField PK`, `*_name CharField(100)`, `is_active`.
- **Task** `task_id AutoField PK`, `assigned_to FK PROTECT`, `created_by FK PROTECT`, `lead FK PROTECT`, `customer FK SET_NULL nullable`, `form_submission FK SET_NULL nullable`, `task_title CharField(200)`, `description Text`, `due_date DateTime nullable`, `status/priority/category FK PROTECT`, `is_active`, `created_at/updated_at`; **clean** validates `customer.lead_id == lead_id` if both present.
- **MeetingStatus/Type** AutoField PK, `status_name/type_name`, `is_active`.
- **Meeting** `meeting_id AutoField PK`, `task_id FK CASCADE` (named `task_id` but is FK), `lead FK SET_NULL nullable`, `meeting_status_id FK PROTECT`, `meeting_type_id FK PROTECT`, `meeting_title CharField(100)`, `meeting_date DateField`, `start_time/end_time TimeField`, `location`, `description`, `meeting_link URL blank null`, `created_by PROTECT`, `manager FK PROTECT`, `approval_status Choices PENDING/APPROVED/REJECTED default PENDING db_index`, `approved_by/approved_at/rejection_reason/reminder_sent_at`, `extra_fields JSONField default dict`, `is_active`.
- **MeetingParticipant** `participant_id AutoField PK`, `meeting_id FK CASCADE`, `user_id FK PROTECT`, `participant_role CharField(100)`, `is_required`, constraint `unique(meeting_id,user_id)`.
- **ReminderType/Status** AutoField PK, `type_name/status_name`, `is_active`.
- **Reminder** `reminder_id AutoField PK`, `task_id/meeting_id/reminder_for FK CASCADE nullable`, `reminder_type_id/status_id FK PROTECT`, `reminder_datetime DateTime`, `message Text`, `is_sent`, `is_active`, `created_by PROTECT`.

### 4.4 FollowUp `FollowUp/models.py:1-49`
- **FollowUpStatus/Types** AutoField PK, `status_name/type_name`, `is_active`.
- **Followup** `followup_id AutoField PK`, `task_id FK CASCADE`, `followup_status/type FK PROTECT`, `followup_date DateTime`, `decription Text typo blank null`, `is_active`, `created_by PROTECT`.

### 4.5 Notification `Notification/models.py:1-158`
- `NotificationEventType TextChoices` 40+ (TASK_*, MEETING_*, REMINDER_*, FOLLOWUP_*, QUOTATION_*, LEAD_*, ROLE_CHANGED … MANUAL).
- `NotificationChannel IN_APP/EMAIL/BOTH`.
- **NotificationTemplate** `id AutoField PK`, `name`, `event_type db_index`, `message Text`, `channel default IN_APP`, `is_default`, `is_active`, ordering `[event_type,-is_default,-created_at]`, `save()` ensures only one default per event_type.
- **Notification** `id AutoField PK`, `recipient FK CASCADE`, `template FK SET_NULL nullable`, `event_type db_index`, `message`, `channel`, `is_read`, `read_at`, `created_at`, ordering `-created_at`.

### 4.6 CallForms `CallForms/models.py:1-508`
- **CallTemplate** UUID PK, `name unique`, `is_active`, `created_by PROTECT`.
- **TemplateVersion** UUID PK, `template FK CASCADE`, `version_number`, `version_label default "v{number}.0"`, `is_primary`, `is_active`, constraint `unique(template,version_number)`, `is_locked property = submissions.exists()`, `clean` blocks edits when locked.
- **TemplateField** UUID PK, `template_version FK CASCADE`, `field_key regex ^[a-z0-9_]+$`, `label`, `field_type Choices text/textarea/number/boolean/date/time/select`, `is_required`, `display_order`, `help_text`, `options JSON`, `validation_rules JSON`, constraint `unique(template_version,field_key)`, blocks edits when parent version locked.
- **PipelineStageActivity** UUID PK, `stage FK CASCADE`, `name`, `activity_type Choices CALL/MEETING/EMAIL/FOLLOWUP`, `call_template FK SET_NULL nullable`, `is_primary`, `display_order`, constraint `unique(stage,name)`.
- **CallAttempt** UUID PK, `lead FK PROTECT`, `stage/activity/template_version SET_NULL nullable`, `attempt_number`, `agent FK PROTECT`, `outcome Choices NO_ANSWER/BUSY/CONNECTED/CALLBACK/COMPLETED/LOST_SUGGESTED`, `notes`, `start_time default now`, `end_time nullable`, `is_form_submitted`, `suggest_mark_lost bool`.
- **FormSubmission** UUID PK, `lead FK PROTECT`, `call_attempt FK SET_NULL nullable`, `template_version FK PROTECT`, `quotation FK SET_NULL nullable`, `submitted_by FK PROTECT`, `data JSON`, `notes`.
- **TaskTriggerRule** UUID PK, `template_version FK CASCADE`, `trigger_condition Choices ALWAYS/FOLLOW_UP_REQUIRED/OUTCOME_MATCH/FIELD_VALUE_MATCH`, `task_title_template default "Follow-up with {lead_name}"`, `task_category/priority FK SET_NULL nullable`, `due_days_offset default 1`, `assignee_rule Choices CONDUCTING_AGENT/LEAD_OWNER/SPECIFIC_USER`, `specific_assignee FK SET_NULL nullable`, `create_reminder`, `reminder_minutes_before default 30`.
- **AdhocFieldProposal** UUID PK, `template_version FK CASCADE`, `field_key/label/field_type/help_text/options`, `status PENDING/APPROVED/REJECTED`, `proposed_by PROTECT`, `reviewed_by SET_NULL nullable`.
- **IndexedSubmissionValue** UUID PK, `submission FK CASCADE`, `field_key db_index`, `value_text/number/date/boolean`, constraint `unique(submission,field_key)`.

### 4.7 AuditLog `audit_log/models.py:1-180`
- **AuditLog** `id UUID PK`, `user FK PROTECT`, `entity_type CharField(100)`, `entity_id UUIDField` (note: incompatible with Task integer PK — code uses `uuid5` deterministic conversion, `audit_log/services.py:8-20`), `action`, `old_value/new_value/metadata JSON`, `created_at`, `managed = False` (table must pre-exist).
- **Activity** `id UUID PK`, `lead/customer/quotation FK PROTECT nullable`, `created_by FK PROTECT`, `activity_type Choices` 30+ (CALL, EMAIL, QUOTATION_*, TASK_*, FOLLOWUP_*, REMINDER_*), `outcome CharField(255)`, `notes`, `follow_up_required`, `follow_up_date`, `clean` validates lead XOR customer, rejects CONVERTED leads, cross-validates follow-up fields, `managed = False`.

---

## 5. Authentication

### 5.1 Mechanism — SimpleJWT `crm/settings.py:210-217`
- `JWTAuthentication` is the **only** auth class (`REST_FRAMEWORK:142-145`).
- `ACCESS_TOKEN_LIFETIME = 15 minutes`, `REFRESH = 7 days`, `USER_ID_FIELD = "user_id"` (UUID), claim `user_id`.
- `ROTATE_REFRESH_TOKENS = False`, `BLACKLIST_AFTER_ROTATION = True` — refresh tokens are blacklisted after use if rotation enabled (currently not rotated, but `LogoutAPIView` blacklists explicitly).

### 5.2 Endpoints (all under `api/` via `accounts/urls.py:19-39`)
| Method | URL | View | Auth | Request body | Success | Errors |
|--------|-----|------|------|--------------|---------|--------|
| POST | `api/register/` | `RegisterAPIView` `accounts/views.py: ~70` | `AllowAny` | `{username,email,phone_number,password}` | 201 `{user_id,username,email,message}` | 400 field errors, duplicate email/phone 400 |
| POST | `api/login/` | `LoginAPIView` | `AllowAny` | `{email,password}` | 200 `{message,refresh_token,access_token}` | 401 invalid/inactive, 400 missing, 500 token creation |
| POST | `api/logout/` | `LogoutAPIView` `IsAuthenticated` `permission_name logout` | JWT | `{refresh_token}` | 200 `{message}` / 200 already logged out | 400 invalid/missing TokenError, 401 unauth |
| POST | `api/refresh/` | `RefreshTokenAPIView` | `AllowAny` | `{refresh_token}` | 200 `{access_token}` | 400 invalid/missing |
| POST | `api/change-password/` | `ChangePasswordAPIView` | JWT | `{old_password,new_password}` | 200 | 400 wrong old / weak / missing, 401 |
| GET | `api/profile/<uuid:user_id>/` | `ProfileAPIView` | JWT | — | 200 `ProfileSerializer` | 403 if not self and not Admin/Manager, 404, 401 |
| POST | `api/forgot-password/` | `ForgotPasswordAPIView` | AllowAny | `{email}` | 200 OTP sent (email) | 404 no user/inactive, 400 invalid |
| POST | `api/reset-password/` | `ResetPasswordAPIView` | AllowAny | `{email,otp (6),new_password}` | 200 | 400 invalid/expired/too many attempts (lock), 404 |

See also `accounts/serializers.py:1-106` for field-level validation (email format, password via `validate_password`, OTP length 6).

### 5.3 OTP details `accounts/views.py:1-50` + `.env`
- `OTP_LENGTH=6`, `OTP_EXPIRY_MINUTES` read in views as **5** (hard-coded) vs `.env` 10 vs `settings` none — **drift** (see §20).
- `OTP_MAX_ATTEMPTS=3` in views vs 5 in .env. OTP is `sha256` hashed, single-use, old unused OTPs bulk-invalidated on new request, constant-time compare via `hmac.compare_digest`, lockout after max attempts sets `is_used=True`.

### 5.4 Current-user endpoint
There is **no** `api/auth/me/` despite `frontend/src/api/endpoints.js:4-7` claiming `"/auth/me/"`. The closest is `api/profile/<uuid:user_id>/` which requires knowing the UUID. Frontend will need to decode JWT or store user_id after login.

### 5.5 Unauthenticated behavior
- Default permission `IsAuthenticated` → 401 `{"detail":"Authentication credentials were not provided."}` or expired/invalid token 401.
- Throttling: anon 100/day, user 1000/day.

---

## 6. Authorization & Permissions

### 6.1 Roles `accounts/models.py:13-22` + `accounts/signals.py:1-152`
- Three seeded roles: **Admin**, **Manager**, **Employee**. `Role.rolename max_length 13 unique`.
- Stored as `CustomUser.role FK Role SET_NULL` — user may have **no role** (nullable). `create_superuser` creates `Admin` and grants **all** permissions.
- `Role.permissions M2M Permission` — uses Django's built-in `auth.Permission` (codename per model: `view_task`, `add_task`, etc.).

### 6.2 Dynamic permission system `accounts/permissions.py:1-61`
```py
class HasDynamicPermission(BasePermission):
    def has_permission(self, request, view):
        if not authenticated: return False
        if superuser: return True
        role = request.user.role
        if not role: return False  # no role → deny
        perm = view.permission_names[method] or view.permission_name # dict or string
        return role.permissions.filter(codename=perm).exists()
```
Subclasses: `CRMHasPermission`, `CanCommunicateWithLead`, `NotificationHasPermission` (currently pass-through), `CallFormsHasPermission` — all inherit same logic. Most views declare `permission_names = {"GET":"view_x","POST":"add_x","PUT":"change_x","PATCH":"change_x","DELETE":"delete_x"}` or single `permission_name`.

### 6.3 Default seeded permissions `accounts/signals.py:10-90`
- `MANAGER_MODEL_PREFIXES` 64 entries → `MANAGER_CODENAMES = {view/add/change/delete}_{prefix}` + `{assign_task, send_notification, manage_* , add_adhoc_field}`
- `EMPLOYEE_MODEL_PREFIXES` 31 entries → `EMPLOYEE_CODENAMES = {view}_{prefix} + {change_task, add_meeting, add_meetingparticipant, … add_followup, add_callattempt …}`
- `DEFAULT_ROLE_PERMISSIONS = {Admin: None (=all), Manager: MANAGER_CODENAMES, Employee: EMPLOYEE_CODENAMES}` applied on `post_migrate`.

### 6.4 Endpoint → required codename (examples)
| App | View | GET | POST | PATCH/PUT | DELETE |
|-----|------|-----|------|-----------|--------|
| accounts | Roles | `view_role` | `add_role` | `change_role` | `delete_role` |
| accounts | Permissions | `view_permission` | `add_permission` | `change_permission` | `delete_permission` |
| accounts | AssignRole | — | — | `assign_role` (PUT) | — |
| customer_management | Lead | `view_lead` | `add_lead` | `change_lead` | — + `assign_lead`, `progress_lead`, `mark_lead_lost`, `reengage_lead`, `convert_lead` for custom actions |
| Task | Task | `view_task` | `add_task` | `change_task` | `delete_task` (+ `assign_task`, `change_taskstatus`) |
| Task | Meeting | `view_meeting` | `add_meeting` | `change_meeting` | `delete_meeting` |
| Task | Reminder | `view_reminder` | `add_reminder` | `change_reminder` | `delete_reminder` |
| Notification | Templates | `view_notificationtemplate` | `add_notificationtemplate` | `change_notificationtemplate` | `delete_notificationtemplate` |
| CallForms | Templates | custom `CallFormsHasPermission` per ViewSet — check `accounts/signals.py` for `manage_call_template` etc. |
| FollowUp | FollowUp | `view_followup` | `change_followup` (note POST uses change, not add) | `change_followup` | `delete_followup` + `change_followupstatus` |

### 6.5 Object-level / visibility rules
- **Task list** `Task/views.py: TaskListCreateView` — Admin/Manager see **all** active tasks; Employee sees only `assigned_to=request.user`.
- **Task detail/update/delete** — Employee allowed only if `task.assigned_to == user`; otherwise 403. Admin/Manager always allowed (or superuser).
- **FollowUp list** — Admin/Manager all; Employee only where `task.assigned_to == user`.
- **FollowUp detail** — similar owner check.
- **Meeting creation** `MeetingCreateView` — `manager` must have `Role.rolename == "Manager"` else 400; approval flow enforces `meeting.manager_id == request.user.user_id` for approval.
- **Meeting reschedule** — only `created_by` may reschedule, and only if `REJECTED`.
- **Profile** — self or Admin/Manager; Employee cannot view others (403).
- **Notifications** — user sees only `recipient=request.user`; template management requires `view_notificationtemplate` etc.
- **Quotations** — `approve_quotation` checks self-approval: if `submitted_by/created_by == reviewer` and not superuser, requires `approve_own_quotation` perm else `PermissionDenied` 403.

### 6.6 Admin/superuser
- `is_superuser` bypasses all `HasDynamicPermission` checks (returns True).
- `is_staff` only affects Django admin; not used in API perms.

---

## 7. Validation Rules

### 7.1 Accounts `accounts/serializers.py` + `accounts/views.py`
| Field | Rule | Where | On fail |
|-------|------|-------|---------|
| `email` | EmailField format, unique | `RegisterSerializer`, `LoginSerializer`, `Forgot/Reset`, `CustomUser.email unique` | 400 `{"email":[...]}`, 401 login not found |
| `phone_number` | Char 10, unique | `CustomUser.phone_number unique` | 400 duplicate |
| `username` | Char 100, not unique | model | 400 blank |
| `password` | `validate_password` (8 chars, not common, not numeric etc.) on change/reset; **Register does NOT validate** (`RegisterEdgeCaseTests` shows weak still 201) | `ChangePasswordSerializer`, `ResetPasswordSerializer` | 400 |
| `old_password` | must match `check_password` | `ChangePasswordAPIView` | 400 `incorrect` |
| `otp` | 6 chars exact, exists, `is_used=False`, `expires_at > now`, `attempts < max`, hmac compare | `ResetPasswordAPIView` `accounts/views.py: ~800` | 400 `invalid/expired/too many attempts` with remaining count |
| `rolename` | Char 13 unique, Admin/Manager/Employee protected from delete/rename | `RoleDetailAPIView` | 403 `Admin cannot be renamed/deleted` |
| `permissions` list on PATCH role | must all exist, else `count != len(set(ids))` | `RoleDetailAPIView PATCH` | 400 `invalid permission ids` |
| `assign-role role_id` | required | `AssignRoleAPIView` | 400 missing, 404 role not found, 403 if target Admin |

### 7.2 Customer Management
| Entity | Rule | Where | Fail |
|--------|------|-------|------|
| `LeadSource/Pipeline name` | unique, required | `LeadSourceSerializer`, `PipelineSerializer` | 400 duplicate |
| `PipelineStage display_order` | >=1 | `PipelineStageSerializer.validate_display_order` | 400 |
| `PipelineStage pipeline` | must be active | `PipelineStageSerializer` | 400 |
| `Lead email/phone` | email format if provided, phone regex `^[0-9+\-()\s]{7,20}$` | `LeadSerializer` | 400 |
| `Lead source/pipeline/current_stage` | must be active, stage pipeline must == lead pipeline | `LeadSerializer` + `CRMService.create_lead` `services.py: ~200` | 400 |
| `Lead assigned_to` | must be active user | `LeadSerializer` | 400 inactive |
| `Lead current_stage` | must equal first stage (lowest display_order) on create | `CRMService.create_lead` | 400 |
| `Lead duplicate` | active lead with same email+phone exists → error | `CRMService.create_lead / assign_lead` | 400 `duplicate` |
| `Lead status` | direct PATCH of `status` when not ACTIVE rejected; `LOST` requires `lost_reason+lost_at`; non-LOST must not have those | `Lead.clean` + `LeadSerializer` | 400 |
| `Customer lead` | lead must be CONVERTED? Actually `CustomerListCreateView` validates lead CONVERTED | `views.py` | 400 |
| `Customer email/phone` | unique | `Customer` model constraints | 400 |
| `Quotation create` | lead must be ACTIVE | `QuotationService.create_quotation` | 400 |
| `Quotation line_items` | if provided: must be non-empty list, each `quantity>=1`, `unit_price>=0.01`, total = sum(qty*price) checked in `QuotationVersion.clean` | `services.py` + `models.py` | 400 validation error |
| `Quotation draft update` | only DRAFT version | `update_draft_quotation` | 400 |
| `Quotation submit` | only DRAFT/REVISED | `submit_quotation_for_approval` | 400 |
| `Quotation approve` | only PENDING, self-approval check | `approve_quotation` | 400/403 |
| `Quotation send` | version must be APPROVED, not SENT/ACCEPTED/REJECTED | `send_quotation` | 400 |
| `Quotation accept` | version SENT | `accept_quotation` | 400 |
| `Activity lead XOR customer` | exactly one, CONVERTED lead no new activity, follow_up_required/date cross-check | `Activity.clean` + `ActivitySerializer` | 400 |
| `CustomerAccount/Contact` | company_name required etc. | serializers | 400 |

### 7.3 Task / Meeting / Reminder `Task/serializers.py:1-303`
| Field | Rule | Fail |
|-------|------|------|
| `task_title` | strip required, len 3-200 | 400 |
| `due_date` | if new and < now → past error; same-instance bypass | 400 |
| `lead` | required on Task | 400 `lead required` |
| `customer.lead` | if both present must match leader | ValidationError in `Task.clean` → 400 |
| `meeting_title` | strip required len>=3 | 400 |
| `meeting_date` | < today → error; also if `meeting_date < localdate` and new → error | 400 |
| `end_time <= start_time` | error | 400 |
| `manager` | must exist and have Role Manager | 400 |
| `participant_role` | strip required | 400 |
| `reminder_message` | strip required | 400 |
| `reminder_datetime` | if new and < now → error | 400 |

### 7.4 FollowUp `FollowUp/serializers.py:1-76`
| Rule | Fail |
|------|------|
| `followup_date < now` → error (bypass if same instance) | 400 |
| `task_id` required on create (checked in view) | 400 |
| `status_id` must exist and `is_active` | 400 |

### 7.5 CallForms `CallForms/serializers.py:1-400` + `services.py:1-1325`
| Rule | Fail |
|------|------|
| `template name` iexact duplicate | 400 |
| `field_key` regex `^[a-z0-9_]+$` lower | 400 |
| `field_type SELECT requires non-empty options` | 400 |
| `template_version locked (submissions.exists())` blocks create/update/delete/reorder of fields/versions | 400 `locked` |
| `submission data` required fields and select options checked | 400 dict |
| `adhoc field_key` regex | 400 |

### 7.6 Error structure (general DRF)
```json
// validation 400
{"field_name": ["error message"], "non_field_errors": ["..."] }
// permission 403
{"detail": "You do not have permission ..."} or custom 403 message
// auth 401
{"detail": "Authentication credentials were not provided."}
// not found 404
{"detail": "Not found."}
// custom business 400
{"detail": "Lead already converted"} / {"error": "..."} (varies)
```
Not standardized — some views return `{"detail": "..."}`, others `{"error": "..."}` or `{"message": "..."}` (see §20).

---

## 8. Complete API Inventory

> Base host: `http://127.0.0.1:8000` (or `http://localhost:5433` DB). Prefixes as in `crm/urls.py:26-35`. All responses are JSON unless noted PDF. Pagination shape `{"count":N,"next":url|null,"previous":null,"results":[...]}` via `CRMPageNumberPagination` page_size 10, max 100, `?page=` + `?page_size=`.

### 8.1 Accounts — `api/` (`accounts/urls.py:19-39`)
| # | Method | URL | View | Auth | Permission | Body / Query | Success | Errors |
|---|--------|-----|------|------|------------|--------------|---------|--------|
| 1 | POST | `api/register/` | RegisterAPIView | AllowAny | — | `{username,email,phone_number,password}` | 201 `{user_id,username,email,message}` | 400 |
| 2 | POST | `api/login/` | LoginAPIView | AllowAny | — | `{email,password}` | 200 `{message,refresh_token,access_token}` | 401/400 |
| 3 | POST | `api/logout/` | LogoutAPIView | JWT | `logout` (HasDynamic) | `{refresh_token}` | 200 | 400/401 |
| 4 | POST | `api/refresh/` | RefreshTokenAPIView | AllowAny | — | `{refresh_token}` | 200 `{access}` | 400 |
| 5 | POST | `api/change-password/` | ChangePasswordAPIView | JWT | IsAuthenticated | `{old_password,new_password}` | 200 | 400/401 |
| 6 | GET | `api/profile/<uuid:user_id>/` | ProfileAPIView | JWT | IsAuthenticated + owner or Admin/Manager | — | 200 ProfileSerializer | 403/404/401 |
| 7 | GET | `api/roles/` | RoleListCreateAPIView | JWT | `view_role` + Admin/Manager role check in view | — | 200 `[RoleListSerializer]` | 403/401 |
| 8 | POST | `api/roles/` | RoleListCreateAPIView | JWT | `add_role` | `{rolename,description,permissions:[id]}` | 201 | 400/403 |
| 9 | PUT | `api/roles/<int:role_id>/` | RoleDetailAPIView | JWT | `change_role` | `{rolename?,description?,permissions?}` partial | 200 | 400/403/404 |
| 10 | PATCH | `api/roles/<int:role_id>/` | RoleDetailAPIView (permissions add) | JWT | `change_role` | `{permissions:[id]}` required | 200 | 400 |
| 11 | DELETE | `api/roles/<int:role_id>/` | RoleDetailAPIView | JWT | `delete_role` | — | 200 | 403 protected/404 |
| 12 | PUT | `api/assign-role/<uuid:user_id>/` | AssignRoleAPIView | JWT | `assign_role` | `{role_id}` Required | 200 | 400/403/404 |
| 13 | GET | `api/permissions/` | PermissionListCreateAPIView | JWT | `view_permission` | — | 200 `[PermissionSerializer]` | 403/401 |
| 14 | POST | `api/permissions/` | PermissionListCreateAPIView | JWT | `add_permission` | `{name,codename,content_type}` | 201 | 400 |
| 15 | PUT | `api/permissions/<int:permission_id>/` | PermissionDetailAPIView | JWT | `change_permission` | partial | 200 | 404 |
| 16 | DELETE | `api/permissions/<int:permission_id>/` | PermissionDetailAPIView | JWT | `delete_permission` | — | 200 | 404 |
| 17 | POST | `api/forgot-password/` | ForgotPasswordAPIView | AllowAny | — | `{email}` | 200 OTP sent (email to user + console) | 404/400 |
| 18 | POST | `api/reset-password/` | ResetPasswordAPIView | AllowAny | — | `{email,otp,new_password}` | 200 | 400 |

### 8.2 Customer Management — `api/crm/` (`customer_management/urls.py:37-203`)
| # | Method | URL | View | Perm | Body/Query | Success | Notes |
|---|--------|-----|------|------|------------|---------|-------|
| 19 | GET | `api/crm/lead-sources/` | LeadSourceListCreateView | `view_leadsource` | — | 200 | list all |
| 20 | POST | `api/crm/lead-sources/` | LeadSourceListCreateView | `manage_lead_source` | `{name,description?,is_active?}` | 201 | via CRMService |
| 21 | GET | `api/crm/pipelines/` | PipelineListCreateView | `view_pipeline` | — | 200 | |
| 22 | POST | `api/crm/pipelines/` | PipelineListCreateView | `manage_pipeline` | `{name,description?,entity_label?,is_active?}` | 201 | |
| 23 | GET | `api/crm/pipeline-stages/` | PipelineStageListCreateView | `view_pipelinestage` | `?pipeline=` filter (in view) | 200 | |
| 24 | POST | `api/crm/pipeline-stages/` | PipelineStageListCreateView | `manage_pipeline_stage` | `{pipeline,name,display_order,requires_quotation?,quotation_approval_required?}` | 201 | validates order>=1, pipeline active |
| 25 | GET | `api/crm/leads/` | LeadListCreateView | `view_lead` | `?search=` `?ordering=` `?pipeline=` `?current_stage=` `?assigned_to=` `?status=` (filters in view) + pagination | 200 `LeadSerializer` | select_related pipelines etc. |
| 26 | POST | `api/crm/leads/` | LeadListCreateView | `add_lead` | `{name,email?,phone?,company_name?,source,pipeline,current_stage,assigned_to?,total_value?...}` | 201 | via CRMService.create_lead, first stage check |
| 27 | GET | `api/crm/leads/<uuid:pk>/` | LeadDetailView | `view_lead` | — | 200 | |
| 28 | PUT/PATCH | `api/crm/leads/<uuid:pk>/` | LeadDetailView | `change_lead` | partial LeadSerializer (status direct edit blocked) | 200 | audit LEAD_UPDATED |
| 29 | POST | `api/crm/leads/<uuid:pk>/assign/` | LeadAssignView | `assign_lead` | `{assigned_to: uuid}` | 200 | CRMService.assign_lead |
| 30 | POST | `api/crm/leads/<uuid:pk>/progress/` | LeadProgressView | `progress_lead` | `{stage_id?}` (optional, else auto next) | 200 | CRMService.progress_lead |
| 31 | POST | `api/crm/leads/<uuid:pk>/lost/` | LeadLostView | `mark_lead_lost` | `{lost_reason: str}` required | 200 | → LOST |
| 32 | POST | `api/crm/leads/<uuid:pk>/reengage/` | LeadReengageView | `reengage_lead` | `{}` | 200 | LOST→ACTIVE |
| 33 | POST | `api/crm/leads/<uuid:pk>/convert/` | LeadConvertView | `convert_lead` | `{name?,email?,phone?,company_name?,gst_number?,account?,contact?}` defaults to lead fields | 201 `{customer, lead}` | auto matches/creates account/contact, checks quotation if required |
| 34 | GET | `api/crm/activities/` | ActivityListCreateView | `view_activity` | `?lead=` `?customer=` | 200 | |
| 35 | POST | `api/crm/activities/` | ActivityListCreateView | `add_activity` | `{lead?/customer? exactly one, activity_type, outcome, notes?, follow_up_required?, follow_up_date?}` | 201 | auto-creates Task if follow_up_required |
| 36 | GET | `api/crm/audit-logs/` | AuditLogListView | `view_auditlog` | — | 200 | list all AuditLog |
| 37 | GET | `api/crm/customers/` | CustomerListCreateView | `view_customer` | pagination, `?search=` | 200 | |
| 38 | POST | `api/crm/customers/` | CustomerListCreateView | `add_customer` | `{lead,name,email,phone,...}` validates lead CONVERTED | 201 | rarely used (conversion creates customer) |
| 39 | GET | `api/crm/customers/<uuid:pk>/` | CustomerDetailView | `view_customer` | — | 200 | |
| 40 | GET | `api/crm/customers/<uuid:pk>/activities/` | CustomerActivityListView | `view_activity` | filter customer_id | 200 | |
| 41 | GET | `api/crm/customers/smart-lookup/` | SmartCustomerLookupView | `view_customer` | `?query=` / `?email=&phone=&gst=&company=` | 200 `{match_found,account,contacts,portfolio:{total,active,completed,outstanding dues},recent[10]}` | multi-field matching |
| 42 | GET | `api/crm/accounts/` | CustomerAccountListCreateView | `view_customeraccount` | — | 200 | |
| 43 | POST | `api/crm/accounts/` | CustomerAccountListCreateView | `manage_customer_account` | `{company_name,gst_number?,website?,primary_phone?,billing_address?}` | 201 | created_by = user |
| 44 | GET | `api/crm/contacts/` | CustomerContactListCreateView | `view_customercontact` | — | 200 | |
| 45 | POST | `api/crm/contacts/` | CustomerContactListCreateView | `manage_customer_contact` | `{account?,name,email?,phone?,designation?,is_primary?}` | 201 | |
| 46 | GET | `api/crm/quotations/` | QuotationListCreateView | `view_quotation` | `?lead=` filter | 200 | |
| 47 | POST | `api/crm/quotations/` | QuotationListCreateView | `add_quotation` | `{lead_id,terms?,notes?,line_items:[{description,quantity,unit_price}]?}` | 201 | QuotationService.create_quotation |
| 48 | GET | `api/crm/quotations/<uuid:pk>/` | QuotationDetailView | `view_quotation` | — | 200 | QuotationSerializer with current/accepted/all_versions |
| 49 | GET | `api/crm/quotations/<uuid:pk>/pdf/` | QuotationPDFView | `view_quotation` | `?version=` optional | 200 `application/pdf` attachment `{number}_vN.pdf` | blocks DRAFT/PENDING |
| 50 | PUT/PATCH | `api/crm/quotations/<uuid:pk>/update-draft/` | QuotationUpdateDraftView | `change_quotation` | `{terms?,notes?,line_items?}` (replaces) | 200 | only DRAFT |
| 51 | POST | `api/crm/quotations/<uuid:pk>/submit/` | QuotationSubmitView | `submit_quotation` | `{}` | 200 | → PENDING or auto APPROVED |
| 52 | POST | `api/crm/quotations/<uuid:pk>/approve/` | QuotationApproveView | `approve_quotation` | `{}` | 200 | 403 if self-approve without perm |
| 53 | POST | `api/crm/quotations/<uuid:pk>/reject-approval/` | QuotationRejectApprovalView | `approve_quotation` | `{reason?}` | 200 | → DRAFT |
| 54 | POST | `api/crm/quotations/<uuid:pk>/send/` | QuotationSendView | `send_quotation` | `{}` | 200 | → SENT + integration event |
| 55 | POST | `api/crm/quotations/<uuid:pk>/send-email/` | QuotationSendEmailView | `send_quotation` | `{recipient_email?,subject?,body?,version_number?}` | 200 `{quotation,version}` | generates PDF, sends email |
| 56 | POST | `api/crm/quotations/<uuid:pk>/revision/` | QuotationRevisionView | `request_quotation_revision` | `{terms?,notes?,line_items?}` optional | 201 | → new DRAFT version |
| 57 | POST | `api/crm/quotations/<uuid:pk>/accept/` | QuotationAcceptView | `accept_quotation` | `{}` | 200 `{quotation,customer}` | auto convert_lead |
| 58 | POST | `api/crm/quotations/<uuid:pk>/reject/` | QuotationRejectView | `reject_quotation` | `{rejection_reason}` required | 200 | → REJECTED + mark lead LOST |
| 59 | GET | `api/crm/quotation-events/` | QuotationIntegrationEventListView | `view_quotation` | — | 200 | list all events |

### 8.3 Tasks / Meetings / Reminders — `api/tasks/` (`Task/urls.py:21-95`)
| # | Method | URL | View | Perm | Body | Success |
|---|--------|-----|------|------|------|---------|
| 60 | GET | `api/tasks/` | TaskListCreateView | `view_task` | query `?status=&priority=&category=&assigned_to=&lead=&customer=&search=&ordering=&page=&page_size=` | 200 paginated TaskSerializer |
| 61 | POST | `api/tasks/` | TaskListCreateView | `add_task` | `{assigned_to?,lead (required),customer?,form_submission?,task_title,description?,due_date?,status?,priority?,category?}` | 201 |
| 62 | GET | `api/tasks/<int:task_id>/` | TaskDetailView | `view_task` | — | 200 |
| 63 | PATCH | `api/tasks/<int:task_id>/` | TaskDetailView | `change_task` | partial TaskSerializer | 200 (soft check owner) |
| 64 | DELETE | `api/tasks/<int:task_id>/` | TaskDetailView | `delete_task` | — | 200 soft delete `is_active=False` |
| 65 | POST | `api/tasks/<int:task_id>/assign/` | TaskAssignView | `assign_task` | `{assigned_to: uuid}` required | 200 |
| 66 | PATCH | `api/tasks/<int:task_id>/status/` | TaskStatusUpdateView | `change_taskstatus` | `{status_id: int}` required | 200 |
| 67 | POST | `api/tasks/meetings/` | MeetingCreateView | `add_meeting` | `{task_id,lead?,meeting_status_id,meeting_type_id (1 Online/2 Offline),meeting_title,meeting_date,start_time,end_time,location?,description?,manager (uuid Required),extra_fields?}` | 201 PENDING + async manager notify + audit |
| 68 | GET | `api/tasks/meetings/<int:meeting_id>/` | MeetingDetailView | IsAuthenticated+CanCommunicate | — | 200 MeetingSerializer |
| 68b | (duplicate) | `api/tasks/meetings/<int:meeting_id>/` | same duplicate entry | — | — | — |
| 69 | PATCH | `api/tasks/meetings/<int:meeting_id>/approval/` | MeetingApprovalView | `change_meeting` + manager owner check | `{approval_status:"APPROVED"/"REJECTED",meeting_link?,location?,extra_fields?,rejection_reason? (if REJECTED)}` | 200 |
| 69b | duplicate | same | — | — | — | — |
| 70 | PATCH | `api/tasks/meetings/<int:meeting_id>/reschedule/` | MeetingRescheduleView | IsAuthenticated+CanCommunicate + created_by owner | `{meeting_date?,start_time?,end_time?,location?,meeting_link?}` at least one | 200 → PENDING re-notify manager |
| 71 | PATCH | `api/tasks/meetings/<int:meeting_id>/status/` | MeetingStatusUpdateView | change_meeting | `{meeting_status_id:int}` | 200 |
| 72 | POST | `api/tasks/meetings/<int:meeting_id>/participants/` | MeetingParticipantAddView | `add_meetingparticipant` | `{user_id: uuid,participant_role:str}` | 201 |
| 73 | DELETE | `api/tasks/meetings/<int:meeting_id>/participants/<str:user_id>/` | MeetingParticipantRemoveView | `delete_meetingparticipant` | — | 200 |
| 74 | POST | `api/tasks/reminders/` | ReminderCreateView | `add_reminder` | `{task_id?,meeting_id?,reminder_for?,reminder_type_id,reminder_status_id,reminder_datetime,message}` | 201 |
| 75 | GET | `api/tasks/reminders/<int:reminder_id>/` | ReminderDetailView | `view_reminder` | — | 200 |
| 76 | PATCH | `api/tasks/reminders/<int:reminder_id>/` | ReminderDetailView | `change_reminder` | partial ReminderSerializer | 200 |
| 77 | DELETE | `api/tasks/reminders/<int:reminder_id>/` | ReminderDetailView | `delete_reminder` | — | 200 |
| 78 | PATCH | `api/tasks/reminders/<int:reminder_id>/status/` | ReminderStatusUpdateView | `change_reminderstatus`? (perm `change_reminderstatus`) | `{reminder_status_id}` | 200 |

Note: Task master-data endpoints (TaskStatus/Priority/Category, MeetingStatus/Type etc.) exist as models/admin but **no REST endpoints** (only via admin/Django). Frontend will need to hard-code or fetch via other means unless backend adds endpoints.

### 8.4 FollowUps — `api/followups/` (`FollowUp/urls.py:5-17`)
| # | Method | URL | Perm | Body/Query | Success |
|---|--------|-----|------|------------|---------|
| 79 | GET | `api/followups/` | `view_followup` | `?followup_status=&followup_type=&task_id=&created_by=&search=&ordering=&page=` | 200 paginated FollowupSerializer |
| 80 | POST | `api/followups/` | `change_followup` (not add) | `{task_id (Required),followup_status,followup_type,followup_date,decription?}` | 201 |
| 81 | GET | `api/followups/<int:followup_id>/` | `view_followup` | — | 200 |
| 82 | PATCH | `api/followups/<int:followup_id>/` | `change_followup` | partial | 200 |
| 83 | DELETE | `api/followups/<int:followup_id>/` | `delete_followup` | — | 200 **hard delete** |
| 84 | PATCH | `api/followups/<int:followup_id>/status/` | `change_followupstatus` | `{status_id:int}` | 200 |

### 8.5 Notifications — `api/` (`Notification/urls.py:13-47`)
| # | Method | URL | Perm | Body/Query | Success |
|---|--------|-----|------|------------|---------|
| 85 | GET | `api/notification-templates/` | `view_notificationtemplate` | `?event_type=&is_active=` | 200 |
| 86 | POST | `api/notification-templates/` | `add_notificationtemplate` | `{name,event_type,message,channel?,is_default?,is_active?}` | 201 |
| 87 | GET | `api/notification-templates/<int:pk>/` | `view_notificationtemplate` | — | 200 |
| 88 | PUT/PATCH | `api/notification-templates/<int:pk>/` | `change_notificationtemplate` | partial | 200 |
| 89 | DELETE | `api/notification-templates/<int:pk>/` | `delete_notificationtemplate` | — | 200 soft `is_active=False` |
| 90 | POST | `api/notifications/send/` | `send_notification` (manual) | `{recipient_id?/recipient_ids? (exactly one),template_id?,event_type? default MANUAL,custom_message?,channel?}` | 201 `{triggered}` |
| 91 | GET | `api/notifications/` | IsAuthenticated | `?is_read=true/false` filter own | 200 `[NotificationSerializer]` ordered -created_at |
| 92 | GET | `api/notifications/<int:pk>/` | IsAuthenticated + owner | — | 200 |
| 93 | PUT/PATCH | `api/notifications/<int:pk>/read/` | IsAuthenticated + owner | `{}` | 200 `is_read=True, read_at=now` idempotent |

### 8.6 CallForms — `api/callforms/` (`CallForms/urls.py:1-34` + DefaultRouter)
Router generates standard ViewSet routes plus `@action` extras. `basename` → URL names `calltemplate-`, `templateversion-` etc.

| # | Method | URL | ViewSet Action | Perm | Body |
|---|--------|-----|----------------|------|------|
| 94 | GET | `api/callforms/templates/` | CallTemplateViewSet.list | CallFormsHasPermission | — |
| 95 | POST | `api/callforms/templates/` | .create | `manage_call_template` | `{name,description?,is_active?,initial_fields?:[{field_key,label,field_type,is_required,options...}]}` |
| 96 | GET | `api/callforms/templates/<uuid:pk>/` | .retrieve | — | — |
| 97 | PUT/PATCH | `api/callforms/templates/<uuid:pk>/` | .update/partial | — | — |
| 98 | DELETE | `api/callforms/templates/<uuid:pk>/` | .destroy | — | — |
| 99 | POST | `api/callforms/templates/<uuid:pk>/set-primary/` | .set_primary | — | `{version_id: uuid}` |
| 100 | POST | `api/callforms/templates/<uuid:pk>/create-version/` | .create_version | — | `{from_version_id?,version_label?}` |
| 101 | GET | `api/callforms/versions/` | TemplateVersionViewSet.list | `manage_template_version` | — |
| 102 | POST | `api/callforms/versions/` | .create | — | `{template,version_number,...}` |
| 103 | GET | `api/callforms/versions/<uuid:pk>/` | .retrieve | — | — |
| 104 | PUT/PATCH | `api/callforms/versions/<uuid:pk>/` | .update (blocked if locked) | — | — |
| 105 | DELETE | `api/callforms/versions/<uuid:pk>/` | .destroy (blocked if locked) | — | — |
| 106 | POST | `api/callforms/versions/<uuid:pk>/clone/` | .clone | — | `{version_label?,set_primary?}` |
| 107 | GET | `api/callforms/fields/` | TemplateFieldViewSet.list | `manage_template_field` | — |
| 108 | POST | `api/callforms/fields/` | .create (blocked if locked) | — | `{template_version,field_key,label,field_type,options?}` |
| 109 | PUT/PATCH | `api/callforms/fields/<uuid:pk>/` | .update (blocked if locked) | — | — |
| 110 | DELETE | `api/callforms/fields/<uuid:pk>/` | .destroy (blocked if locked) | — | — |
| 111 | POST | `api/callforms/fields/reorder/` | .reorder | — | `{template_version_id,orders:[{field_id,display_order}]}` |
| 112 | GET | `api/callforms/stage-activities/` | PipelineStageActivityViewSet.list | `manage_stage_activity` | `?stage_id=` via for-stage action |
| 113 | POST | `api/callforms/stage-activities/` | .create | — | `{stage,name,activity_type,call_template?,is_primary?,display_order?}` handles primary uniqueness |
| 114 | GET | `api/callforms/stage-activities/<uuid:pk>/` | .retrieve | — | — |
| 115 | PUT/PATCH | `api/callforms/stage-activities/<uuid:pk>/` | .update | — | — |
| 116 | DELETE | `api/callforms/stage-activities/<uuid:pk>/` | .destroy | — | — |
| 117 | POST | `api/callforms/stage-activities/<uuid:pk>/set-primary/` | .set_primary | — | `{}` |
| 118 | GET | `api/callforms/stage-activities/for-stage/` | .for_stage | — | `?stage_id=uuid` |
| 119 | GET | `api/callforms/stage-activities/lead-primary-form/` | .lead_primary_form | — | `?lead_id=uuid` → `{lead,stage,activity,call_template,template_version,fields[]}` |
| 120 | GET | `api/callforms/attempts/` | CallAttemptViewSet.list | — | `?lead_id=&agent_id=&outcome=` |
| 121 | POST | `api/callforms/attempts/` | .create | — | `{lead_id,stage_id?,activity_id?,template_version_id?,outcome?,notes?,start_time?,end_time?}` → returns with `suggest_mark_lost` |
| 122 | GET | `api/callforms/attempts/<uuid:pk>/` | .retrieve | — | — |
| 123 | GET | `api/callforms/attempts/lead-history/` | .lead_history | — | `?lead_id=uuid` |
| 124 | GET | `api/callforms/submissions/` | FormSubmissionViewSet.list | — | `?lead_id=&version_id=&field_key=&value=` |
| 125 | POST | `api/callforms/submissions/` | .create | — | `{lead_id,template_version_id,call_attempt_id?,quotation_id?,data:{field_key:value},notes?}` |
| 126 | GET | `api/callforms/submissions/<uuid:pk>/` | .retrieve | — | — |
| 127 | GET | `api/callforms/submissions/lead-timeline/` | .lead_timeline | — | `?lead_id=&account_id=&contact_id=` → timeline feed |
| 128 | GET | `api/callforms/submissions/analytics/` | .analytics | — | `?template_version_id=uuid` → per-field analytics |
| 129 | GET | `api/callforms/trigger-rules/` | TaskTriggerRuleViewSet.list | — | `?version_id=` |
| 130 | POST | `api/callforms/trigger-rules/` | .create | — | `{template_version,trigger_condition,condition_field_key?,condition_value?,task_title_template?,task_category?,task_priority?,due_days_offset?,assignee_rule?,specific_assignee?,create_reminder?}` |
| 131 | GET | `api/callforms/trigger-rules/<uuid:pk>/` | .retrieve | — | — |
| 132 | PUT/PATCH | `api/callforms/trigger-rules/<uuid:pk>/` | .update | — | — |
| 133 | DELETE | `api/callforms/trigger-rules/<uuid:pk>/` | .destroy | — | — |
| 134 | GET | `api/callforms/adhoc-proposals/` | AdhocFieldProposalViewSet.list | `view_adhocfieldproposal` | — |
| 135 | POST | `api/callforms/adhoc-proposals/` | .create | `add_adhoc_field` | `{template_version,field_key,label,field_type?,help_text?,options?}` → PENDING |
| 136 | GET | `api/callforms/adhoc-proposals/<uuid:pk>/` | .retrieve | — | — |
| 137 | POST | `api/callforms/adhoc-proposals/<uuid:pk>/review/` | .review | `manage_adhoc_field` | `{status:"APPROVED"/"REJECTED",rejection_reason?}` |
| 138 | GET | `api/callforms/indexed-values/` | IndexedSubmissionValueViewSet.list | IsAuthenticated | `?submission_id=&field_key=` |

### 8.7 Docs
| GET | `schema/` | SpectacularAPIView | — | OpenAPI JSON |
| GET | `docs/` | SpectacularSwaggerView | — | Swagger UI |
| GET | `redoc/` | SpectacularRedocView | — | ReDoc |

---

## 9. Important Business Workflows

### 9.1 Lead Creation `customer_management/services.py: CRMService.create_lead`
```
Frontend POST api/crm/leads/
→ LeadSerializer validation (source/pipeline active, stage belongs to pipeline, phone regex, assigned_to active)
→ CRMService.create_lead:
   1. Validate stage.pipeline == pipeline else 400
   2. Duplicate check: Lead.objects.filter(status=ACTIVE, email=..., phone=...) → 400 if exists
   3. Enforce first stage: current_stage must equal pipeline.stages.order_by(display_order).first() else 400
   4. Create Lead ACTIVE, audit LEAD_CREATED, trigger LEAD_CREATED notification to assigned_to
→ Response 201 LeadSerializer
```
Interesting: initial stage must be the first in display_order; frontend cannot create a lead directly at stage 2.

### 9.2 Lead Assignment / Progression / Lost / Reengage
- **Assign** `POST api/crm/leads/<uuid>/assign/` `{assigned_to}` → validates ACTIVE, inactive assignee 400, duplicate check, audit + trigger `LEAD_ASSIGNED`.
- **Progress** `POST .../progress/` `{stage_id?}` → if `stage_id` provided must be active pipeline stage; else auto next `display_order > current`. Saves, audit `STAGE_CHANGED`, trigger `LEAD_STAGE_CHANGED` if assigned != actor.
- **Lost** `POST .../lost/` `{lost_reason}` required → ACTIVE only, sets `LOST`, `lost_reason`, `lost_at=now`, audit + trigger `LEAD_MARKED_LOST`.
- **Reengage** `POST .../reengage/` → only LOST, resets to ACTIVE nulls lost fields, audit `LEAD_REENGAGED`.

### 9.3 Lead Conversion `customer_management/services.py: convert_lead` `customer_management/views.py: LeadConvertView`
```
POST api/crm/leads/<uuid>/convert/ {name?,email?,phone?,company_name?,gst_number?,account?,contact?}
→ select_for_update lead
→ If CONVERTED → 400 "Already converted"
→ If not ACTIVE → 400
→ If current_stage.requires_quotation and no ACCEPTED quotation → 400 "Quotation required"
→ Duplicate protection:
   - Exact email+phone → return existing Customer 201 (idempotent)
   - Email match OR phone match alone → 400 duplicate
→ Multi-project identity:
   - Account via gst_number iexact → lead.customer_account → company_name iexact → create if none → save lead.customer_account
   - Contact via (email+phone) → email → phone → create if none with is_primary logic
→ Create Customer {lead,name,email,phone,company_name} unique constraints email/phone
→ Lead.status=CONVERTED save, audit LEAD_CONVERTED (+ LEAD_CONVERTED_AFTER_QUOTATION_ACCEPTANCE if quotation present), trigger LEAD_CONVERTED
→ 201 {customer, lead}
```
Frontend must supply email+phone either from lead or override; gst_number optional triggers account lookup. If stage requires quotation, UI must block convert until accepted.

### 9.4 Quotation Flow `customer_management/services.py: QuotationService.*`
```
1. Create: POST api/crm/quotations/ {lead_id, terms?, notes?, line_items?}
   → Validates lead ACTIVE, assigned_user = lead.assigned_to or request.user
   → approval_required = stage.quotation_approval_required
   → Creates Quotation DRAFT + QuotationVersion v1 DRAFT (approval_required snapshot) + line items → total recomputed
   → audit QUOTATION_CREATED, activity QUOTATION_CREATED, trigger QUOTATION_CREATED

2. Update draft: PATCH api/crm/quotations/<uuid>/update-draft/ → only DRAFT else 400
   → terms/notes/line_items replace, total recomputed, audit+activity+trigger

3. Submit: POST .../submit/ → DRAFT/REVISED only
   → If approval_required: → PENDING_APPROVAL + QuotationApproval PENDING, trigger SUBMITTED
   → Else auto-approve: APPROVED + approved_at, trigger APPROVED

4. Approve/Reject (manager): POST .../approve/ or .../reject-approval/
   → PENDING only, self-approval check (requires approve_own_quotation), decision APPROVED → quotation APPROVED or DRAFT + activity

5. Send: POST .../send/ → APPROVED only (not SENT/ACCEPTED/REJECTED)
   → sets SENT + sent_at, creates QuotationIntegrationEvent (pending follow-up task), trigger QUOTATION_SENT
   → Follow-up task auto-created via activity? Actually send creates integration event consumed by follow-up via async? Not auto task here.

6. Revision: POST .../revision/ → SENT/REVISED/DRAFT/APPROVED
   → If SENT/APPROVED sets REVISED, creates new version_number+1 DRAFT copy of line items or new list, sets as current_version

7. Accept: POST .../accept/ → SENT only → ACCEPTED + accepted_at → quotation.accepted_version = version
   → Trigger ACCEPTED
   → Auto convert_lead (if ACTIVE) with lead email fallback → creates Customer

8. Reject: POST .../reject/ {rejection_reason} required → SENT only → REJECTED + rejected_at
   → Trigger CLIENT_REJECTED
   → If lead ACTIVE → mark_lead_lost with reason

9. PDF: GET .../pdf/?version= → blocks DRAFT/PENDING, renders customer_management/quotation_pdf.html via weasyprint/xhtml2pdf fallback, returns attachment

10. Email: POST .../send-email/ {recipient_email?, subject?, body?, version_number?}
    → If version APPROVED auto-send, generates PDF, EmailMessage attach, send; on failure audit QUOTATION_EMAIL_FAILED + 400
```

### 9.5 Task Flow `Task/views.py:1-~500` + `Task/services.py`
```
Create: POST api/tasks/ {assigned_to?, lead required, ...}
 → serializer save created_by=user, audit TASK_CREATED, activity TASK_CREATED, trigger TASK_ASSIGNED if assigned_to != user
List: GET api/tasks/?status=&... → visibility: Admin/Manager all, Employee own assigned only
Detail: GET/PATCH/DELETE api/tasks/<id>/ → Employee 403 unless assigned_to
Assign: POST .../<id>/assign/ {assigned_to} → audit ASSIGNED/REASSIGNED, trigger accordingly
Status: PATCH .../<id>/status/ {status_id} → Admin/Manager or assigned Employee
```
Task model has no state machine — any status transition allowed. `followUp` creation via activity auto-creates Task (see §9.8).

### 9.6 Meeting Flow `Task/views.py: MeetingCreateView` + `Task/services.py` + `Task/tasks.py`
```
1. Request: POST api/tasks/meetings/ {task_id, meeting_status/type, title, date, start/end, manager uuid Required, location?, extra_fields?}
   → manager must have Manager role else 400
   → save created_by, approval_status=PENDING, reminder_sent_at=None, location/meet_link auto per type
   → on_commit notify_manager_about_meeting.delay(meeting_id) (Celery)
     → if online and no link → generate_google_meet_link (real API if GOOGLE_SERVICE_ACCOUNT_FILE else fake https://meet.google.com/xxx-xxxx-xxx)
     → if offline and no location → OFFICE_LOCATION "123, Business Park, Ahmedabad…"
     → trigger ONLINE/OFFLINE/MEETING_CREATED notification to manager + send email "Meeting Approval Required"
   → audit MEETING_CREATED, activity MEETING

2. Manager approval: PATCH .../meetings/<id>/approval/ {approval_status:"APPROVED"/"REJECTED", ...}
   → checks meeting.manager_id == request.user.user_id and role Manager else 403, must be PENDING
   → APPROVED: sets link/location if online/offline, APPROVED + approved_by/at, on_commit send_approved_meeting.delay
        → send_meeting_scheduled_emails to employee+manager+customer, generate link if missing, notifications to both
   → REJECTED: requires rejection_reason, sets REJECTED, on_commit notify_employee_meeting_rejected.delay → email + notification

3. Reschedule: PATCH .../meetings/<id>/reschedule/ {date/time/link/location at least one}
   → only created_by and only if REJECTED, resets to PENDING nulls approval fields, on_commit notify_manager_about_reschedule

4. 5-minute reminder: Celery beat every minute Task/tasks.py: meeting_reminder_job
   → finds APPROVED today, reminder_sent_at ISNULL, start_time in [now, now+5m59s]
   → sends 5-min emails to employee/manager/customer + in-app notifications, sets reminder_sent_at
```

### 9.7 Activity + Auto-Task `customer_management/services.py: create_activity`
```
POST api/crm/activities/ {lead XOR customer exactly one, activity_type, outcome, notes?, follow_up_required?, follow_up_date?}
→ Validates CONVERTED lead cannot have new activity
→ Creates Activity
→ If follow_up_required and follow_up_date future:
   → get_or_create TaskStatus Pending, Priority High if MEETING/DEMO else Medium, Category Follow-Up
   → assigned_user = lead.assigned_to or request.user
   → Creates Task + Activity autocreation audit
   → Notifications to lead assigned_to and customer assigned (if diff)
```
Frontend should offer "Create follow-up task" checkbox that sets these fields.

### 9.8 Quotation → FollowUp → Task via CallForms `CallForms/services.py: process_submission_task_triggers`
```
POST api/callforms/submissions/ {lead_id, template_version_id, data:{field_key: value}, call_attempt_id?}
→ validate_submission_data (required + select options)
→ Creates FormSubmission + IndexedSubmissionValue rows + sync_submission_to_lead (fill-if-blank keys name/email/phone/company)
→ If call_attempt → marks COMPLETED + is_form_submitted True
→ process_submission_task_triggers:
   → for each active TaskTriggerRule where condition eval (ALWAYS / FOLLOW_UP_REQUIRED / OUTCOME_MATCH / FIELD_VALUE_MATCH)
   → due_date = follow_up_date parsed if future else now + due_days_offset
   → Creates Task (status Pending fallback) + Followup (Pending/Call) + Reminder (if create_reminder and future)
→ Trigger TASK_ASSIGNED etc.
```

### 9.9 Notification Flow `Notification/notification_utils.py:1-213`
```
Event (lead convert, task assign, meeting approval, quotation workflow, role change etc.)
→ trigger_notification_event(event_type, recipient(s), context dict, template_id?, custom_message?, channel?)
  → Resolves template: template_id active else is_default active else first for event_type
  → Renders message: custom_message > template with {{var}} replacement else fallback "Notification ({event}): {title}"
  → Channel: template.channel or IN_APP
  → For each recipient: create Notification row (is_read False) + if EMAIL/BOTH send_mail (fail_silently True)
→ User inbox GET api/notifications/?is_read= ordered -created_at
→ Mark read PUT/PATCH api/notifications/<pk>/read/ (idempotent)
```

---

## 10. Existing Backend Tests

Test counts are approximate (lines include helpers). No external coverage report in repo.

| App | File | Lines | Classes / Count | What is covered |
|-----|------|-------|-----------------|-----------------|
| accounts | `accounts/tests.py` | ~1400 | 15+ classes, ~100 tests | CustomUserManager, Role model, register/login/logout/refresh/changePassword/profile/roles/assignRole/permissions/HasDynamicPermission, edge cases (weak password still 201, duplicate, no role). |
| accounts | `accounts/test_spectacular.py` + `test_accounts_extra.py` | not read | — | Schema/docs extras |
| Task | `Task/tests.py` | 1407 | 3 suites | Task CRUD, auth 401, validation, soft delete, assign, status, pagination 10, filters, search, ordering; Meeting create 201 pending, invalid time 400, approval flows (online/offline/custom extra_fields), rejection→reschedule, 5-min celery job 4m45s, participant add/remove; Reminder CRUD, status, process_due_* |
| FollowUp | `FollowUp/tests.py` | 491 | FollowUpAPITestCase | Auth, create 201, validation, list/detail/update/hard delete, pagination, filters, search, ordering, owner/forbidden 403, notification skip. Note `decription` typo field. |
| Notification | `Notification/tests.py` | ~1400+ | 10+ suites | Template CRUD, default unset logic, render placeholders, user inbox own-only, filter is_read, mark read idempotent, channel EMAIL/BOTH vs IN_APP, persistent storage, manual send single/multi, business integration (task/quotation triggers), trigger fallbacks, email sending. |
| customer_management | `customer_management/tests.py` | ~2000+ | CRMBaseTestCase + 5 suites ~80 tests | LeadSource/Pipeline/Stage (duplicate, inactive, display_order, quotation flags), Lead CRUD, validation (inactive, wrong pipeline, converted patch blocked, lost_reason), assign/progress/lost/reengage/convert (duplicate, quotation required, perms 403, unauth), Customer list/detail/create duplicate via convert, Activity (XOR, follow_up, converted block, auto-task), Quotation workflows (not fully read but CRUD included). |
| CallForms | `CallForms/tests.py` | very large | Phase1-6 + ScenarioWorkflow 10 scenarios | Task master seeded, template/version/field stage activity, attempt/submission, version locked mutation blocked, reorder, stage primary, lead primary form, sequential attempts, validation missing/invalid, submission marks attempt COMPLETED locks version, threshold 5 suggests lost, trigger rule → Task+Reminder, adhoc filtering/analytics/timeline, 10 end-to-end scenarios (no_answer, connected interested, not interested lost, threshold, demo quotation accepted, reassign etc.). |
| audit_log | — | 0 | — | No tests file listed. |
| Overall | `pytest.ini:3` | — | `python_files=tests.py test_*.py *_test.py`, `addopts=--reuse-db` | Run via `pytest` (no `python manage.py test` needed). Coverage via `pytest-cov` available but no report committed. |

**Missing / weak areas:**
- No audit_log tests at all.
- Register weak-password accepted but not explicitly tested for frontend UX.
- No integration test for PDF generation failure (weasyprint fallback).
- No CORS/refresh-rotation tests beyond basic.
- No test for `Task` integer PK vs `AuditLog` uuid5 conversion (warned in docstring).

---

## 11. Current Frontend State

### 11.1 File inventory `frontend/` `C:/Users/developer/Downloads/CRM/DemoCRM/frontend`
```
frontend/
  .env                  VITE_API_BASE_URL=http://127.0.0.1:8000/api
  .env.example          same (correct)
  .gitignore            24 lines (node_modules/dist/.local etc.)
  eslint.config.js:1-21  defineConfig([ globalIgnores dist, flat recommended + reactHooks + reactRefresh ])
  vite.config.js:1-11    plugins [react(), babel({presets:[reactCompilerPreset()]})]  # React Compiler via Babel
  index.html:1-13        <div id="root"> + /src/main.jsx
  package.json:1-37      scripts dev/build/lint/preview; deps see below; type module
  package-lock.json      lockfile v3
  public/
    favicon.svg          9522 bytes single-line SVG
    icons.svg            24 lines 5 symbol icons
  dist/                  pre-built (index.html 458B, css 152B, js 216kB) — stale, not git-ignored? dist listed in .gitignore
  src/
    main.jsx:1-23        StrictMode + QueryClient(retry:1, refetchOnWindowFocus:false) + App
    App.jsx:1-10         <h1>CRM</h1><p>Frontend is running</p>  # no router
    index.css:1-20       box-sizing + Inter font + #root min-height
    api/
      axios.js:1-10      axios.create({baseURL:import.meta.env.VITE_API_BASE_URL, Content-Type json})
      endpoints.js:1-31  placeholder map (wrong paths, see §12)
    assets/
      hero.png (13kB binary), react.svg (4126), vite.svg (8709)
    components/common|forms|tables|ui  EMPTY (0)
    features/auth|customers|dashboard|leads|meetings|notifications|quotations|tasks EMPTY
    hooks/               EMPTY
    layouts/             EMPTY
    pages/               EMPTY
    router/              EMPTY
    schemas/             EMPTY
    utils/               EMPTY

Total source files: 8 (including 3 binary assets)
```

### 11.2 Dependencies `frontend/package.json:1-37`
- **Installed and used:** `react 19.2.8`, `react-dom 19.2.8`, `react-router-dom 7.18.2` (unused), `axios 1.19`, `@tanstack/react-query 5.102.4` (used in main.jsx), `react-hook-form 7.86` (unused), `zod 4.4` (unused), `@hookform/resolvers 5.9.1` (unused), `recharts 3.10.1` (unused).
- **Dev:** `vite 8.2.2`, `@vitejs/plugin-react 6.1`, `@rolldown/plugin-babel 0.2.3`, `babel-plugin-react-compiler 1.0`, `eslint 10`, `eslint-plugin-react-hooks/refresh`, `globals`, `@types/react*`, `@babel/core`.
- **NOT installed despite requested architecture (§6 prompt):** `tailwindcss`, `shadcn/ui` (requires tailwind + components), `vitest`, `@testing-library/react`, `playwright`, `@tanstack/react-query` is installed, `zod` installed. So 4 of the recommended list are missing and need `npm install` before implementation.

### 11.3 What is **already created** vs **still empty**
| Area | Created | Empty / Not implemented |
|------|---------|-------------------------|
| Build tooling | Vite + ESLint + React Compiler preset working | No Tailwind, no shadcn config, no path aliases (`@/`), no Vitest, no Playwright |
| Entry | `main.jsx` QueryClient, `App.jsx` static, `index.css` global | No `BrowserRouter`, no `RouterProvider`, no `QueryClient` persistence, no error boundaries |
| API layer | `axios.js` instance, `endpoints.js` map | No interceptors (auth header, 401 refresh, error toasts), no query/mutation hooks, wrong endpoint paths |
| State / Auth | — | No AuthContext, no token storage, no refresh, no profile fetch, no role/permission cache |
| Components | Empty scaffold folders | No Button/Input/Card/Table/Form/Error/Loading/Empty/Layout/Header/Sidebar |
| Features | Empty `src/features/*` | No auth pages, no CRUD, no dashboard, no filters |
| Routing | Empty `src/router/` | No protected routes, no role guards, no lazy loading |
| Schemas | Empty `src/schemas/` | No zod schemas mirroring backend validation |
| Hooks/Utils | Empty | No `useAuth`, `usePermissions`, `useDebounce`, `formatDate` etc. |
| Tests | None | No Vitest/RTL/Playwright |

---

## 12. Backend ↔ Frontend API Mapping

### 12.1 API base URL
- Frontend `.env:1` → `VITE_API_BASE_URL=http://127.0.0.1:8000/api` — correct for backend host but **must not have trailing slash issues** (axios `baseURL + endpoints` should avoid double slash; endpoints should start with `/` or not consistently. Backend expects no trailing slash on base; `api/tasks/` etc. — frontend base already includes `/api`, so endpoints should be `/register/` not `/auth/login/`).
- Docker port `8000` matches. Local dev without Docker also `127.0.0.1:8000`. OK.

### 12.2 Real vs placeholder endpoints
`frontend/src/api/endpoints.js:1-31` currently:
```js
auth: { login:"/auth/login/", me:"/auth/me/", logout:"/auth/logout/" }
leads: { list:"/leads/" } customers: { list:"/customers/" } tasks: { list:"/tasks/" } ...
```
**All wrong.** Real paths are `api/register/`, `api/login/`, `api/profile/<uuid>/`, `api/crm/leads/`, `api/tasks/`, `api/notifications/` etc. (see §8). Must be replaced before any integration.

### 12.3 Which backend APIs the React frontend will need
| Frontend need | Backend exists | Notes |
|---------------|----------------|-------|
| Login / register / logout / refresh / change-password / forgot/reset | Yes §8.1 | No `me` — use `profile/<uuid>` + decode JWT `user_id` |
| Roles / permissions / assign-role | Yes §8.1 | Admin/Manager only; list requires auth |
| Lead sources / pipelines / stages | Yes §8.2 | Lead create needs these dropdowns |
| Leads CRUD + assign/progress/lost/reengage/convert | Yes §8.2 | Convert is the biggest flow |
| Customer list/detail + smart-lookup + accounts/contacts | Yes §8.2 | Smart-lookup `?gst=&email=&phone=&company=` |
| Activities & audit-logs | Yes §8.2 | Audit logs Admin only |
| Quotations full lifecycle (12 endpoints) + PDF + email | Yes §8.2 | Versioning, approvals, line items |
| Tasks CRUD + assign + status | Yes §8.3 | Visibility filtered by role |
| Meetings create/detail/approval/reschedule/status/participants | Yes §8.3 | Manager approval required |
| Reminders CRUD + status | Yes §8.3 | Celery handles due/5-min |
| FollowUps CRUD + status | Yes §8.4 | Note `decription` typo vs `notes` search |
| Notifications inbox + mark read + templates + manual send | Yes §8.5 | Polling or WS? No WS — polling via query |
| CallForms 40+ routes (templates/versions/fields/stage-activities/attempts/submissions/triggers/adhoc/analytics/timeline) | Yes §8.6 | Largest frontend surface |
| Dashboard stats / charts | **Not determined — no dedicated stats endpoint** (only via querying counts per resource) | Frontend must aggregate |
| User list / admin users | **Not found** — only `profile/<uuid>` retrieve; no user list endpoint | Admin user management limited to assign-role; full CRUD missing |
| Master data for Task/Meeting status etc. | **No REST endpoint** — only admin | Frontend needs to either hard-code or request new endpoints |

### 12.4 Auth mechanism for React
- Use `JWTAuthentication` — header `Authorization: Bearer <access_token>`. Store `access_token` short-lived (15m) + `refresh_token` 7d. Must implement **interceptor**: attach access, on 401 try `POST api/refresh/` with refresh_token, retry, on fail redirect login. Backend has no `/auth/me/`; decode JWT payload `user_id` client-side or call `profile/<user_id>` after login.

### 12.5 State shapes
- **Auth state**: `{user_id, email, username, phone_number, role:{role_id,rolename,permissions}, access_token, refresh_token, isAuthenticated}`. Persist in `localStorage` or `httpOnly`? Currently no httpOnly — use `localStorage` with care + refresh.
- **Paginated list state**: TanStack Query infinite or paginated; shape `{count,next,previous,results}` — normalize to `results`.
- **Error shape** `axios` `error.response.data` varies (`{detail}`, `{field:[...]}`) — need `getApiErrorMessage()` helper.

---

## 13. Recommended Frontend Architecture

> Constraint: keep `React + React Compiler + JS + Vite + ESLint + React Router + Axios + TanStack Query + React Hook Form + Zod + Recharts` plus add `Tailwind CSS + shadcn/ui + Vitest + RTL + Playwright` as requested unless concrete reason not to.

### 13.1 Folder structure
```
frontend/src/
  api/
    axios.js              # instance + interceptors (auth, refresh queue, error normalize)
    endpoints.js          # CORRECT map mirroring §8 (grouped accounts/crm/tasks/followups/notifications/callforms)
    queryKeys.js          # factory: accountsKeys, leadKeys, taskKeys etc. for invalidation
  hooks/
    useAuth.jsx           # AuthContext + useAuth, usePermissions
    useDebounce.js
    usePagination.js
    useLeadMutations.js etc. (or per-feature)
  schemas/                # Zod mirrors backend validation §7
    auth.schema.js
    lead.schema.js
    task.schema.js
    meeting.schema.js
    quotation.schema.js
    callform.schema.js
  components/
    ui/                   # shadcn: button, input, card, dialog, table, badge, skeleton, toast, select, textarea
    common/               # AppHeader, Sidebar, PageLoader, ErrorBoundary, EmptyState, ConfirmDialog, ProtectedRoute, RoleGuard
    forms/                # FormField, FormSelect, FormDate, DynamicFieldRenderer (for CallForms)
    tables/               # DataTable + column helpers + pagination controls
  layouts/
    AuthLayout.jsx        # centered card for login/forgot/reset
    AppLayout.jsx         # sidebar + header + outlet + notification bell
  router/
    index.jsx             # createBrowserRouter([],) with lazy pages + loaders + errorElement
    guards.jsx            # RequireAuth, RequirePermission, RequireRole
  features/
    auth/                 # LoginPage, RegisterPage, ForgotPasswordPage, ResetPasswordPage, ChangePasswordPage, hooks/useAuthMutations
    dashboard/            # DashboardPage + widgets (stats from aggregated queries)
    leads/                # LeadsListPage, LeadCreatePage, LeadDetailPage (tabs: activities, quotations, tasks, timeline), hooks
    customers/            # CustomersListPage, CustomerDetailPage, SmartLookupModal
    pipelines/            # PipelinesPage (Admin/Manager)
    quotations/           # QuotationsListPage, QuotationDetailPage, LineItemsEditor, ApprovalBar, PdfPreview
    tasks/                # TasksListPage, TaskDetailPage
    meetings/             # MeetingsListPage (via tasks/meetings), MeetingRequestModal, ApprovalPanel
    reminders/            # RemindersPage
    followups/            # FollowUpsPage
    notifications/        # NotificationsPage, BellDropdown, TemplatesAdmin (Manager/Admin)
    callforms/            # TemplatesPage, VersionEditor, TriggerRulesPage, AdhocProposals, TimelineTab, AnalyticsCharts
    admin/                # RolesPage, PermissionsPage, AssignRoleModal, UsersPlaceholder
  pages/                  # re-export or thin wrappers for router lazy()
  utils/
    formatters.js         # formatDate(Asia/Kolkata), currency INR, phone
    errors.js             # normalizeApiError, getFieldErrors
    permissions.js        # hasPermission(codename), hasRole(name)
    constants.js          # status colors, query stale times
```

### 13.2 Routing structure `src/router/index.jsx`
- Public: `/login`, `/register`, `/forgot-password`, `/reset-password`
- Protected (AppLayout): `/` dashboard, `/leads`, `/leads/new`, `/leads/:id`, `/leads/:id/convert`, `/customers`, `/customers/:id`, `/pipelines`, `/quotations`, `/quotations/:id`, `/tasks`, `/tasks/:id`, `/meetings`, `/followups`, `/notifications`, `/callforms/*`, `/admin/roles`, `/admin/permissions`, `/profile` (+ `change-password` modal), `*` 404.
- Lazy: `const LeadsListPage = lazy(()=>import('@/features/leads/pages/List'))`.
- Guards: `element={<RequireAuth><RequirePermission perm="view_lead"><LeadsListPage/></RequirePermission></RequireAuth>}`.

### 13.3 Authentication architecture
- `src/hooks/useAuth.jsx` — `AuthContext` holds `user, tokens, role, permissions, isLoading, login(), logout(), refresh()`. On mount: read `localStorage` `access_token/refresh_token/user_id`, decode JWT exp, if valid fetch `GET api/profile/<user_id>/` to hydrate role/permissions, set axios default header, start refresh timer (14m). Interceptor in `api/axios.js` queues failed requests while refreshing.
- Token storage: `localStorage` (client-only) + consider `httpOnly` cookie if backend ever supports; for now document risk.
- Refresh: `POST api/refresh/` with `refresh_token`; on 400/401 clear storage + redirect `/login?expired=1`.

### 13.4 API architecture
- `api/axios.js` — `axios.create({baseURL: import.meta.env.VITE_API_BASE_URL, headers: {'Content-Type':'application/json'}})` + request interceptor inject `Authorization`, + response interceptor handle 401 refresh (with `isRefreshing` queue) and normalize errors (`error.apiMessage = normalizeApiError(error.response)`).
- `api/endpoints.js` — export grouped constants matching §8 real paths (no more `/auth/me/`). Example `auth: {register:"/register/", login:"/login/", logout:"/logout/", refresh:"/refresh/", changePassword:"/change-password/", profile:(id)=>`/profile/${id}/`}` etc. All paths under `VITE_API_BASE_URL` which already includes `/api`, so endpoints are suffixes like `/register/` not `/api/register/`.
- `api/queryKeys.js` — factory `leadKeys.list(filters)` for cache keys.
- No `fetch` wrappers — use axios directly in query functions for type-like control.

### 13.5 State management
- **Server state** → TanStack Query only (no Redux/Zustand). All lists = queries, mutations = mutations.
- **Client/UI state** → React `useState`/`useReducer` for filters, modals, pagination; URL search params for shareable filters.
- **Auth state** → Context (not Query) because needed synchronously for headers/guards.

### 13.6 TanStack Query organization
- Per feature file `features/leads/hooks/useLeads.js`:
  ```js
  export const useLeads = (filters) => useQuery({queryKey: leadKeys.list(filters), queryFn: ()=>api.get(endpoints.leads.list, {params:filters}).then(r=>r.data), staleTime: 30000});
  export const useCreateLead = () => useMutation({mutationFn: (data)=>api.post(...), onSuccess: ()=>queryClient.invalidateQueries({queryKey: leadKeys.all})});
  ```
- Group queries vs mutations; `queries: retry:1, refetchOnWindowFocus:false` already set in `main.jsx:10-13`.

### 13.7 Form architecture
- `react-hook-form` + `zodResolver` + `zod` schema per entity (`src/schemas/*`). Example lead schema mirrors `LeadSerializer` regex, required, stage pipeline. Forms use `FormField` wrappers feeding `control`. Submit → mutation; `form.setError` from API field errors.

### 13.8 Validation architecture
- Zod schemas replicate §7 (strip/empty checks, regex phone, date not past, etc.). Frontend shows inline errors before submit, plus server errors mapped.

### 13.9 Permission handling
- `utils/permissions.js` — `hasPermission(codename)` checks `user.role.permissions` (hydrate from profile roles/permissions list). For `HasDynamicPermission` views, frontend should hide buttons/links if missing perm, but also handle 403 gracefully.
- `components/common/RoleGuard.jsx` — `if (!hasPermission(required)) return <Forbidden/> or null` for button-level guard.

### 13.10 Reusable components (see §15)
- shadcn-based `ui/*` + domain `common/*` (guards, empty, loader, confirm).
- Every list page uses `DataTable` + pagination + search + filters; every form uses `Form` + `FormField`; every detail uses `Card` + `Tabs`.

### 13.11 Layouts
- `AppLayout` — sidebar nav filtered by role/permissions, header with user menu + notification bell (badge = unread count `GET api/notifications/?is_read=false`), main `Outlet`, toaster.
- `AuthLayout` — centered card, no nav.

### 13.12 Error / Loading / Empty
- Loading: `Skeleton` for tables/cards, `Spinner` for buttons, TanStack `isLoading`/`isFetching`.
- Empty: `EmptyState` with `Create first lead` CTA if list `count===0`.
- Error: `ErrorBoundary` + per-query `ErrorState` reading `normalizeApiError`, plus global `toast.error`.

---

## 14. Required Frontend Screens

> Only screens justified by actual backend endpoints (no invention).

| Group | Screen | Route (proposed) | Justified by |
|-------|--------|------------------|--------------|
| Auth | Login | `/login` | `POST api/login/` — required |
|  | Register | `/register` | `POST api/register/` — optional if public sign-up desired; else Admin-only but endpoint exists AllowAny |
|  | Forgot Password | `/forgot-password` | `POST api/forgot-password/` |
|  | Reset Password | `/reset-password` | `POST api/reset-password/` |
|  | Change Password | `/profile` modal or `/change-password` | `POST api/change-password/` |
|  | Logout (button) | in header | `POST api/logout/` |
| Dashboard | Dashboard (stats + charts) | `/` | No dedicated stats API — must aggregate counts from leads/tasks/quotations/notifications queries + recharts |
| Leads | Leads List (filters search pagination) | `/leads` | `GET api/crm/leads/` |
|  | Lead Create | `/leads/new` | `POST api/crm/leads/` needs sources/pipelines/stages dropdowns |
|  | Lead Detail (tabs: details, activities, quotations, tasks, timeline) | `/leads/:id` | `GET api/crm/leads/:id` + related |
|  | Lead Assign Modal | in detail/list | `POST .../assign/` |
|  | Lead Progress Modal |  | `POST .../progress/` |
|  | Mark Lost + Reengage actions |  | `POST .../lost/` + `.../reengage/` |
|  | Lead Convert Wizard (account/contact selection, gst) | `/leads/:id/convert` or modal | `POST .../convert/` |
| Lead Support | Lead Sources Admin | `/lead-sources` or settings | `GET/POST api/crm/lead-sources/` |
|  | Pipelines + Stages Admin | `/pipelines` | `GET/POST api/crm/pipelines/` + `pipeline-stages/` |
| Customers | Customers List | `/customers` | `GET api/crm/customers/` |
|  | Customer Detail (tabs: activities, lead link, financials) | `/customers/:id` | `GET api/crm/customers/:id` + activities |
|  | Smart Lookup | modal/page `/customers/lookup` | `GET api/crm/customers/smart-lookup/?gst=&email=` |
|  | Accounts/Contacts Admin | `/accounts` | `GET/POST api/crm/accounts/` etc. |
| Tasks | Tasks List (filters status/priority/category) | `/tasks` | `GET api/tasks/` (visibility role-filtered) |
|  | Task Create/Edit | `/tasks/new`, `/tasks/:id` | `POST api/tasks/` + `PATCH api/tasks/:id/` + `.../assign/` + `.../status/` |
| Meetings | Meetings List (via meetings/) | `/meetings` | `GET api/tasks/meetings/<id>` detail exists but no list endpoint — list via tasks meetings? Actually no list — will need to aggregate via task meetings or request backend adds `GET api/tasks/meetings/`; currently only Create+Detail — gap |
|  | Meeting Request Form | modal | `POST api/tasks/meetings/` manager required |
|  | Meeting Approval Panel (Manager) | `/meetings/:id/approvals` | `PATCH .../approval/` + `.../reschedule/` |
| Reminders | Reminders List | `/reminders` | `GET api/tasks/reminders/:id` detail but no list — again list missing; via task reminders? Gap |
| FollowUps | FollowUps List + Detail + Status | `/followups` | `GET api/followups/` + `POST` + `.../status/` |
| Quotations | Quotations List | `/quotations` | `GET api/crm/quotations/` |
|  | Quotation Detail (versions, approvals, line items) | `/quotations/:id` | `GET api/crm/quotations/:id` + `.../update-draft/` + `.../submit/` + `.../approve/` + `.../send/` + `.../revision/` + `.../accept/` + `.../reject/` + `.../pdf/` + `.../send-email/` |
|  | Quotation PDF Preview | link | `GET .../pdf/` |
| Notifications | Inbox (all / unread tab) | `/notifications` | `GET api/notifications/?is_read=` |
|  | Mark All/One Read | in inbox | `PUT .../<pk>/read/` |
|  | Templates Admin (Manager/Admin) | `/notifications/templates` | `GET/POST api/notification-templates/` |
|  | Manual Send (Admin) | modal | `POST api/notifications/send/` |
| Activities | Lead/Customer Activities tab | in lead/customer detail tabs | `GET api/crm/activities/` + `POST` |
| Audit Logs | Audit Logs Admin | `/audit-logs` | `GET api/crm/audit-logs/` (requires view_auditlog) |
| Admin | Roles List + Create/Edit + Assign Permissions | `/admin/roles` | `GET/POST api/roles/` + `PUT/PATCH/DELETE api/roles/:id/` |
|  | Permissions List | `/admin/permissions` | `GET/POST api/permissions/` |
|  | Assign Role to User | modal in roles or users | `PUT api/assign-role/<uuid>/` |
| CallForms | Templates List | `/callforms/templates` | `GET api/callforms/templates/` |
|  | Version Editor (fields, reorder, clone) | `/callforms/templates/:id/versions/:vid` | `versions/` + `fields/reorder/` + `clone/` |
|  | Stage Activities | `/callforms/stage-activities` | `GET api/callforms/stage-activities/` + `for-stage/` + `lead-primary-form/` |
|  | Call Attempts Log | `/callforms/attempts` | `GET api/callforms/attempts/?lead_id=` + `POST` |
|  | Form Submissions + Data | `/callforms/submissions` | `GET/POST api/callforms/submissions/` |
|  | Trigger Rules | `/callforms/trigger-rules` | `GET/POST api/callforms/trigger-rules/` |
|  | Adhoc Proposals + Review | `/callforms/adhoc-proposals` | `GET api/callforms/adhoc-proposals/` + `.../review/` |
|  | Submission Analytics Charts | in template detail | `GET api/callforms/submissions/analytics/?template_version_id=` |
|  | Lead Timeline | in lead detail tab | `GET api/callforms/submissions/lead-timeline/?lead_id=` |
|  | Indexed Values quick lookup | debug/admin | `GET api/callforms/indexed-values/` |

Total ≈ 45+ screens/modals. Meetings/Reminders list screens flagged as gaps (no list endpoint).

---

## 15. Required Reusable Components

### 15.1 UI (shadcn/ui) — must be installed via `npx shadcn init` after Tailwind
- `Button`, `Input`, `Textarea`, `Select` (with search), `Dialog`/`Sheet`, `Card`, `Badge`, `Tabs`, `Table` (`DataTable` with TanStack Table or plain), `Pagination`, `Skeleton`, `Spinner`, `Toast` (`sonner` or similar), `DropdownMenu`, `Popover`, `Calendar/DatePicker`, `Form` (wrapper around RHF), `Checkbox`, `RadioGroup`, `Avatar`, `Alert`.

### 15.2 Common (domain-agnostic)
- `AppLayout` / `AuthLayout` / `Sidebar` / `Header` (with notification bell + user menu)
- `ProtectedRoute` + `RoleGuard` + `PermissionGuard`
- `PageLoader` / `PageError` / `EmptyState` (illustration + CTA) / `ConfirmDialog` / `ErrorBoundary`
- `StatusBadge` (color per lead/task/quotation status)
- `SearchInput` (debounced) + `FilterBar`
- `CopyButton`, `FormattedDate` (Asia/Kolkata), `Currency` (INR), `PhoneLink`

### 15.3 Forms
- `FormField` (label+error+control), `FormSelectAsync` (fetch pipeline stages), `FormDate`, `FormTime`, `DynamicFieldRenderer` (for CallForms template fields: text/textarea/number/boolean/date/time/select), `LineItemsEditor` (quotation), `AdhocFieldInput`.

### 15.4 Tables
- `DataTable` (sorting, pagination, column visibility), column defs per entity, row actions menu (View/Edit/Delete/Assign/Progress/Convert etc.).

### 15.5 Charts
- `LeadsByStageBar` (Recharts BarChart from `GET leads` aggregation), `QuotationsByStatusPie`, `TasksByStatusArea`, `SubmissionAnalyticsBar` (from CallForms analytics), `Timeline` vertical feed component.

---

## 16. Frontend State/API Strategy

### 16.1 What is Query vs Mutation
| Type | Query (GET, cached, auto-refetch) | Mutation (POST/PUT/PATCH/DELETE) + invalidate |
|------|-----------------------------------|-----------------------------------------------|
| Queries | Leads list/detail, customers, pipelines/stages, accounts/contacts, activities, auditLogs, quotations, tasks, followups, notifications, notification templates, callforms templates/versions/fields/stage-activities/attempts/submissions/analytics/timeline, smart-lookup, profile | — |
| Mutations | — | Create/update/delete lead, assign/progress/lost/reengage/convert; create activity; create/update quotation, submit/approve/reject/send/revision/accept/reject/email/pdf; create/update/delete task, assign, status; create meeting, approval, reschedule, add/remove participants; create/update/delete reminder; create/update/delete followup + status; mark notification read, create template, manual send; register/login/logout/changePassword/forgot/reset; create role/assignRole; CallForms create template/version/field, clone, reorder, create trigger, propose/review adhoc, log attempt, submit form |

### 16.2 Cache invalidation graph
- `leadKeys.all` invalidated by: assign, progress, lost, reengage, convert, update, create → refetches lists + detail + dashboard
- `customerKeys.all` invalidated by: convert (creates customer), customer create, smart-lookup does not need.
- `quotationKeys.allForLead(leadId)` invalidated by: create, updateDraft, submit, approve, send, revision, accept, reject → refetches `quotations/?lead=` and detail and lead detail (status)
- `taskKeys.list` invalidated by: create, update, assign, status, delete → also `followUpKeys` if via activity
- `meetingKeys.all` invalidated by: create, approval, reschedule, participant add/remove, status
- `notificationKeys.inbox` → poll every 30s? `refetchInterval: 30000` or via manual invalidate on mark-read; `notificationKeys.templates` on template CRUD
- `callFormKeys.*` granular: `templateKeys`, `versionKeys`, `attemptKeys.lead(leadId)`, `submissionKeys.lead(leadId)` invalidated by submit, etc.

### 16.3 Pagination & filters as URL state
- Use `useSearchParams` for `page, page_size, search, status, pipeline, ordering` → query key includes them → shareable URLs + back button.

---

## 17. Frontend Validation Strategy

### 17.1 Zod schemas must mirror §7 exactly
| Entity | Zod rules (mirror backend) | Extra UX |
|--------|----------------------------|----------|
| Register | `username` min 1, `email` email(), `phone_number` regex `^\d{10}$` (model max 10 but serializer no regex — follow model), `password` min 8 with `validate_password` try but warn weak still passes backend | Show hint weak but allowed |
| Login | email + password required | — |
| ChangePassword | old required, `new_password` min 8, not common etc. via `zod` + async check old via API | server 400 wrong old |
| Profile | read-only | — |
| Lead | `name` min 1, `email` optional email, `phone` regex `^[0-9+\-()\s]{7,20}$`, `source` uuid required active, `pipeline` uuid required active, `current_stage` validates belongs to pipeline (client via fetched stages), `assigned_to` uuid active | Disable inactive options |
| Activity | exactly one of `lead`/`customer` required, `activity_type` enum, `outcome` min 1 max 255, `follow_up_required` bool, `follow_up_date` required if true and > now, must not be CONVERTED lead (show warning) | — |
| Task | `task_title` 3-200, `due_date` > now, `lead` required | — |
| Meeting | `meeting_title` 3+, `meeting_date` >= today, `end_time` > `start_time`, `manager` required Manager role, `location` or `meeting_link` conditional on type | — |
| Quotation line item | `quantity` >=1, `unit_price` >=0.01, `description` min 1 | total auto-calc |
| CallForms field | `field_key` regex `^[a-z0-9_]+$`, SELECT requires options | — |
| Reminder | `message` min 1, `reminder_datetime` > now | — |
| FollowUp | `followup_date` > now | note `decription` typo — schema should use `decription` to match backend |

### 17.2 Server error mapping
- `normalizeApiError(error)` → `{message: string, fieldErrors: Record<string,string>}` extracting `detail` or first field message.
- On mutation `onError`: `if (fieldErrors) form.setError(...)` else toast.

### 17.3 What backend validations must be reflected in UI
All date-not-past rules (§7.2-7.5) should disable past dates in pickers; stage pipeline mismatch should filter stages after pipeline chosen; quotation approval block should disable Convert button with tooltip "Quotation required (stage requires accepted quotation)"; duplicate email+phone should be shown as field-level if 400 mentions.

---

## 18. Frontend Permission Strategy

- Hydrate `user.role.permissions: string[]` (codenames) after login via `GET roles/` or `GET profile`? Currently `ProfileSerializer` returns `role` as ID (not expanded). Need to fetch `GET api/roles/` or expand profile to include `role.permissions` — check `ProfileSerializer` fields include `role` (likely id). Will need an extra call `GET api/roles/` filtered or `GET api/permissions/` to map. Simplest: on login also `GET api/roles/` and find matching role to get codenames.
- `hasPermission(codename)` → `!!userRole.permissions.includes(codename)`. For fallback if role is null → deny all (except superuser).
- **Route guard**: `RequirePermission({perm, children})` checks `hasPermission` else redirect `/forbidden` or hide link.
- **Element guard**: Buttons like "Assign Lead" render only if `hasPermission('assign_lead')`; list fetch will 403 if not, so hide preemptively.
- **Admin screens** (`/admin/roles`) visible only to `hasRole('Admin')||hasRole('Manager')` + `hasPermission('view_role')`.
- **Employee vs Manager view**: Task list already server-filtered; UI just shows same table but manager sees all, employee sees own — no client branching needed beyond info text.
- **Meeting approval** UI: Show Approve/Reject buttons only if `user_id === meeting.manager` and `hasPermission('change_meeting')` and `approval_status===PENDING`.
- **Quotation approve** UI: Show approve button if `stage.quotation_approval_required` and version `PENDING_APPROVAL` and not self-approval violation (hide if submittedBy === current user and not superuser without `approve_own_quotation`).

---

## 19. Important Business Rules for UI

> Each rule cites implementation location for traceability.

| # | Rule | Location | UI implication |
|---|------|----------|----------------|
| 1 | Lead creation must use first stage of pipeline | `customer_management/services.py: create_lead` `display_order` check | Lead Create form should auto-select first stage or disable others; validate before submit |
| 2 | Duplicate active lead by email+phone blocked | `CRMService.create_lead / assign_lead` duplicate check | Show field-level duplicate error; Smart Lookup before create |
| 3 | Stage must belong to pipeline | `Lead.clean` + `LeadSerializer` stage pipeline mismatch | Pipeline select filters Stage dropdown |
| 4 | Inactive source/pipeline/stage/assignee rejected | `LeadSerializer` + `CRMService` active checks | Dropdowns must hide inactive or show disabled with "(inactive)" |
| 5 | Convert requires ACTIVE lead only; CONVERTED/LOST blocked | `CRMService.convert_lead` status check | Convert button disabled with status badge if not ACTIVE |
| 6 | Convert requires accepted quotation if stage `requires_quotation` | `convert_lead` `stage.requires_quotation` check | Convert wizard must show quotation status and block with message |
| 7 | Convert exact email+phone returns existing customer (idempotent) | `convert_lead` exact match | Show success with existing customer link, not error |
| 8 | Convert email OR phone alone → 400 duplicate | `convert_lead` email_match/phone_match | Form must validate both provided or at least not colliding |
| 9 | Account matching: gst_number exact → company_name iexact → create | `convert_lead` account block | Wizard should allow entering GST/company and show matched account preview |
| 10 | Lead status direct PATCH blocked; use dedicated endpoints | `LeadSerializer` status check | Detail edit form must not expose status field; use dedicated buttons |
| 11 | LOST requires reason+timestamp; non-LOST must not have them | `Lead.clean` | Lost modal requires textarea; Reengage button only on LOST |
| 12 | Task requires lead; customer must match lead if both | `Task.clean` + `TaskSerializer.validate_lead` | Task Create form lead required; if customer chosen, validate via API or hide customer until lead chosen |
| 13 | Tasks soft-delete (`is_active=False`) visible only Admin/Manager | `TaskDetailView` delete + `TaskListCreateView` filter | Delete button soft-deletes; Employee cannot delete others |
| 14 | Meeting manager must be Manager role | `MeetingCreateView` manager role check 400 | Manager dropdown filtered to role Manager |
| 15 | Meeting approval only by `meeting.manager` with Manager role and PENDING only | `MeetingApprovalView` owner+role+status check 403/400 | Approval bar visible only to assigned manager; show 403 if not owner |
| 16 | Meeting reschedule only by created_by and only if REJECTED | `MeetingRescheduleView` checks | Reschedule button only on REJECTED and owned |
| 17 | Meeting auto-generates Google Meet link or office location if missing per type | `services.py` `ONLINE_MEETING_TYPE_ID=1` etc. | UI can show "Auto link will be generated" hint |
| 18 | 5-min reminder via Celery every minute for today's APPROVED meetings | `Task/tasks.py: meeting_reminder_job` | No UI action; bell will receive notification |
| 19 | FollowUp `decription` typo field name vs `notes` search | `FollowUp/models.py: decription` + `views.py` search `notes/task_title` | Form must use `decription` key (keep typo) but label "Description" |
| 20 | FollowUp POST uses `change_followup` perm, not `add_followup` | `FollowUp/views.py: FollowUpListCreateView.permission_names` | Permission guard must check `change_followup` for create |
| 21 | Quotation total must equal sum line items | `QuotationVersion.clean` | LineItemsEditor must auto-sum and show mismatch |
| 22 | Quotation draft only editable in DRAFT | `update_draft_quotation` status check | Edit button disabled if not DRAFT with tooltip |
| 23 | Quotation submit only DRAFT/REVISED | `submit_quotation_for_approval` | Submit button only in those states |
| 24 | Self-approval blocked without `approve_own_quotation` (unless superuser) | `approve_quotation` perm check 403 | Hide Approve if `submitted_by === currentUser` and not superuser with perm |
| 25 | Quotation send only APPROVED | `send_quotation` status check | Send button only APPROVED |
| 26 | Quotation accept auto-converts lead (creates Customer) | `accept_quotation` calls `convert_lead` | Accept button should show "Will create Customer" confirmation |
| 27 | Reject quotation auto marks lead LOST with reason | `reject_quotation` calls `mark_lead_lost` | Reject modal requires reason and warns "Lead will be marked Lost" |
| 28 | PDF blocked for DRAFT/PENDING | `QuotationPDFView` check | PDF button disabled with tooltip |
| 29 | Activity exactly one of lead/customer; CONVERTED lead blocked; auto Task if followUp | `Activity.clean` + `services.create_activity` | Form must enforce XOR via radio; show CONVERTED warning |
| 30 | CallForms version locked after submissions blocks field edits | `TemplateVersion.is_locked` + `serializers.clean` | Version editor must show "Locked (has submissions)" and disable edit |
| 31 | Trigger `suggest_mark_lost` after 5 consecutive failed attempts | `services.log_call_attempt` threshold `CALL_FORMS_MAX_FAILED_ATTEMPTS=5` | Attempt log should show banner "Suggest marking lost" when `suggest_mark_lost` true |
| 32 | OTP length 6, 5-min expiry (view) vs 10-min (.env), max 3 attempts (view) vs 5 (.env) | `accounts/views.py` constants drift | UI must show 6-digit input, countdown 5 min, attempts remaining message |
| 33 | JWT user_id is UUID, role nullable — no role denies most perms | `settings.SIMPLE_JWT` + `HasDynamicPermission` no-role check | Register creates no role? Actually Employee — but handle "No role" empty state |

---

## 20. Gaps / Risks

> **Do NOT fix now** — report only. Severity: 🔴 blocker / 🟡 risk / 🟢 minor.

| # | Severity | Area | Finding | Impact | Location |
|---|----------|------|---------|--------|----------|
| G1 | 🔴 | CORS | `crm/settings.py:74-82` has **no** `corsheaders` / `CorsMiddleware` / `CORS_ALLOWED_ORIGINS` | Browser dev on `localhost:5173` → `localhost:8000` will be blocked by CORS. Must add `django-cors-headers`, `MIDDLEWARE` entry, env var. | `crm/settings.py:74-82` |
| G2 | 🔴 | Frontend endpoints | `frontend/src/api/endpoints.js:3-29` map is **entirely placeholder** (`/auth/*` vs `/register/` etc.) | No frontend request will succeed until map is rewritten to §8 real paths. | `frontend/src/api/endpoints.js:1-31` |
| G3 | 🔴 | Frontend auth wiring | `frontend/src/api/axios.js:1-10` has **no interceptor**, no `Authorization` header injection, no refresh queue, no error normalize. `VITE_API_BASE_URL` includes `/api` but endpoints add leading slash — risk double slash or missing prefix. | Login will store tokens but no subsequent request will be authenticated; 401 refresh loop. | `frontend/src/api/axios.js:1-10`, `main.jsx:1-23` |
| G4 | 🔴 | Current user | No `GET /auth/me/` (or `api/me`) — `endpoints.js` claims `/auth/me/` does not exist. Only `GET api/profile/<uuid>/`. | Frontend must decode JWT `user_id` or persist user_id; no discovery after refresh without storing. | `accounts/urls.py:25`, `endpoints.js:5` |
| G5 | 🟡 | Token storage | No httpOnly cookie strategy; tokens in localStorage XSS risk | Security decision needed before implementing. | `accounts/views.py: Login` returns tokens in JSON (no httpOnly) |
| G6 | 🟡 | No user list | No `GET api/users/` endpoint; only profile retrieve. Admin cannot list users to assign roles except via known UUIDs. | AssignRole UI needs user search — will need new backend endpoint or admin via Django admin. | `accounts/urls.py` |
| G7 | 🟡 | No master data endpoints | `TaskStatus/Priority/Category`, `MeetingStatus/Type` etc. have **no REST list** endpoints (only admin). | Task/Meeting forms need dropdowns — frontend will have to hard-code or backend must add endpoints. | `Task/models.py:1-50` vs `Task/urls.py` |
| G8 | 🟡 | Meetings/Reminders list missing | `Task/urls.py:41-95` has `POST meetings/` and `GET meetings/<id>/` but **no** `GET meetings/` list; similarly `reminders/` only POST + detail. | Meetings/Reminders list screens cannot be built as spec'd; will need to request `GET meetings/` list or reuse task meetings relation. | `Task/urls.py:36-95` |
| G9 | 🟡 | Duplicate URL entries | `Task/urls.py:51-60` duplicates `meetings/<id>/` and `.../approval/` entries (identical). | Harmless but confusing; last entry wins; indicates incomplete refactor. | `Task/urls.py:51-60` |
| G10 | 🟡 | OTP config drift | `accounts/views.py: ~15` `OTP_LENGTH=6, EXPIRY=5, MAX=3` vs `.env` `6/10/5` vs `settings` default `6/5/3` via `load_dotenv` — three sources disagree. | Frontend countdown/attempts UX will be wrong; user may see "5 min" but backend expires in 5 vs 10. | `accounts/views.py:1-20`, `backend/.env:29-31`, `crm/settings.py` (none for OTP) |
| G11 | 🟡 | Inconsistent error formats | Accounts returns `{"detail":"..."}`, `{"email":[...]}`; Task returns `{"detail":...}` or `{"error":...}`; CallForms raises `ValidationError` dict; Notification returns `{"error":...}`. | `normalizeApiError` must handle multiple shapes; forms need field mapping. | Multiple `views.py` |
| G12 | 🟡 | `decription` typo | `FollowUp/models.py: decription` (not `description`) but serializer and search use `notes/task_title` | Frontend must send `decription` (typo) to match backend; docs will confuse devs. | `FollowUp/models.py:1-49`, `FollowUp/serializers.py` |
| G13 | 🟡 | FollowUp POST perm `change_followup` not `add_followup` | `FollowUp/views.py: FollowUpListCreateView.permission_names POST change_followup` | Devs expecting `add_followup` will be denied 403. Must document. | `FollowUp/views.py: ~30` |
| G14 | 🟡 | `VITE_API_BASE_URL` includes `/api` | `frontend/.env:1` `http://127.0.0.1:8000/api` | If endpoints also include `/api` prefix, double `/api/api/` will 404. Must ensure endpoints are suffixes `/register/` not `api/register/`. | `frontend/.env:1`, `frontend/src/api/endpoints.js` |
| G15 | 🟡 | Meetings `is_active` soft-delete but no list filter | `Meeting` has `is_active` but list endpoint does not exist; soft-deleted meetings may still appear if list added | Need spec for filtered list. | `Task/models.py: Meeting.is_active` |
| G16 | 🟢 | `Task/serializers.py` duplicate `created_by` read_only, `TaskListCreateView` log no audit comment | Minor code quality | — | `Task/serializers.py` |
| G17 | 🟢 | `AuditLog` integer PK note | `audit_log/models.py` docstring warns integer PK vs UUID; code uses `uuid5` — works but fragile | Frontend audit-log display may show deterministic UUID not original id | `audit_log/services.py:8-20` |
| G18 | 🟢 | `frontend/dist/` stale build | `dist` not needed in repo; `.gitignore` lists `dist` but folder exists with old build | Ignore | `frontend/dist/` |
| G19 | 🟢 | Missing Tailwind/shadcn/Vitest | `package.json` has no tailwind, shadcn, vitest, RTL, playwright despite prompt requiring | Will need `npm install -D tailwindcss + init` before UI work | `frontend/package.json:1-37` |
| G20 | 🟢 | `ALLOWED_HOSTS=127.0.0.1` only | `backend/.env:4` `ALLOWED_HOSTS=127.0.0.1` | Will block `localhost` or docker `web` host without edit. | `backend/.env:4`, `crm/settings.py:47-49` |
| G21 | 🟡 | Refresh not rotated, but logout blacklists | `SIMPLE_JWT ROTATE false` + logout blacklists single token; stolen refresh usable until expiry | Consider rotate or short-lived refresh | `crm/settings.py:214-216` |
| G22 | 🟢 | `CallForms` `stage-activities/lead-primary-form/` vs `for-stage/` need stage_id query | Docs fine but frontend must know to call correct | — | `CallForms/urls.py` actions |

---

## 21. Recommended Implementation Order

> Phased to unblock vertical slice early (auth → leads) and defer largest subsystem (CallForms) to last.

**Phase 0 — Pre-flight (backend fixes, 0.5 day)**
- Add `django-cors-headers` to `requirements.txt` + `INSTALLED_APPS` + `MIDDLEWARE` + `CORS_ALLOWED_ORIGINS` in `crm/settings.py:74-82` (allow `http://localhost:5173`). Fix `ALLOWED_HOSTS` to include `localhost,web`. Reconcile OTP constants in `accounts/views.py` vs `.env`. Fix `frontend/src/api/endpoints.js` map to §8. Add missing user list or document workaround. Decide token storage.

**Phase 1 — Foundation (1-2 days)**
1. Install Tailwind + shadcn/ui init + Vitest/RTL/Playwright (no code changes yet, only config). Add `@/` alias in `vite.config.js` and `jsconfig.json`.
2. Rebuild `src/api/axios.js` with interceptors (auth header, refresh queue, normalize). Create `src/api/queryKeys.js`.
3. Create `src/schemas/*` zod mirrors (§17).
4. Create `ui/` shadcn primitives (Button, Input, Card, Dialog, Table, Badge, Skeleton, Toast) + `common/` (AppLayout, AuthLayout, ProtectedRoute, RoleGuard, EmptyState, PageLoader).
5. Implement `src/hooks/useAuth.jsx` + `src/router/index.jsx` with lazy routes + guards. Verify login→profile hydrates.

**Phase 2 — Auth vertical slice (1 day)**
6. `features/auth` Login, Register, Forgot, Reset, ChangePassword pages + forms + mutations. Handle 401/403 toasts, redirect, refresh.

**Phase 3 — CRM core: Leads → Customers (2-3 days)**
7. `features/leads` LeadsList (DataTable + pagination + search + filters `status/pipeline/assigned_to`), LeadsCreate (with LeadSource/Pipeline/Stage selects), LeadDetail tabs (header with status badge + action bar Assign/Progress/Lost/Reengage/Convert), SmartLookup modal.
8. `features/customers` CustomersList, CustomerDetail, Accounts/Contacts admin (if manager).
9. Pipelines/Stages admin pages (Manager/Admin).

**Phase 4 — Quotations (2 days)**
10. QuotationsList, QuotationDetail with LineItemsEditor, version timeline, approval bar (approve/reject), send/revision/accept/reject flows, PDF link, SendEmail modal. Need to handle self-approval guard.

**Phase 5 — Tasks + Meetings + FollowUps (2 days)**
11. TasksList + TaskCreate/Detail + Assign/Status.
12. Meetings request modal + Approval panel (Manager) + Reschedule flow; participants add/remove.
13. Reminders + FollowUps pages (handle `decription` typo, status update).

**Phase 6 — Notifications + Admin + Activities (1 day)**
14. Notifications bell (poll `is_read=false` every 30s) + inbox tabs + mark read + templates admin + manual send.
15. Activities tab in lead/customer, AuditLogs admin.
16. Admin Roles/Permissions + Assign Role UI.

**Phase 7 — CallForms engine (3-4 days, largest)**
17. Templates list + Template builder (fields CRUD + reorder drag + clone + lock banner).
18. Stage Activities linking + lead-primary-form consumer in LeadDetail.
19. Call Attempts logging + Form Submission (DynamicFieldRenderer from template fields) + submission list + indexed-values filter.
20. Trigger Rules + Adhoc Proposals + Review flow + Analytics charts (Recharts) + Timeline feed.

**Phase 8 — Dashboard + Polish (1-2 days)**
21. Dashboard aggregating counts: `GET leads/?count`, `GET tasks/?status=`, `GET quotations/?status=` etc. + Recharts (Leads by stage, Quotations by status, Tasks due). Recent activity feed from `audit-logs` or `activities`.
22. Global polish: Empty states, loading skeletons, error boundaries, 403/404 pages, responsive, accessibility, Playwright e2e for critical flows (login → create lead → convert → quotation → accept).

Total estimated effort: **~14-18 dev days** for one engineer; can be parallelized after Phase 1.

---

## 22. Files That Will Need Changes Later

> For implementation reference — **do not change now**.

| File | Action | Reason |
|------|--------|--------|
| `frontend/.env` | May need `VITE_API_BASE_URL=http://127.0.0.1:8000/api` confirmed; no change unless Docker host differs (`http://web:8000` not reachable from browser). | Keep as is for local; document. |
| `frontend/vite.config.js:1-11` | Add `resolve.alias @ -> src`, `server.port/proxy`, `test` (vitest) config. | Path aliases + Vitest. |
| `frontend/eslint.config.js:1-21` | Add `eslint-plugin-tailwindcss` + ignore `components/ui` if generated. | Tailwind/shadcn. |
| `frontend/package.json:1-37` | Add `tailwindcss, autoprefixer, class-variance-authority, clsx, tailwind-merge, lucide-react, sonner, @testing-library/*, vitest, jsdom, playwright` and scripts `test, test:ui, e2e`. | Required stack. |
| `frontend/src/main.jsx:1-23` | Wrap with `BrowserRouter` or switch to `RouterProvider`; add `ReactQueryDevtools`, `Toaster`. | Routing + devtools + toasts. |
| `frontend/src/App.jsx:1-10` | Replace with router outlet (`<RouterProvider>` or `<Routes>`). | All screens. |
| `frontend/src/index.css:1-20` | Replace with Tailwind `@tailwind ...` + CSS variables for shadcn. | Styling. |
| `frontend/src/api/axios.js:1-10` | Add interceptors (auth, refresh queue, error normalize). | Critical for auth. |
| `frontend/src/api/endpoints.js:1-31` | **Complete rewrite** to §8 real paths grouped `accounts, crm, tasks, followups, notifications, callforms`. | Fixes G2. |
| `frontend/src/components/**` | Create `ui/*`, `common/*`, `forms/*`, `tables/*` per §15. | New files (empty dirs). |
| `frontend/src/features/**` | Create per-feature folders per §13.1. | New files. |
| `frontend/src/hooks/` | Create `useAuth.jsx, useDebounce, usePermissions` etc. | New. |
| `frontend/src/layouts/` | Create `AppLayout, AuthLayout`. | New. |
| `frontend/src/router/` | Create `index.jsx, guards.jsx`. | New. |
| `frontend/src/schemas/` | Create zod schemas per §17. | New. |
| `frontend/src/utils/` | Create `formatters, errors, permissions, constants`. | New. |
| `frontend/src/pages/` | Optional thin re-exports for lazy routing. | New. |
| `backend/crm/crm/settings.py:74-82, 47-49` | Add `corsheaders`, `CORS_ALLOWED_ORIGINS`, expand `ALLOWED_HOSTS`. | Fix G1/G20. |
| `backend/requirements.txt:1-97` | Add `django-cors-headers` if not present (check — not in current 97). | For cors. |
| `backend/crm/Task/urls.py:51-60` | Remove duplicate entries. | Code quality. |
| `backend/crm/accounts/views.py: ~15` | Reconcile OTP constants to single source (env). | Fix G10. |
| `backend/crm/Task/models.py` | Consider adding `GET meetings/` list + `GET reminders/` list endpoints. | Fix G8. |

---

## READY FOR FRONTEND IMPLEMENTATION — Assessment

### Verdict: **CONDITIONAL GO — fix 3 blockers first, then ready**

The backend is **feature-complete and heavily tested** — every major CRM workflow (lead pipeline, quotation versioning/approvals, tasks/meetings with approval & reminders, follow-ups, notifications, CallForms engine) is implemented, documented via OpenAPI (`/schema/ /docs/`), and covered by extensive pytest suites. No backend feature invention is needed; the API map in §8 is authoritative (verified against actual `urls.py` files).

The frontend scaffold is **truly empty** — only `main.jsx`, `App.jsx`, `axios.js`, `endpoints.js` exist. This is intentional (greenfield), but it means **all** of §13–§19 must be built.

**Before writing any React UI, fix these 3 blockers (≤ half day):**

1. **CORS** (`G1`): add `django-cors-headers` + `CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173` to `crm/settings.py:74-82` and `ALLOWED_HOSTS` to include `localhost,web`. Without this, every `fetch` from Vite dev server will be `CORS error` and you will mis-diagnose as auth bug.
2. **Endpoint map** (`G2`): replace `frontend/src/api/endpoints.js:1-31` placeholders with §8 real paths. Do this before any `useQuery` is written.
3. **Axios auth wiring** (`G3`): add `Authorization: Bearer` injection + 401 refresh queue + error normalize in `frontend/src/api/axios.js:1-10`. Without it, login succeeds but no protected screen loads.

**Strongly recommended (same day):** expand `vite.config.js` with `@` alias, install Tailwind+shadcn (generates `components.json`, `tailwind.config.js`, `src/components/ui/*`), add Vitest/RTL/Playwright scripts to `package.json`. These are assumed in §13 and without them you will drift from the requested stack.

Once blockers are cleared, proceed in order **Phase 1 → Phase 2 → Phase 3 …** (§21). The first vertical slice (auth + leads list/create) can be demoable in **~3 days**. The largest risk is underestimating **CallForms** (Phase 7) — reserve 3-4 days; it is a full form-builder with version locking, dynamic rendering, trigger rules, analytics and timeline.

**No backend schema/migration changes are required** for initial frontend. If later you need `GET /users/` list or `GET meetings/` list or master-data endpoints, add them as small DRF views (permission-guarded) without breaking existing contracts.

---

*Report generated read-only. All paths absolute under `C:/Users/developer/Downloads/CRM/DemoCRM`. References formatted as `file:line` for jump-to-source. “Not determined from current code” noted where no code evidence exists (e.g., dashboard stats aggregation — no dedicated endpoint found, must be computed client-side).*
