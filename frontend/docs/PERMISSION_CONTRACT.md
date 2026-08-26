# PERMISSION_CONTRACT

> Facts verified from code: `backend/crm/accounts/permissions.py`,
> `accounts/models.py` (Role, CustomUser), `accounts/signals.py` (seed maps),
> and per-view `permission_names` declarations.

## How backend authorization works

```py
class HasDynamicPermission(BasePermission):
    # superuser → allow everything
    # no role (role is nullable FK) → deny everything
    # else → role.permissions M2M must contain the codename the view
    #        declares for the request method
```

- Roles are seeded: **Admin** (= all permissions), **Manager**, **Employee**
  (`accounts/signals.py`, applied on post_migrate).
- Permissions are Django's built-in `auth.Permission` rows, referenced by
  `codename`.
- Superuser bypasses all checks. A user with **no role is denied by default**.
- Frontend gating is UX only — the backend stays authoritative; every gated
  action must still handle a 403 gracefully.

## Where codenames come from — RESOLVED (verified from views + live schema)

Login response: tokens only. Profile response: `{message, profile:{..., role:<int>}}`
— no codenames.

`GET /roles/` requires `view_role`, which **only Admin** (and superusers) has —
`role`/`permission` are absent from both the Manager and Employee seed lists
(`accounts/signals.py:33-130`). The roles list response is also nested:
`{ message, roles: [RoleListSerializer...] }`.

Therefore client-side permission hydration is:

1. After login → decode JWT → `GET /profile/<user_id>/` → read
   `response.data.profile.role` (integer id) — but this gives no rolename.
   To display the rolename, Admin can resolve via `GET /roles/`; everyone else
   relies on the fallback below.
2. **Fallback (primary path for Manager/Employee):** hardcode the seed maps
   from `accounts/signals.py` in `src/utils/permissions.js`, keyed by
   rolename. These maps ARE the effective grant set unless an Admin edits
   roles via the admin UI. Keep them in sync with signals.py; document any
   drift in BACKEND_GAPS.md.
3. `hasPermission(codename)` checks the hydrated/fallback set; superusers
   bypass everything.

## ⚠️ Critical seed finding (filed as G23)

The seeded Manager and Employee roles contain **no permissions for any
`customer_management` model**: `lead`, `leadsource`, `pipeline`,
`pipelinestage`, `quotation*`, `activity`, nor `view_auditlog`. Under default
seeds:

- **Only Admin** can access Leads / Pipelines / Quotations / Activities /
  Audit Logs modules.
- Employees have `add_followup` but the FollowUp create endpoint requires
  `change_followup` (G13) — so **Employees cannot create follow-ups at all**
  under default seeds.

UI implication: gate nav/buttons on real hydrated permissions and handle 403s
gracefully — do NOT assume every role can open Leads. This is very likely a
backend seed oversight to raise with the backend owner.

## Seed permission maps (`accounts/signals.py`)

- **Admin:** all permissions (None = unrestricted).
- **Manager:** `{view,add,change,delete}_<model>` for ~64 model prefixes,
  plus custom: `assign_task`, `send_notification`, `manage_*` family,
  `add_adhoc_field`.
- **Employee:** `view_<model>` for ~31 model prefixes, plus write customs:
  `change_task`, `add_meeting`, `add_meetingparticipant`, `add_followup`,
  `add_callattempt`, etc.

## Codenames the frontend must gate on (per endpoint, verified)

| Action | Codename | Gotcha |
|---|---|---|
| Leads list | `view_lead` | |
| Lead create | `add_lead` | First-stage rule enforced server-side |
| Lead edit | `change_lead` | Status NOT editable here — dedicated endpoints only |
| Lead assign / progress / lost / reengage / convert | `assign_lead` / `progress_lead` / `mark_lead_lost` / `reengage_lead` / `convert_lead` | One codename per workflow button |
| Tasks list | `view_task` | Server filters: Employee sees own only |
| Task create / edit / delete | `add_task` / `change_task` / `delete_task` | Soft delete; Employee can't touch others' tasks |
| Task assign / status | `assign_task` / `change_taskstatus` | |
| Meetings create / detail | `add_meeting` / IsAuthenticated | Manager role required for chosen manager (400 otherwise) |
| Meeting approval / status | `change_meeting` | Owner + Manager + PENDING enforced server-side |
| Participants add/remove | `add_meetingparticipant` / `delete_meetingparticipant` | |
| Reminders CRUD/status | `view/add/change/delete_reminder`, `change_reminderstatus` | |
| FollowUps list/detail | `view_followup` | |
| FollowUp **create** | `change_followup` | ⚠️ NOT `add_followup` (G13) — gate Create button on this |
| FollowUp delete / status | `delete_followup` / `change_followupstatus` | DELETE is hard delete |
| Quotations list/create | `view_quotation` / `add_quotation` | |
| Quotation draft edit | `change_quotation` | DRAFT only |
| Quotation submit | `submit_quotation` | |
| Quotation approve/reject-approval | `approve_quotation` | Self-approval additionally requires `approve_own_quotation` or superuser (403 otherwise) |
| Quotation send / send-email | `send_quotation` | APPROVED only |
| Revision | `request_quotation_revision` | |
| Accept / reject | `accept_quotation` / `reject_quotation` | Accept auto-converts lead; reject auto-marks lead LOST |
| Activities list/create | `view_activity` / `add_activity` | lead XOR customer enforced server-side |
| Audit logs | `view_auditlog` | Admin-only in practice |
| Notification inbox | IsAuthenticated (owner-scoped) | No codename needed |
| Notification templates CRUD | `view/add/change/delete_notificationtemplate` | |
| Manual notification send | `send_notification` | Manager/Admin |
| CallForms templates/versions/fields/stage-activities | `manage_call_template`, `manage_template_version`, `manage_template_field`, `manage_stage_activity` (+ view equivalents) | Version locking enforced server-side |
| Adhoc proposals create/review | `add_adhoc_field` / `manage_adhoc_field` (+ `view_adhocfieldproposal`) | |
| Roles / permissions admin | `view_role`… / `view_permission`… | Admin/Manager only |

## Object-level rules the UI must mirror

- Task/FollowUp lists: Admin/Manager see all, Employee sees own (server-filtered).
- Meeting approval buttons: only when `currentUser.user_id === meeting.manager`
  AND role is Manager AND status PENDING.
- Meeting reschedule: only creator AND status REJECTED.
- Quotation Approve: hide when `submitted_by === currentUser` unless user has
  `approve_own_quotation` or is superuser.
- Notifications: strictly own inbox; mark-read owner-checked.

## Status

- [x] Codename mapping verified from views + signals (2026-08-26)
- [x] LIVE-CONFIRM resolved (2026-08-26): profile payload nested (`data.profile`),
      `role` is integer id, `GET /roles/` is Admin-only (`view_role` absent from
      Manager/Employee seeds), roles response nested as `{message, roles:[...]}`
      (`accounts/views.py:402-421`).
