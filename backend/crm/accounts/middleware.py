"""
Middleware to enforce mandatory password change on first login.

If a user has must_change_password=True, all API requests except the
allow-listed ones are blocked with 403 + code must_change_password.
This ensures the frontend cannot bypass the forced change screen and
that backend data isn'"'"'t accessible with the initial temporary password.

Note: At Django middleware time, request.user is still AnonymousUser for
JWT-authenticated requests (DRF authenticates later). So we also inspect
the Authorization header and validate the JWT to find the user even before
DRF authentication.
"""

from django.http import JsonResponse
from django.contrib.auth import get_user_model

ALLOWED_PREFIXES_WHEN_MUST_CHANGE = (
    "/api/change-password/",
    "/api/logout/",
    "/api/refresh/",
    "/api/profile/",
    "/api/login/",
    "/admin/",
    "/schema/",
    "/docs/",
    "/redoc/",
)

ALLOWED_EXACT_PATHS = (
    "/api/change-password/",
    "/api/logout/",
    "/api/refresh/",
)


def _is_allowed_path(path: str) -> bool:
    for prefix in ALLOWED_PREFIXES_WHEN_MUST_CHANGE:
        if path.startswith(prefix):
            return True
    if path in ALLOWED_EXACT_PATHS:
        return True
    return False


def _get_user_from_authorization_header(request):
    """Try to extract and validate JWT from Authorization header and fetch user."""
    auth = request.headers.get("Authorization") if hasattr(request, "headers") else None
    if not auth:
        auth = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth or not auth.startswith("Bearer "):
        return None
    token_str = auth.split(" ", 1)[1].strip()
    if not token_str:
        return None
    try:
        # Validate token signature & expiry via SimpleJWT
        from rest_framework_simplejwt.tokens import UntypedToken, AccessToken

        # UntypedToken validates any token type (access/refresh) signature
        UntypedToken(token_str)
        # Now try to get user_id claim
        try:
            token = AccessToken(token_str)
            user_id = token.get("user_id")
        except Exception:
            token = UntypedToken(token_str)
            user_id = (
                token.payload.get("user_id")
                if hasattr(token, "payload")
                else token.get("user_id")
            )
        if not user_id:
            return None
        User = get_user_model()
        try:
            # user_id is UUID stored as string
            user = User.objects.get(user_id=user_id)
            return user
        except Exception:
            return None
    except Exception:
        return None


class MustChangePasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            return self.get_response(request)

        user = getattr(request, "user", None)
        is_authed = bool(user and getattr(user, "is_authenticated", False))
        target_user = user if is_authed else None

        # If not authenticated at middleware time, try to resolve via JWT header
        if not is_authed:
            target_user = _get_user_from_authorization_header(request)
            if not target_user:
                return self.get_response(request)

        # Superusers are exempt
        if getattr(target_user, "is_superuser", False):
            return self.get_response(request)

        must_change = getattr(target_user, "must_change_password", False)
        if not must_change:
            return self.get_response(request)

        path = request.path
        if path.startswith("/api/") and not _is_allowed_path(path):
            return JsonResponse(
                {
                    "error": "Password change required. Please change your password before continuing.",
                    "code": "must_change_password",
                    "must_change_password": True,
                },
                status=403,
            )

        return self.get_response(request)
