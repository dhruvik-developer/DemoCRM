// Profile page — read-only account info from auth context + change password.
// (Phase 15 "Profile settings" item.)

import { useAuth } from "@/hooks/useAuth";
import ChangePasswordPage from "@/features/auth/pages/ChangePasswordPage";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function Field({ label, value }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="text-sm">{value ?? "—"}</span>
    </div>
  );
}

export default function ProfilePage() {
  const { user } = useAuth();

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
      <h1 className="text-2xl font-semibold tracking-tight">Profile</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Account</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label="Username" value={user?.username} />
          <Field label="Email" value={user?.email} />
          <Field label="Phone number" value={user?.phone_number} />
          <div className="flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wide text-muted-foreground">Role</span>
            {/* Role id only — resolving the name requires Admin (G6/G23). */}
            <Badge variant="outline" className="w-fit">
              role #{user?.role ?? "?"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Change password</CardTitle>
        </CardHeader>
        <CardContent>
          <ChangePasswordPage />
        </CardContent>
      </Card>
    </div>
  );
}
