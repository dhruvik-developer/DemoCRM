import axios from "axios";
import { getAccessToken, getRefreshToken, clearTokens, setAccessToken } from "./tokenStorage";
import { normalizeApiError } from "../utils/errors";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Bare instance for the refresh call so its own 401/400 can't re-trigger the
// response interceptor below (no recursion).
const refreshClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Single in-flight refresh promise shared across concurrent 401s, so a burst
// of expired-token requests triggers exactly one refresh call.
let refreshPromise = null;

function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = refreshClient
      .post("/refresh/", { refresh_token: getRefreshToken() })
      .then((response) => {
        const accessToken = response.data.access_token;
        setAccessToken(accessToken);
        return accessToken;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;
    const isRefreshCall = originalRequest?.url === "/refresh/";

    // Refresh failed → session is over; caller (or auth context) handles redirect.
    if (isRefreshCall || !getRefreshToken()) {
      if (status === 401 || status === 400) {
        clearTokens();
      }
      error.normalized = normalizeApiError(error);
      return Promise.reject(error);
    }

    // Expired access token → refresh once and retry the original request once.
    if (status === 401 && !originalRequest._retried) {
      originalRequest._retried = true;
      try {
        const accessToken = await refreshAccessToken();
        originalRequest.headers.Authorization = `Bearer ${accessToken}`;
        return apiClient(originalRequest);
      } catch {
        clearTokens();
        error.normalized = normalizeApiError(error);
        return Promise.reject(error);
      }
    }

    error.normalized = normalizeApiError(error);
    return Promise.reject(error);
  }
);

export default apiClient;
