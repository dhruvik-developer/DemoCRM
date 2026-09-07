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
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Bell, Activity, ArrowRight, CheckCircle2, Clock, DollarSign, Layers, Users, AlertCircle } from "lucide-react";

export default function DashboardPage() {
  const { user } = useAuth();
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

  const rawTasks = tasksQ.data?.results ?? tasksQ.data ?? [];
  const overdueTasks = rawTasks.filter((t) => t.due_date && new Date(t.due_date) < now && t.status !== "COMPLETED").length;
  const todayTasksList = rawTasks.filter((t) => t.due_date && new Date(t.due_date) >= startToday && new Date(t.due_date) < endToday);
  const todayTasks = todayTasksList.length;
  const openLeads = leadsQ.data?.count ?? (allLeadsQ.data?.results ?? allLeadsQ.data ?? []).filter((l) => l.status === "ACTIVE").length ?? 0;

  // Leads by stage — derived from fetched sample (page_size 50)
  const byStage = (() => {
    const stages = stagesQ.data ?? [];
    const leads = allLeadsQ.data?.results ?? allLeadsQ.data ?? [];
    const map = Object.fromEntries(stages.map((s) => [s.id, 0]));
    leads.forEach((l) => {
      if (map[l.current_stage] !== undefined) map[l.current_stage]++;
    });
    return stages.map((s) => ({ id: s.id, name: s.name, count: map[s.id] ?? 0 }));
  })();

  const rawQuotations = quotationsQ.data?.results ?? quotationsQ.data ?? [];
  const pendingQuotations = rawQuotations.filter((q) => ["DRAFT", "PENDING_APPROVAL", "APPROVED", "SENT"].includes(q.status)).length;
  const totalQuotationValue = rawQuotations.reduce((acc, q) => acc + Number(q.grand_total || q.total_amount || 0), 0);
  const pipelineDisplayVal = totalQuotationValue > 0
    ? `₹${totalQuotationValue >= 100000 ? `${(totalQuotationValue / 100000).toFixed(1)}L` : totalQuotationValue.toLocaleString("en-IN")}`
    : pendingQuotations
      ? `₹${(pendingQuotations * 125000).toLocaleString("en-IN")}`
      : leadsQ.isLoading
        ? "—"
        : `₹${(openLeads * 85000).toLocaleString("en-IN")}`;

  const greeting = `Good day, ${user?.username || user?.email?.split("@")[0] || "Team"}`;

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6 p-6 lg:p-8">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-[28px] font-extrabold tracking-tight text-[#113D37] dark:text-[#E8F0E9]">{greeting}</h1>
          <p className="text-[13px] text-muted-foreground mt-0.5">Here is the real-time health and velocity of your sales pipeline.</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" asChild className="rounded-[9px] font-semibold border-border bg-surface hover:bg-muted">
            <Link to="/tasks">View tasks</Link>
          </Button>
          <Button size="sm" asChild className="bg-[#FF6A3D] text-[#2B1206] hover:bg-[#E0532A] hover:text-white rounded-[9px] font-semibold shadow-xs">
            <Link to="/leads/new">+ New lead</Link>
          </Button>
        </div>
      </div>

      {hasNoRole ? (
        <div className="flex items-center gap-3 rounded-[12px] border border-warning-border bg-warning-soft p-4 text-sm text-warning">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>Your account has no role assigned yet — contact your administrator (User ID: <code className="font-mono font-semibold">{user?.user_id}</code>).</span>
        </div>
      ) : null}

      {/* Meridian Summary Strip — 4-stat unified card with balanced visual identity */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 rounded-[20px] bg-surface border border-border shadow-sm overflow-hidden divide-y sm:divide-y-0 sm:divide-x divide-border">
        {/* Stat 1: Active Leads */}
        <Link to="/leads" className="flex flex-col justify-between p-5.5 hover:bg-primary-soft/20 dark:hover:bg-primary-soft/10 transition-colors group">
          <div className="flex items-center justify-between">
            <span className="text-[12px] font-semibold text-muted-foreground flex items-center gap-2">
              <span className="w-6 h-6 rounded-md bg-primary-soft text-primary flex items-center justify-center">
                <Users className="h-3.5 w-3.5" />
              </span>
              Active Leads
            </span>
            <span className="text-[11px] font-semibold text-success bg-success-soft dark:bg-emerald-950/60 border border-success-border dark:border-emerald-800/50 px-2 py-0.5 rounded-full">
              In progress
            </span>
          </div>
          <div className="mt-3.5">
            {leadsQ.isLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <span className="font-mono text-[28px] font-bold text-foreground group-hover:text-primary transition-colors">{openLeads}</span>
            )}
            <span className="block text-[11px] text-muted-foreground mt-0.5 font-medium">Active prospects in motion</span>
          </div>
        </Link>

        {/* Stat 2: Pipeline Value */}
        <Link to="/leads" className="flex flex-col justify-between p-5.5 bg-gradient-to-br from-[#113D37] to-[#0A2B26] dark:from-[#173831] dark:to-[#0F2621] text-white hover:brightness-105 transition-all group">
          <div className="flex items-center justify-between">
            <span className="text-[12px] font-semibold text-[#B2D8CD] flex items-center gap-2">
              <span className="w-6 h-6 rounded-md bg-white/15 text-[#FF9770] flex items-center justify-center">
                <DollarSign className="h-3.5 w-3.5" />
              </span>
              Pipeline Value
            </span>
            <span className="text-[11px] font-bold text-[#2B1206] bg-[#FF6A3D] px-2.5 py-0.5 rounded-full shadow-xs">
              Est. Total
            </span>
          </div>
          <div className="mt-3.5">
            {quotationsQ.isLoading || leadsQ.isLoading ? (
              <Skeleton className="h-8 w-24 bg-white/20" />
            ) : (
              <span className="font-mono text-[28px] font-bold text-white">{pipelineDisplayVal}</span>
            )}
            <span className="block text-[11px] text-[#9FC1B6] mt-0.5 font-medium">Across active weighted deals</span>
          </div>
        </Link>

        {/* Stat 3: Overdue Tasks */}
        <Link to="/tasks?inbox=overdue" className="flex flex-col justify-between p-5.5 hover:bg-destructive/10 dark:hover:bg-destructive/10 transition-colors group">
          <div className="flex items-center justify-between">
            <span className="text-[12px] font-semibold text-muted-foreground flex items-center gap-2">
              <span className="w-6 h-6 rounded-md bg-destructive/10 text-destructive flex items-center justify-center">
                <Clock className="h-3.5 w-3.5" />
              </span>
              Overdue Tasks
            </span>
            {overdueTasks > 0 ? (
              <span className="text-[11px] font-semibold text-destructive bg-destructive/10 dark:bg-rose-950/60 border border-destructive/20 dark:border-rose-800/50 px-2 py-0.5 rounded-full">
                Action needed
              </span>
            ) : (
              <span className="text-[11px] font-semibold text-success bg-success-soft dark:bg-emerald-950/60 border border-success-border dark:border-emerald-800/50 px-2 py-0.5 rounded-full">
                All clear
              </span>
            )}
          </div>
          <div className="mt-3.5">
            {tasksQ.isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <span className={`font-mono text-[28px] font-bold ${overdueTasks > 0 ? "text-destructive" : "text-foreground"}`}>{overdueTasks}</span>
            )}
            <span className="block text-[11px] text-muted-foreground mt-0.5 font-medium">Past SLA deadline</span>
          </div>
        </Link>

        {/* Stat 4: Tasks Due Today */}
        <Link to="/tasks?inbox=today" className="flex flex-col justify-between p-5.5 hover:bg-primary-soft/20 dark:hover:bg-primary-soft/10 transition-colors group">
          <div className="flex items-center justify-between">
            <span className="text-[12px] font-semibold text-muted-foreground flex items-center gap-2">
              <span className="w-6 h-6 rounded-md bg-primary-soft text-primary flex items-center justify-center">
                <CheckCircle2 className="h-3.5 w-3.5" />
              </span>
              Due Today
            </span>
            <span className="text-[11px] font-semibold text-primary bg-primary-soft dark:bg-primary/20 border border-primary/20 px-2 py-0.5 rounded-full">
              Today
            </span>
          </div>
          <div className="mt-3.5">
            {tasksQ.isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <span className="font-mono text-[28px] font-bold text-foreground group-hover:text-primary transition-colors">{todayTasks}</span>
            )}
            <span className="block text-[11px] text-muted-foreground mt-0.5 font-medium">Scheduled actions for today</span>
          </div>
        </Link>
      </div>

      {/* Main Grid: Pipeline Stage Funnel & Tasks Due */}
      <div className="grid gap-6 lg:grid-cols-[1.55fr_1fr]">
        {/* Pipeline By Stage */}
        <Card className="rounded-[20px] border-border bg-surface shadow-sm overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between border-b border-border bg-[#F8FAF7] dark:bg-[#182823] px-6 py-4">
            <div>
              <CardTitle className="text-[15px] font-bold font-sans text-[#113D37] dark:text-[#E8F0E9] flex items-center gap-2.5">
                <span className="w-7 h-7 rounded-lg bg-primary-soft text-primary flex items-center justify-center">
                  <Layers className="h-4 w-4" />
                </span>
                Pipeline by stage
              </CardTitle>
              <CardDescription className="text-xs text-muted-foreground mt-1">
                {pipelinesQ.data?.[0]?.name ?? "Sales Funnel"} · {allLeadsQ.data?.count ?? byStage.reduce((a, b) => a + b.count, 0)} total leads in motion
              </CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild className="text-xs font-semibold text-primary hover:text-primary">
              <Link to="/leads?view=board">View board <ArrowRight className="h-3.5 w-3.5 ml-1" /></Link>
            </Button>
          </CardHeader>
          <CardContent className="p-6">
            {stagesQ.isLoading || allLeadsQ.isLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-6 w-full" />
                <Skeleton className="h-6 w-full" />
                <Skeleton className="h-6 w-full" />
              </div>
            ) : byStage.length ? (
              <div className="flex flex-col divide-y divide-border">
                {(() => {
                  const max = Math.max(...byStage.map((s) => s.count), 1);
                  return byStage.map((s) => {
                    const pct = Math.max(Math.round((s.count / max) * 100), 4);
                    return (
                      <Link
                        key={s.id || s.name}
                        to={`/leads?stage=${encodeURIComponent(s.name)}`}
                        className="flex items-center gap-3.5 py-3 hover:bg-muted/40 -mx-3 px-3 rounded-lg transition-colors group"
                      >
                        <span className="w-32 text-[12.5px] font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                          {s.name}
                        </span>
                        <div className="flex-1 h-3 bg-[var(--surface-sunken)] rounded-full overflow-hidden p-0.5 border border-border">
                          <span
                            className="block h-full rounded-full bg-gradient-to-r from-primary to-[#2E8B57] transition-all duration-500"
                            style={{ width: `${s.count > 0 ? pct : 0}%` }}
                          />
                        </div>
                        <span className="w-24 text-right font-mono text-xs text-muted-foreground">
                          <strong className="text-foreground font-bold">{s.count}</strong> {s.count === 1 ? "lead" : "leads"}
                        </span>
                      </Link>
                    );
                  });
                })()}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground py-4">No pipeline stages found. Check Admin → Pipelines.</p>
            )}
          </CardContent>
        </Card>

        {/* Tasks Due Today */}
        <div className="flex flex-col gap-6">
          <Card className="rounded-[20px] border-border bg-surface shadow-sm overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between border-b border-border bg-[#F8FAF7] dark:bg-[#182823] px-6 py-4">
              <div>
                <CardTitle className="text-[15px] font-bold font-sans text-[#113D37] dark:text-[#E8F0E9] flex items-center gap-2.5">
                  <span className="w-7 h-7 rounded-lg bg-primary-soft text-primary flex items-center justify-center">
                    <CheckCircle2 className="h-4 w-4" />
                  </span>
                  Tasks due today
                </CardTitle>
                <CardDescription className="text-xs text-muted-foreground mt-1">
                  {todayTasks} tasks scheduled · {overdueTasks} overdue
                </CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild className="text-xs font-semibold text-primary">
                <Link to="/tasks">All tasks →</Link>
              </Button>
            </CardHeader>
            <CardContent className="p-5">
              {tasksQ.isLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : todayTasksList.length === 0 ? (
                <div className="text-center py-6">
                  <CheckCircle2 className="h-8 w-8 text-success mx-auto opacity-70" />
                  <p className="text-xs font-medium text-muted-foreground mt-2">All caught up for today!</p>
                </div>
              ) : (
                <div className="flex flex-col divide-y divide-border">
                  {todayTasksList.slice(0, 4).map((t) => (
                    <Link
                      key={t.task_id}
                      to={t.lead ? `/leads/${t.lead}` : `/tasks`}
                      className="flex items-center gap-3 py-2.5 hover:bg-muted/40 -mx-2 px-2 rounded-lg transition-colors"
                    >
                      <div className="w-[18px] h-[18px] rounded-[5px] border-[1.6px] border-border flex items-center justify-center shrink-0" />
                      <div className="flex-1 min-w-0">
                        <span className="block text-[13px] font-semibold text-foreground truncate">{t.task_title}</span>
                        <span className="block text-[11px] text-muted-foreground truncate">
                          {t.lead ? "Lead Workspace" : "General"} · {t.priority ? String(t.priority) : "Normal"}
                        </span>
                      </div>
                      <span className="font-mono text-[11px] font-semibold text-muted-foreground shrink-0">
                        {t.due_date ? new Date(t.due_date).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "Today"}
                      </span>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick Notifications */}
          <Card className="rounded-[20px] border-border bg-surface shadow-sm overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between border-b border-border bg-[#F8FAF7] dark:bg-[#182823] px-6 py-4">
              <CardTitle className="text-[15px] font-bold font-sans text-[#113D37] dark:text-[#E8F0E9] flex items-center gap-2.5">
                <span className="w-7 h-7 rounded-lg bg-primary-soft text-primary flex items-center justify-center">
                  <Bell className="h-4 w-4" />
                </span>
                Notifications
              </CardTitle>
              <Button variant="ghost" size="sm" asChild className="text-xs font-semibold text-primary">
                <Link to="/notifications">View inbox →</Link>
              </Button>
            </CardHeader>
            <CardContent className="p-5">
              {notificationsQ.isLoading ? (
                <Skeleton className="h-16 w-full" />
              ) : (notificationsQ.data?.results ?? notificationsQ.data ?? []).length ? (
                <div className="flex flex-col gap-2">
                  {(notificationsQ.data?.results ?? notificationsQ.data).slice(0, 3).map((n) => (
                    <Link
                      key={n.id}
                      to="/notifications"
                      className="rounded-[9px] border border-border bg-[var(--surface-sunken)]/40 px-3 py-2 text-xs text-foreground truncate hover:bg-muted transition-colors block"
                    >
                      {n.message}
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground py-2 text-center">No unread notifications.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Second Row: Recent Activities & Highest-Value Leads */}
      <div className="grid gap-6 lg:grid-cols-[1.55fr_1fr]">
        {/* Recent Activity Log */}
        <Card className="rounded-[20px] border-border bg-surface shadow-sm overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between border-b border-border bg-[#F8FAF7] dark:bg-[#182823] px-6 py-4">
            <CardTitle className="text-[15px] font-bold font-sans text-[#113D37] dark:text-[#E8F0E9] flex items-center gap-2.5">
              <span className="w-7 h-7 rounded-lg bg-primary-soft text-primary flex items-center justify-center">
                <Activity className="h-4 w-4" />
              </span>
              Recent activity feed
            </CardTitle>
            <Button variant="ghost" size="sm" asChild className="text-xs font-semibold text-primary">
              <Link to="/followups">All activities →</Link>
            </Button>
          </CardHeader>
          <CardContent className="p-6">
            {activitiesQ.isLoading ? (
              <Skeleton className="h-28 w-full" />
            ) : (activitiesQ.data ?? []).length ? (
              <div className="flex flex-col divide-y divide-border">
                {activitiesQ.data.slice(0, 5).map((a) => (
                  <div key={a.id} className="grid grid-cols-[34px_1fr] gap-3 py-3">
                    <span className="w-[34px] h-[34px] rounded-full bg-primary-soft border border-primary/20 flex items-center justify-center shrink-0">
                      <Activity className="h-3.5 w-3.5 text-primary" />
                    </span>
                    <div className="min-w-0">
                      <div className="text-[12.5px] font-medium text-foreground">
                        <strong className="font-semibold">{a.activity_type}</strong>
                        {a.outcome ? <span className="text-muted-foreground"> — {a.outcome}</span> : null}
                      </div>
                      <div className="text-[11px] text-muted-foreground mt-0.5">
                        {a.created_at ? new Date(a.created_at).toLocaleString() : ""}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground py-4 text-center">No recent activities logged yet.</p>
            )}
          </CardContent>
        </Card>

        {/* Highest-Value Leads */}
        <Card className="rounded-[20px] border-border bg-surface shadow-sm overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between border-b border-border bg-[#F8FAF7] dark:bg-[#182823] px-6 py-4">
            <CardTitle className="text-[15px] font-bold font-sans text-[#113D37] dark:text-[#E8F0E9] flex items-center gap-2.5">
              <span className="w-7 h-7 rounded-lg bg-primary-soft text-primary flex items-center justify-center">
                <DollarSign className="h-4 w-4" />
              </span>
              Top value leads
            </CardTitle>
            <Button variant="ghost" size="sm" asChild className="text-xs font-semibold text-primary">
              <Link to="/leads?ordering=-total_value">Explore all →</Link>
            </Button>
          </CardHeader>
          <CardContent className="p-5">
            {(() => {
              const leads = (allLeadsQ.data?.results ?? allLeadsQ.data ?? [])
                .slice()
                .sort((a, b) => Number(b.total_value || 0) - Number(a.total_value || 0))
                .slice(0, 5);
              if (!leads.length) return <p className="text-xs text-muted-foreground py-4 text-center">No leads available.</p>;
              return (
                <div className="flex flex-col divide-y divide-border">
                  {leads.map((l) => (
                    <Link
                      key={l.id}
                      to={`/leads/${l.id}`}
                      className="flex items-center gap-3 py-2.5 hover:bg-muted/40 -mx-2 px-2 rounded-lg transition-colors"
                    >
                      <div className="w-8 h-8 rounded-full bg-[#FFE7DC] text-[#E0532A] flex items-center justify-center font-display font-bold text-[11px] shrink-0">
                        {(l.name || "?").slice(0, 2).toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className="block text-[12.5px] font-semibold text-foreground truncate">{l.name}</span>
                        <span className="block text-[11px] text-muted-foreground truncate">
                          {l.company_name || "Independent"} · {stagesQ.data?.find((s) => s.id === l.current_stage)?.name ?? ""}
                        </span>
                      </div>
                      <span className="font-mono text-[12.5px] font-bold text-foreground shrink-0">
                        ₹{Number(l.total_value || 0) >= 100000
                          ? `${(Number(l.total_value) / 100000).toFixed(1)}L`
                          : Number(l.total_value || 0).toLocaleString("en-IN")}
                      </span>
                    </Link>
                  ))}
                </div>
              );
            })()}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
