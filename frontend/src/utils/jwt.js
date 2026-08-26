// Minimal JWT payload access. The backend puts the user UUID in the "user_id"
// claim (SIMPLE_JWT USER_ID_CLAIM, see frontend/docs/AUTH_CONTRACT.md).

function base64UrlDecode(segment) {
  const normalized = segment.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
  return atob(padded);
}

export function decodeJwtPayload(token) {
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    return JSON.parse(base64UrlDecode(parts[1]));
  } catch {
    return null;
  }
}

/** Returns the user_id (UUID) from an access token, or null. */
export function getUserIdFromToken(token) {
  const payload = decodeJwtPayload(token);
  return payload?.user_id ?? null;
}

/** True when the token's exp has passed (with a small safety margin). */
export function isTokenExpired(token, marginSeconds = 30) {
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) return true;
  return payload.exp * 1000 <= Date.now() + marginSeconds * 1000;
}
