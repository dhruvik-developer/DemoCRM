# AUTH_CONTRACT

> Facts verified from code AND against the LIVE running backend on 2026-08-26
> (`GET /schema/` + probe requests). No remaining LIVE-CONFIRM items.

## Login

```
POST /login/            (suffix; full URL = VITE_API_BASE_URL + /login/)
AllowAny

Request:  { "email": string, "password": string }
200:      { "message": string, "access_token": string, "refresh_token": string }
401:      { "error": string }            ← NOT {"detail"} — verified via live schema
400:      DRF field errors, e.g. {"email": ["This field is required."], ...}
          (400 shape verified by live probe request)
```

Login response contains **no user object and no permissions** — only tokens.
(Live schema: `LoginRequest`, `LoginSuccessResponse`, `LoginUnauthorizedResponse`.)

## Tokens (SIMPLE_JWT — `crm/settings.py:210-217`)

| Setting | Value |
|---|---|
| Access token lifetime | 15 minutes |
| Refresh token lifetime | 7 days |
| `USER_ID_FIELD` / claim | `user_id` (UUID — not `id`) |
| Rotation | OFF (`ROTATE_REFRESH_TOKENS = False`) |
| Blacklist after rotation | True (and logout blacklists explicitly) |

Storage decision (locked in implementation plan §0): **localStorage**, XSS
caveat documented (G5). Access isolated in `src/api/tokenStorage.js` so the
strategy can be swapped later without touching call sites.

## Refresh

```
POST /refresh/
AllowAny
Request:  { "refresh_token": string }
200:      { "message": string, "access_token": string }   ← verified via live schema
400:      { "error": string } — invalid/expired/blacklisted refresh token
```

Client behavior on 401: attempt one refresh with a single shared in-flight
promise (race guard), retry the original request once; on refresh failure clear
tokens and redirect to `/login`.

## Logout

```
POST /logout/
JWT + "logout" permission
Request:  { "refresh_token": string }
200:      { "message": string }   (also returns 200 if already logged out)
400:      missing/invalid token
```

Client must also clear localStorage tokens + TanStack Query cache regardless
of the response.

## Current user (no `/auth/me/` exists — G4)

Resolution chain:
1. Decode JWT access token payload → `user_id` (UUID).
2. `GET /profile/<user_id>/` → **response is NESTED (verified via live schema
   `ProfileSuccessResponse`)**:

```json
{
  "message": "...",
  "profile": {
    "user_id": "uuid",
    "username": "string",
    "email": "string",
    "phone_number": "string",
    "role": 1,
    "created_at": "...",
    "updated_at": "..."
  }
}
```

⚠️ The user object is under `data.profile`, NOT at the top level — auth
hydration must read `response.data.profile`.

**`role` is the Role FK integer id — it does NOT include permission
codenames** (live schema: `role:integer`). Permission codenames require an
additional call — see PERMISSION_CONTRACT.md.

Profile access rule: self, Admin, or Manager. Employee viewing another user → 403
(`{"error": string}`). Unknown id → 404 (`{"detail": string}`).

## Password flows

### Change password
```
POST /change-password/
JWT
Request:  { "old_password": string, "new_password": string }
200 / 400 (wrong old password, weak password, missing) / 401
```
`validate_password` IS enforced here (min length, not common, not all numeric).

### Forgot password
```
POST /forgot-password/
AllowAny
Request:  { "email": string }
200:      OTP sent by email
404:      no active user with that email
```

### Reset password
```
POST /reset-password/
AllowAny
Request:  { "email": string, "otp": string(6), "new_password": string }
200 / 400 (invalid, expired, too many attempts — lockout) / 404
```
OTP mechanics (from views): sha256-hashed, single-use, old unused OTPs
invalidated when a new one is issued, constant-time compare, lockout after max
attempts.

## OTP configuration — RESOLVED (was G10)

`accounts/views.py:52-54` reads OTP config from environment with fallbacks:

```py
OTP_LENGTH = int(os.getenv("OTP_LENGTH", "6"))
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "5"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "3"))
```

`backend/.env` sets `OTP_LENGTH=6, OTP_EXPIRY_MINUTES=10, OTP_MAX_ATTEMPTS=5`,
and env overrides fallbacks — so the **effective live values are:

| Value | Effective | Source |
|---|---|---|
| Length | **6 digits** | `.env` + fallback agree |
| Expiry | **10 minutes** | `.env` (fallback would be 5) |
| Max attempts | **5 attempts** | `.env` (fallback would be 3) |

The reset-password UI countdown must show **10 minutes** and attempts
messaging based on **5**, not the code fallbacks.

## Register

```
POST /register/
AllowAny
Request:  { "username", "email", "phone_number", "password" }
201:      { "user_id", "username", "email", "message" }   ← verified via live schema
400:      duplicate email / duplicate phone_number / blank fields
```

Note: register does NOT run `validate_password` (weak passwords accepted —
verified in accounts tests). Frontend zod schema may warn but must not block
on rules the backend doesn't enforce.
