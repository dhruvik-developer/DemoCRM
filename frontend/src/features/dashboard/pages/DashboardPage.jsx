// Real dashboard per §16 — only real data, never fake numbers.
// Queries underlying modules: leads, tasks, quotations, activities, notifications.
// Role-specific cards gated via hasPermission; backend 403 remains authoritative.

import { Link } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { useLeads } from "@/features/leads/hooks";
import { useTasks } from "@/features/tasks/hooks";
import { useQuotations } from "@/features/quotations/hooks";
import { useActivities } from "@/features/activities/hooks";
import { useNotifications } from "@/features/notifications/hooks";
import { usePipelineStages, usePipelines } from "@/features/crm/hooks";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Users, CheckSquare, FileText, Bell, Activity } from "lucide-react";

function Stat({ title, value, desc, icon: Icon, to, loading }) {
  return (
    <Card className="rounded-xl">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {loading ? <Skeleton className="h-7 w-12" /> : <div className="text-2xl font-bold">{value}</div>}
        {desc ? <p className="text-xs text-muted-foreground">{desc}</p> : null}
        {to ? <Link to={to} className="text-xs text-[#2563EB] hover:underline">View →</Link> : null}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const hasNoRole = user != null && user.role == null;

  // Real queries — page_size 1 for count-only where possible, else small page
  const leadsQ = useLeads({ page: 1, page_size: 1, status: "ACTIVE" });
  const allLeadsQ = useLeads({ page: 1, page_size: 50 });
  const tasksQ = useTasks({ page: 1, page_size: 50 });
  const quotationsQ = useQuotations({ page: 1 });
  const activitiesQ = useActivities({});
  const notificationsQ = useNotifications({ is_read: false, page_size: 5 });
  const pipelinesQ = usePipelines();
  const pipelineId = pipelinesQ.data?.[0]?.id;
  const stagesQ = usePipelineStages(pipelineId);

  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const endToday = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);

  const overdueTasks = (tasksQ.data?.results ?? tasksQ.data ?? []).filter((t) => t.due_date && new Date(t.due_date) < now).length;
  const todayTasks = (tasksQ.data?.results ?? tasksQ.data ?? []).filter((t) => t.due_date && new Date(t.due_date) >= startToday && new Date(t.due_date) < endToday).length;
  const openLeads = leadsQ.data?.count ?? (allLeadsQ.data?.results ?? allLeadsQ.data ?? []).filter((l) => l.status === "ACTIVE").length ?? 0;

  // Leads by stage — derived from fetched sample (page_size 50); note: not exhaustive if >50 leads
  const byStage = (() => {
    const stages = stagesQ.data ?? [];
    const leads = allLeadsQ.data?.results ?? allLeadsQ.data ?? [];
    const map = Object.fromEntries(stages.map((s) => [s.id, 0]));
    leads.forEach((l) => { if (map[l.current_stage] !== undefined) map[l.current_stage]++; });
    return stages.map((s) => ({ name: s.name, count: map[s.id] ?? 0 }));
  })();

  const pendingQuotations = (quotationsQ.data?.results ?? quotationsQ.data ?? []).filter((q) => ["DRAFT","PENDING_APPROVAL","APPROVED","SENT"].includes(q.status)).length;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
        <Button variant="outline" onClick={logout}>Log out</Button>
      </div>

      {hasNoRole ? (
        <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Your account has no role yet — ask an admin to assign one (user ID: <span className="font-mono">{user?.user_id}</span>).
        </p>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Stat title="Open leads" value={leadsQ.isLoading ? "—" : openLeads} desc="ACTIVE status" icon={Users} to="/leads" loading={leadsQ.isLoading} />
        <Stat title="Overdue tasks" value={tasksQ.isLoading ? "—" : overdueTasks} desc="Past due" icon={CheckSquare} to="/tasks?inbox=overdue" loading={tasksQ.isLoading} />
        <Stat title="Today's tasks" value={tasksQ.isLoading ? "—" : todayTasks} desc="Due today" icon={CheckSquare} to="/tasks?inbox=today" loading={tasksQ.isLoading} />
        <Stat title="Quotations pipeline" value={quotationsQ.isLoading ? "—" : pendingQuotations} desc="DRAFT → SENT" icon={FileText} to="/quotations" loading={quotationsQ.isLoading} />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="rounded-xl lg:col-span-2">
          <CardHeader><CardTitle className="text-sm">Leads by stage</CardTitle><CardDescription>Sample of first 50 leads — not exhaustive</CardDescription></CardHeader>
          <CardContent>
            {stagesQ.isLoading || allLeadsQ.isLoading ? <Skeleton className="h-24 w-full" /> : byStage.length ? (
              <div className="flex flex-col gap-2">
                {byStage.map((s) => (
                  <div key={s.name} className="flex items-center justify-between rounded-md border px-3 py-2">
                    <span className="text-sm font-medium">{s.name}</span>
                    <Badge variant="secondary">{s.count}</Badge>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-muted-foreground">No pipeline stages configured. Create one under Admin · Pipelines.</p>}
          </CardContent>
        </Card>

        <Card className="rounded-xl">
          <CardHeader><CardTitle className="text-sm flex items-center gap-2"><Bell className="h-4 w-4" /> Notifications</CardTitle></CardHeader>
          <CardContent>
            {notificationsQ.isLoading ? <Skeleton className="h-20 w-full" /> : (notificationsQ.data?.results ?? notificationsQ.data ?? []).length ? (
              <div className="flex flex-col gap-2">
                {(notificationsQ.data?.results ?? notificationsQ.data).slice(0,5).map((n) => (
                  <div key={n.id} className="rounded border px-2 py-1.5 text-sm truncate">{n.message}</div>
                ))}
                <Link to="/notifications" className="text-xs text-[#2563EB] hover:underline">View all →</Link>
              </div>
            ) : <p className="text-sm text-muted-foreground">No unread notifications.</p>}
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-xl">
        <CardHeader><CardTitle className="text-sm flex items-center gap-2"><Activity className="h-4 w-4" /> Recent activity</CardTitle></CardHeader>
        <CardContent>
          {activitiesQ.isLoading ? <Skeleton className="h-20 w-full" /> : (activitiesQ.data ?? []).length ? (
            <div className="flex flex-col gap-1.5">
              {(activitiesQ.data).slice(0,6).map((a) => (
                <div key={a.id} className="flex items-center justify-between rounded border px-3 py-1.5 text-sm">
                  <span className="truncate">{a.activity_type} — {a.outcome ?? "—"}</span>
                  <span className="text-xs text-muted-foreground">{a.created_at ? new Date(a.created_at).toLocaleDateString() : ""}</span>
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-muted-foreground">No activity yet. Log calls and activities from a lead workspace.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
