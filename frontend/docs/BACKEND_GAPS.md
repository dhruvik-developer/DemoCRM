# BACKEND_GAPS

> Ticket tracker for known backend gaps affecting the frontend. Every entry
> has a status: `workaround in place` / `waiting on backend` / `resolved`.
> Full details in `CRM_ANALYSIS_REPORT.md` §20. Update this file in the same
> commit that changes any workaround.

---

## G6 — No `GET /users/` list endpoint

- **Status:** workaround in place (manual UUID entry)
- **Blocks:** Phase 15 Admin role-assignment UI (user search)
- **Location:** `backend/crm/accounts/urls.py` — only `/profile/<uuid:user_id>/` exists
- **Workaround:** Assign Role screen falls back to manual UUID entry until the
  backend ships a permission-guarded user-list endpoint.

## G7 — No master-data REST endpoints for Task/Meeting enums

- **Status:** workaround in place (hardcoded dropdowns)
- **Blocks:** Task/Meeting/Reminder form dropdowns (TaskStatus, Priority,
  Category, MeetingStatus, MeetingType, ReminderType, ReminderStatus)
- **Location:** models exist in `Task/models.py`; no routes in `Task/urls.py`
- **Workaround:** hardcode options client-side; re-check this file before
  building Phases 9–11 in case endpoints landed.

## G8 — No `GET /tasks/meetings/` or `GET /tasks/reminders/` list endpoints

- **Status:** waiting on backend (interim UX: open-by-ID + create)
- **Blocks:** Meetings list page, Reminders list page (Phases 10–11)
- **Location:** `Task/urls.py:36-95` — meetings have POST + `<id>` detail +
  actions only; reminders have POST + detail + status only
- **CORRECTION (2026-08-26):** the plan's fallback ("derive client-side from
  the Task relation") is NOT feasible either — `TaskSerializer` uses
  `fields="__all__"` and exposes NO nested meeting/reminder collections, and
  there is no other route that returns them. A meetings/reminders LIST is
  impossible until the backend ships one.
- **Interim UX shipped instead:** `/meetings` shows a create CTA plus an
  open-by-ID lookup; creation navigates straight to the new meeting's detail
  page. Swap to real queries when endpoints land.

## G9 — Duplicate URL entries in `Task/urls.py`

- **Status:** waiting on backend (cosmetic, not blocking)
- **Detail:** `meetings/<int:meeting_id>/` and `.../approval/` registered twice
  (lines 51–60). Harmless — last entry wins.

## G10 — OTP configuration drift

- **Status:** resolved (2026-08-26, verified from code + live backend)
- **Detail:** `accounts/views.py:52-54` reads OTP values from env with
  fallbacks (6/5/3); `.env` overrides with 6/10/5 — effective live values are
  **6-digit / 10-minute / 5-attempts**. Recorded in AUTH_CONTRACT.md; UI
  countdown must use 10 min / 5 attempts.

## G11 — Inconsistent API error formats

- **Status:** workaround in place (normalizeApiError)
- **Detail:** four+ shapes observed — `{"detail"}`, DRF field dicts
  `{"field": ["msg"]}`, `{"error"}`, CallForms validation dicts.
- **Workaround:** all responses normalized client-side via
  `src/utils/errors.js` → `{ message, fieldErrors, status }`.

## G12 — FollowUp description field named `decription` (typo)

- **Status:** workaround in place (frontend sends the typo'd key)
- **Rule:** send `decription` in payloads; label it "Description" in the UI.

## G13 — FollowUp POST requires `change_followup`, not `add_followup`

- **Status:** documented (no code impact if gated correctly)
- **Rule:** gate the FollowUp Create button on `change_followup`.

## G14 — Double `/api/` prefix risk

- **Status:** resolved by convention (this file documents it)
- **Detail:** `VITE_API_BASE_URL` already includes `/api`; every entry in
  `src/api/endpoints.js` must be a suffix (`/login/`), never `/api/login/`.

## G23 — Role seeds omit all `customer_management` models + roles/permissions

- **Status:** waiting on backend (frontend gates on hydrated permissions and
  handles 403 gracefully in the meantime)
- **Discovered:** 2026-08-26 during Phase 0.2 (signals.py read)
- **Detail:** `MANAGER_MODEL_PREFIXES` and `EMPLOYEE_MODEL_PREFIXES`
  (`accounts/signals.py:33-111`) contain no entries for `lead`, `leadsource`,
  `pipeline`, `pipelinestage`, `quotation*`, `activity` — nor `role`,
  `permission`, `auditlog`. Under default seeds only Admin can use the Leads /
  Quotations / Activities / Audit modules, and only Admin can call
  `GET /roles/`.
- **Knock-on effect:** Employees have `add_followup` but FollowUp create
  requires `change_followup` (G13) → Employees cannot create follow-ups.
- **Suggested backend fix:** add the customer_management prefixes to
  MANAGER/EMPLOYEE seed lists (or grant per-role explicitly), then re-run
  migrate to reseed.

---

## Resolved blockers (kept for history)

### G1 — CORS missing ✅ resolved 2026-08-26

- Added `django-cors-headers` to `requirements.txt`, `INSTALLED_APPS`,
  `MIDDLEWARE`, and `CORS_ALLOWED_ORIGINS` (env-driven) in `crm/settings.py`.
- `.env` / `.env.example`: `ALLOWED_HOSTS` expanded to include `localhost`.
- **Action required:** run `pip install -r requirements.txt` before starting
  the backend, or Django will fail on the new app import.

### G2 — Placeholder endpoint map ✅ resolved 2026-08-26

- `frontend/src/api/endpoints.js` rewritten from real `urls.py` routes;
  cross-check vs live `/schema/` still pending backend restart.

### G3 — Axios had no auth wiring ✅ resolved 2026-08-26

- `src/api/tokenStorage.js` added (isolated localStorage access).
- `src/api/axios.js` now injects `Authorization: Bearer`, performs single
  in-flight refresh + retry on 401, and normalizes errors via
  `src/utils/errors.js`.

### G4 — No current-user endpoint ✅ resolved by decision

- Decode JWT `user_id` claim → `GET /profile/<uuid:user_id>/`. Documented in
  AUTH_CONTRACT.md; no backend change needed.
