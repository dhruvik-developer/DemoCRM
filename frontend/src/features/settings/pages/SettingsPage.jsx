import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission, ROLES } from "@/utils/permissions";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "next-themes";
import { Sun, Moon, Monitor, Shield, Users, User, Settings } from "lucide-react";
import ChangePasswordPage from "@/features/auth/pages/ChangePasswordPage";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { registerSchema } from "@/schemas/auth.schema";
import apiClient from "@/api/axios";
import { endpoints } from "@/api/endpoints";
import { toast } from "sonner";
import { getApiErrorMessage } from "@/utils/errors";

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const options = [
    { value: "light", icon: Sun, label: "Light" },
    { value: "dark", icon: Moon, label: "Dark" },
    { value: "system", icon: Monitor, label: "System" },
  ];
  return (
    <div className="flex items-center gap-2">
      {options.map((o) => {
        const Icon = o.icon;
        const active = theme === o.value;
        return (
          <Button key={o.value} variant={active ? "default" : "outline"} size="sm" className={active ? "bg-primary text-primary-foreground" : ""} onClick={() => setTheme(o.value)}>
            <Icon className="h-4 w-4 mr-1" /> {o.label}
          </Button>
        );
      })}
    </div>
  );
}

function InviteEmployee() {
  const { resolved } = useAuth();
  const canInvite = hasPermission(resolved, "add_role") || resolved.isAdmin;
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm({ resolver: zodResolver(registerSchema) });
  const onSubmit = async (values) => {
    try {
      await apiClient.post(endpoints.auth.register, values);
      toast.success(`Invite sent to ${values.email} — temp password set, must change on first login.`);
      reset();
    } catch (e) {
      toast.error(getApiErrorMessage(e));
    }
  };
  if (!canInvite) return <p className="text-sm text-muted-foreground">Only Admin can invite employees. Manager can view team in User Management.</p>;
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-3">
      <div className="grid gap-2"><Label htmlFor="invite_username">Username</Label><Input id="invite_username" {...register("username")} />{errors.username && <p className="text-xs text-destructive">{errors.username.message}</p>}</div>
      <div className="grid gap-2"><Label htmlFor="invite_email">Email</Label><Input id="invite_email" type="email" {...register("email")} />{errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}</div>
      <div className="grid gap-2"><Label htmlFor="invite_phone">Phone (10 digits)</Label><Input id="invite_phone" {...register("phone_number")} />{errors.phone_number && <p className="text-xs text-destructive">{errors.phone_number.message}</p>}</div>
      <div className="grid gap-2"><Label htmlFor="invite_pass">Temp password</Label><Input id="invite_pass" type="password" {...register("password")} />{errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}</div>
      <Button type="submit" disabled={isSubmitting} className="self-start bg-secondary hover:bg-[#E0532A]">{isSubmitting ? "Inviting…" : "Invite employee"}</Button>
      <p className="text-xs text-muted-foreground">Employee will log in with email + temp password and be forced to change password once before seeing dashboard.</p>
    </form>
  );
}

function ProfileCard({ user }) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ username: user?.username || "", phone_number: user?.phone_number || "" });
  const initials = (user?.username || user?.email || "?").slice(0, 2).toUpperCase();
  const roleName = user?.role_name || user?.role?.rolename || "No role";
  const roleColor = roleName === ROLES.ADMIN ? "bg-purple-100 text-purple-800" : roleName === ROLES.MANAGER ? "bg-blue-100 text-blue-800" : "bg-green-100 text-green-800";
  const canEdit = true; // self can edit username/phone; Admin can edit all via same endpoint
  const onSave = async () => {
    setSaving(true);
    try {
      await apiClient.patch(endpoints.auth.profile(user.user_id), { username: form.username, phone_number: form.phone_number });
      toast.success("Profile updated — refresh to see changes.");
      setEditing(false);
    } catch (e) { toast.error(getApiErrorMessage(e)); } finally { setSaving(false); }
  };
  return (
    <Card className="rounded-xl overflow-hidden">
      <CardHeader className="flex flex-row items-start gap-4">
        <div className="h-14 w-14 rounded-full bg-primary text-primary-foreground grid place-items-center text-lg font-bold shrink-0">{initials}</div>
        <div className="flex-1 min-w-0">
          <CardTitle className="text-base flex items-center gap-2">{user?.username || "—"} <Badge className={roleColor}>{roleName}</Badge> {user?.is_active === false ? <Badge variant="destructive">Inactive</Badge> : <Badge variant="secondary">Active</Badge>}</CardTitle>
          <CardDescription className="truncate">{user?.email} · ID {user?.user_id?.slice(0, 8)}</CardDescription>
          <p className="text-xs text-muted-foreground mt-1">Joined {user?.created_at ? new Date(user.created_at).toLocaleDateString() : "—"} · {user?.must_change_password ? "Must change password" : "Verified"}</p>
        </div>
        {canEdit && !editing ? <Button variant="outline" size="sm" onClick={() => setEditing(true)}>Edit</Button> : null}
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {!editing ? (
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-muted-foreground">Email</span><p className="font-medium truncate">{user?.email}</p></div>
            <div><span className="text-muted-foreground">Phone</span><p className="font-medium">{user?.phone_number || "—"}</p></div>
            <div><span className="text-muted-foreground">Username</span><p className="font-medium">{user?.username || "—"}</p></div>
            <div><span className="text-muted-foreground">Role ID</span><p className="font-mono text-xs">{String(user?.role ?? "—")}</p></div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="grid gap-2"><Label>Username</Label><Input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></div>
            <div className="grid gap-2"><Label>Phone</Label><Input value={form.phone_number} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} /></div>
            <div className="flex gap-2"><Button onClick={onSave} disabled={saving}>{saving ? "Saving…" : "Save"}</Button><Button variant="outline" onClick={() => setEditing(false)}>Cancel</Button></div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  const { user, resolved } = useAuth();
  const mustChange = user?.must_change_password;
  const roleName = user?.role_name || user?.role?.rolename;
  const isAdmin = resolved?.isAdmin || roleName === ROLES.ADMIN;
  const isManager = roleName === ROLES.MANAGER;
  const isEmployee = roleName === ROLES.EMPLOYEE;
  const canManageTeam = isAdmin;
  const canViewTeam = isAdmin || isManager;

  const defaultTab = mustChange ? "security" : "account";

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2"><Settings className="h-6 w-6" /> Settings</h1>
            <p className="text-sm text-muted-foreground">Manage account, security, and team. <Badge variant="outline" className="ml-2">{roleName || "No role"}</Badge> {isAdmin ? <Badge>Admin — full access</Badge> : isManager ? <Badge variant="secondary">Manager — team view</Badge> : <Badge variant="secondary">Employee — self only</Badge>}</p>
          </div>
          <ThemeToggle />
        </div>
        {mustChange ? <p className="mt-2 rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800">You must change your temporary password before accessing other pages.</p> : null}
      </div>
      <Tabs defaultValue={defaultTab}>
        <TabsList className="flex flex-wrap">
          <TabsTrigger value="account"><User className="h-4 w-4 mr-1" />Account</TabsTrigger>
          <TabsTrigger value="security"><Shield className="h-4 w-4 mr-1" />Security</TabsTrigger>
          {canViewTeam ? <TabsTrigger value="team"><Users className="h-4 w-4 mr-1" />Team</TabsTrigger> : null}
        </TabsList>
        <TabsContent value="account">
          <ProfileCard user={user} />
          <Card className="rounded-xl mt-4"><CardHeader><CardTitle className="text-sm">Preferences</CardTitle><CardDescription>Soft — local only, no harsh change.</CardDescription></CardHeader><CardContent className="flex flex-wrap items-center gap-4 text-sm">
            <label className="flex items-center gap-2"><input type="checkbox" defaultChecked className="h-4 w-4" onChange={() => toast("Email notifications — coming soon")} /> Email notifications</label>
            <span className="text-muted-foreground">Language: English (default)</span>
          </CardContent></Card>
          {!isAdmin ? <p className="mt-3 text-xs text-muted-foreground">Employee/Manager: you can edit your own username/phone above. Role changes require Admin.</p> : null}
        </TabsContent>
        <TabsContent value="security">
          <Card className="rounded-xl"><CardHeader><CardTitle className="text-sm">Change password</CardTitle><CardDescription>Update your account password. After first-login change, you will see the dashboard.</CardDescription></CardHeader><CardContent><ChangePasswordPage /></CardContent></Card>
          {isEmployee ? <p className="mt-3 text-xs text-muted-foreground">Employee: password is the only security setting available to you.</p> : null}
        </TabsContent>
        {canViewTeam ? (
          <TabsContent value="team">
            <Card className="rounded-xl"><CardHeader><CardTitle className="text-sm">{canManageTeam ? "Invite employee" : "Team — view only"}</CardTitle><CardDescription>{canManageTeam ? "Admin creates account with temp password — employee logs in and is forced to change once." : "Manager can view team members. Invites are Admin-only (hasPermission add_role)."}</CardDescription></CardHeader><CardContent><InviteEmployee /></CardContent></Card>
            {!canManageTeam ? <p className="mt-3 text-xs text-muted-foreground">Ask Admin to invite via Settings → Team → Invite.</p> : null}
          </TabsContent>
        ) : null}
      </Tabs>
    </div>
  );
}
