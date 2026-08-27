// Auth route guards (implementation plan Phase 3).
// Frontend gating is UX only - the backend stays authoritative; any gated
// action must still handle a 403 gracefully.

import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

function FullScreenSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
    </div>
  );
}

/** Allows only authenticated users; remembers the attempted location. */
export function ProtectedRoute() {
  const { isAuthenticated, isLoading, mustChangePassword } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <FullScreenSpinner />;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  // Force password change takes precedence over any other route
  if (mustChangePassword && location.pathname !== "/force-change-password") {
    return <Navigate to="/force-change-password" replace />;
  }
  return <Outlet />;
}

/** Guard for the mandatory password-change screen itself */
export function ForceChangePasswordRoute() {
  const { isAuthenticated, isLoading, mustChangePassword } = useAuth();
  const location = useLocation();

  if (isLoading) return <FullScreenSpinner />;
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  // If password already changed, send to dashboard
  if (!mustChangePassword) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}

/** Allows only Admin and Manager to access child routes (e.g. /register) */
export function AdminManagerRoute() {
  const { isAuthenticated, isLoading, mustChangePassword, user, resolved } = useAuth();
  const location = useLocation();

  if (isLoading) return <FullScreenSpinner />;
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  if (mustChangePassword && location.pathname !== "/force-change-password") {
    return <Navigate to="/force-change-password" replace />;
  }
  const roleName = user?.role_name ?? user?.role?.rolename;
  let isAdminOrManager = false;
  if (resolved?.isAdmin) isAdminOrManager = true;
  else if (roleName === "Admin" || roleName === "Manager") isAdminOrManager = true;
  else {
    const rawRole = user?.role;
    if (typeof rawRole === "number") {
      // Numeric role cannot be resolved without API; optimistically allow and let backend 403 surface
      isAdminOrManager = true;
    }
  }

  if (!isAdminOrManager) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="max-w-md text-center">
          <h2 className="text-lg font-semibold">Access denied</h2>
          <p className="mt-2 text-sm text-muted-foreground">Only Admin and Manager can register new employees.</p>
        </div>
      </div>
    );
  }
  return <Outlet />;
}

/** Allows only unauthenticated users (login/forgot/reset). Authenticated users go to dashboard, unless they must change password. */
export function PublicOnlyRoute() {
  const { isAuthenticated, isLoading, mustChangePassword } = useAuth();

  if (isLoading) {
    return <FullScreenSpinner />;
  }
  if (isAuthenticated) {
    if (mustChangePassword) {
      return <Navigate to="/force-change-password" replace />;
    }
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}
