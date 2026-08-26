// Placeholder until Phase 16 builds the real dashboard (plan §0 decision:
// dashboard is deferred so no fake numbers are shown).

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/hooks/useAuth";
import ChangePasswordPage from "@/features/auth/pages/ChangePasswordPage";

export default function DashboardPage() {
  const { user, logout } = useAuth();
  // profile.role is null for freshly-registered users (no role assigned yet).
  const hasNoRole = user != null && user.role == null;

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <Button variant="outline" onClick={logout}>
          Log out
        </Button>
      </div>

      {hasNoRole ? (
        <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
          Your account has no role yet, so most modules are unavailable. Ask an
          administrator to assign you one under Admin · Roles (they will need
          your user ID: <span className="font-mono">{user?.user_id}</span>).
        </p>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Welcome{user?.username ? `, ${user.username}` : ""}</CardTitle>
          <CardDescription>
            Signed in as {user?.email ?? "unknown"} — module screens are built in
            Phases 6–15.
          </CardDescription>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Change password</CardTitle>
          <CardDescription>Update your account password.</CardDescription>
        </CardHeader>
        <CardContent>
          <ChangePasswordPage />
        </CardContent>
      </Card>
    </div>
  );
}
