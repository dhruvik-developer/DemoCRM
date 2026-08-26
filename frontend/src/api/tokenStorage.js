// Single place for token persistence so the storage strategy can be swapped
// later without touching call sites (implementation plan Phase 2, decision G5).
//
// NOTE (documented XSS caveat): tokens live in localStorage because the
// backend returns them in plain JSON and has no httpOnly-cookie flow.
// See frontend/docs/AUTH_CONTRACT.md.

const ACCESS_TOKEN_KEY = "crm_access_token";
const REFRESH_TOKEN_KEY = "crm_refresh_token";
const USER_ID_KEY = "crm_user_id";

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getUserId() {
  return localStorage.getItem(USER_ID_KEY);
}

export function setTokens({ accessToken, refreshToken, userId }) {
  if (accessToken) {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  }
  if (refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }
  if (userId) {
    localStorage.setItem(USER_ID_KEY, userId);
  }
}

export function setAccessToken(accessToken) {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_ID_KEY);
}
