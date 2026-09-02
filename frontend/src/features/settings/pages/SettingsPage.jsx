import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useTheme } from "next-themes";
import { Sun, Moon, Monitor } from "lucide-react";
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
          <Button
            key={o.value}
            variant={active ? "default" : "outline"}
            size="sm"
            className={active ? "bg-primary text-primary-foreground" : ""}
            onClick={() => setTheme(o.value)}
          >
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
  if (!canInvite) return <p className="text-sm text-muted-foreground">Only Admin can invite employees.</p>;
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-3">
      <div className="grid gap-2">
        <Label htmlFor="invite_username">Username</Label>
        <Input id="invite_username" {...register("username")} />
        {errors.username && <p className="text-xs text-destructive">{errors.username.message}</p>}
      </div>
      <div className="grid gap-2">
        <Label htmlFor="invite_email">Email</Label>
        <Input id="invite_email" type="email" {...register("email")} />
        {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
      </div>
      <div className="grid gap-2">
        <Label htmlFor="invite_phone">Phone (10 digits)</Label>
        <Input id="invite_phone" {...register("phone_number")} />
        {errors.phone_number && <p className="text-xs text-destructive">{errors.phone_number.message}</p>}
      </div>
      <div className="grid gap-2">
        <Label htmlFor="invite_pass">Temp password</Label>
        <Input id="invite_pass" type="password" {...register("password")} />
        {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
      </div>
      <Button type="submit" disabled={isSubmitting} className="self-start bg-[#2563EB] hover:bg-[#1D4ED8]">{isSubmitting ? "Inviting…" : "Invite employee"}</Button>
      <p className="text-xs text-muted-foreground">Employee will log in with this email + temp password and be forced to change password once (GitLab-style) before seeing dashboard.</p>
    </form>
  );
}

export default function SettingsPage() {
  const { user } = useAuth();
  const mustChange = user?.must_change_password;
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
            <p className="text-sm text-muted-foreground">Manage account, security, and team.</p>
          </div>
          <ThemeToggle />
        </div>
        {mustChange ? <p className="mt-2 rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800">You must change your temporary password before accessing other pages — like GitLab.</p> : null}
      </div>
      <Tabs defaultValue={mustChange ? "security" : "account"}>
        <TabsList>
          <TabsTrigger value="account">Account</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
          <TabsTrigger value="team">Team</TabsTrigger>
        </TabsList>
        <TabsContent value="account">
          <Card className="rounded-xl"><CardHeader><CardTitle className="text-sm">Profile</CardTitle><CardDescription>{user?.email} · {user?.role_name ?? "No role"} · {user?.user_id?.slice(0,8)}</CardDescription></CardHeader><CardContent><p className="text-sm text-muted-foreground">Profile details from <code>GET /profile/&lt;id&gt;/</code>. Role shown from `role_name`.</p></CardContent></Card>
        </TabsContent>
        <TabsContent value="security">
          <Card className="rounded-xl"><CardHeader><CardTitle className="text-sm">Change password</CardTitle><CardDescription>Update your account password. After first-login change, you will see the dashboard.</CardDescription></CardHeader><CardContent><ChangePasswordPage /></CardContent></Card>
        </TabsContent>
        <TabsContent value="team">
          <Card className="rounded-xl"><CardHeader><CardTitle className="text-sm">Invite employee</CardTitle><CardDescription>Admin creates account with temp password — employee logs in with email + temp password, forced to change once.</CardDescription></CardHeader><CardContent><InviteEmployee /></CardContent></Card>
          <p className="mt-4 text-xs text-muted-foreground"><a href="/stitch-preview" className="text-[#2563EB] hover:underline">Open Stitch Design Preview</a> — pixel-exact snapshot of the target workspace look.</p>
        </TabsContent>
      </Tabs>
    </div>
  );
}
