// Central auth state per implementation plan Phase 3:
// isAuthenticated / currentUser / permissions / loading + login/logout.
//
// Current-user resolution (no /auth/me/ exists — G4):
//   access token → decode JWT user_id → GET /profile/<user_id>/ → data.profile
//
// Permission hydration follows PERMISSION_CONTRACT.md: the profile carries
// only a numeric role id. GET /roles/ is Admin-only; when it succeeds we map
// role_id → rolename, otherwise we fall back to the seed maps keyed by an
// unknown role ("staff" union). See utils/permissions.js.

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  getUserId,
  setTokens,
} from "@/api/tokenStorage";
import { endpoints } from "@/api/endpoints";
import apiClient from "@/api/axios";
import { fetchProfile, loginRequest, logoutRequest } from "@/features/auth/api";
import { getUserIdFromToken, isTokenExpired } from "@/utils/jwt";
import { resolvePermissions } from "@/utils/permissions";

// Context files export both the provider and the hook by design.
/* eslint-disable react-refresh/only-export-components */
const AuthContext = createContext(null);

// Roles response shape (verified): { message, roles: [{role_id, rolename, ...}] }.
// Returns null when the caller lacks view_role (any non-Admin).
async function tryResolveRoleName(roleId) {
  if (roleId == null) return null;
  try {
    const { data } = await apiClient.get(endpoints.auth.roles);
    const role = (data.roles ?? []).find((r) => r.role_id === roleId);
    return role?.rolename ?? null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState({
    status: "initializing", // initializing | authenticated | unauthenticated
    user: null,
    resolved: null, // { isAdmin, codenames } from resolvePermissions
  });

  const applySession = useCallback(async () => {
    const accessToken = getAccessToken();
    if (!accessToken || isTokenExpired(accessToken)) {
      clearTokens();
      setState({ status: "unauthenticated", user: null, resolved: null });
      return;
    }

    const userId = getUserId() ?? getUserIdFromToken(accessToken);
    if (!userId) {
      clearTokens();
      setState({ status: "unauthenticated", user: null, resolved: null });
      return;
    }

    try {
      const profile = await fetchProfile(userId);
      const roleName = await tryResolveRoleName(profile.role);
      setState({
        status: "authenticated",
        user: profile,
        resolved: resolvePermissions({ roleName }),
      });
    } catch {
      // Profile fetch failed (expired refresh / network) — force re-login.
      clearTokens();
      setState({ status: "unauthenticated", user: null, resolved: null });
    }
  }, []);

  useEffect(() => {
    // Scheduled as a microtask so no setState runs synchronously inside the
    // effect body (react-hooks/set-state-in-effect). Cancelled flag guards
    // against StrictMode double-mount races.
    let cancelled = false;
    queueMicrotask(async () => {
      const accessToken = getAccessToken();
      if (!accessToken || isTokenExpired(accessToken)) {
        clearTokens();
        if (!cancelled) {
          setState({ status: "unauthenticated", user: null, resolved: null });
        }
        return;
      }

      const userId = getUserId() ?? getUserIdFromToken(accessToken);
      if (!userId) {
        clearTokens();
        if (!cancelled) {
          setState({ status: "unauthenticated", user: null, resolved: null });
        }
        return;
      }

      try {
        const profile = await fetchProfile(userId);
        if (cancelled) return;
        const roleName = await tryResolveRoleName(profile.role);
        if (cancelled) return;
        setState({
          status: "authenticated",
          user: profile,
          resolved: resolvePermissions({ roleName }),
        });
      } catch {
        // Profile fetch failed (expired refresh / network) — force re-login.
        clearTokens();
        if (!cancelled) {
          setState({ status: "unauthenticated", user: null, resolved: null });
        }
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(
    async (values) => {
      const tokens = await loginRequest(values); // throws normalized errors on 400/401
      setTokens({
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
      });
      await applySession();
    },
    [applySession],
  );

  const logout = useCallback(async () => {
    try {
      await logoutRequest(getRefreshToken());
    } catch {
      // Backend already-invalidated/absent token is fine — local cleanup continues.
    }
    clearTokens();
    queryClient.clear();
    setState({ status: "unauthenticated", user: null, resolved: null });
  }, [queryClient]);

  const value = useMemo(
    () => ({
      ...state,
      isLoading: state.status === "initializing",
      isAuthenticated: state.status === "authenticated",
      login,
      logout,
    }),
    [state, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}
