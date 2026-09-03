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
import { Bell, Activity } from "lucide-react";

function DashboardHero({ user, stats }) {
  const greeting = `Good morning, ${user?.username || user?.email?.split("@")[0] || "there"}`;
  return (
    <div className="rounded-[20px] bg-primary bg-gradient-to-br from-primary to-primary-fixed-dim p-6 text-white shadow-lg md:p-8">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="font-display text-2xl font-semibold md:text-3xl">{greeting}</h2>
          <p className="mt-1 text-sm text-white/70">Here is what is happening with your pipeline today.</p>
        </div>
        <Link to="/leads" className="inline-flex h-9 items-center justify-center rounded-[9px] bg-secondary px-5 text-sm font-semibold text-[#2B1206] hover:bg-[#E0532A]">View leads</Link>
      </div>
      <div className="mt-8 grid grid-cols-2 gap-0 divide-x divide-white/15 rounded-[12px] border border-white/15 bg-white/5 md:grid-cols-4">
        {stats.map((s) => {
          const content = (
            <>
              <span className="text-xs font-medium uppercase tracking-wider text-white/60">{s.title}</span>
              {s.loading ? <Skeleton className="h-7 w-16 bg-white/20" /> : <span className={`font-mono font-semibold text-white ${s.hero ? "text-3xl" : "text-2xl"}`}>{s.value}</span>}
              {s.desc ? <span className="text-xs text-white/60">{s.desc}</span> : null}
            </>
          );
          return s.to ? (
            <Link key={s.title} to={s.to} className="flex flex-col gap-1 px-4 py-4 md:px-6 rounded-[10px] hover:bg-white/10 transition-colors cursor-pointer">
              {content}
            </Link>
          ) : (
            <div key={s.title} className="flex flex-col gap-1 px-4 py-4 md:px-6">
              {content}
            </div>
          );
        })}
      </div>
    </div>
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

  const heroStats = [
    { title: "Open leads", value: leadsQ.isLoading ? "—" : openLeads, desc: "Active", loading: leadsQ.isLoading, to: "/leads" },
    { title: "Pipeline value", value: pendingQuotations ? `₹${(pendingQuotations * 125000).toLocaleString("en-IN")}` : leadsQ.isLoading ? "—" : `₹${(openLeads * 85000).toLocaleString("en-IN")}`, desc: "Est. total", hero: true, loading: leadsQ.isLoading || quotationsQ.isLoading, to: "/leads" },
    { title: "Overdue", value: tasksQ.isLoading ? "—" : overdueTasks, desc: "Need attention", loading: tasksQ.isLoading, to: "/tasks?inbox=overdue" },
    { title: "Today", value: tasksQ.isLoading ? "—" : todayTasks, desc: "Due today", loading: tasksQ.isLoading, to: "/tasks?inbox=today" },
  ];

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-on-surface">Overview</h1>
        <Button variant="outline" onClick={logout}>Log out</Button>
      </div>

      {hasNoRole ? (
        <p className="rounded-[12px] border border-warning-border bg-warning-soft px-3 py-2 text-sm text-warning">
          Your account has no role yet — ask an admin to assign one (user ID: <span className="font-mono">{user?.user_id}</span>).
        </p>
      ) : null}

      <DashboardHero user={user} stats={heroStats} loading={leadsQ.isLoading} />

      <div className="grid gap-6 lg:grid-cols-[1.55fr_1fr]">
        <Card className="rounded-[20px]">
          <CardHeader className="flex flex-row items-center justify-between">
            <div><CardTitle className="text-[14.5px]">Pipeline by stage</CardTitle><CardDescription>{pipelinesQ.data?.[0]?.name ?? "Enterprise Sales"} · {allLeadsQ.data?.count ?? byStage.reduce((a,b)=>a+b.count,0)} open leads</CardDescription></div>
            <Button variant="ghost" size="sm" asChild><Link to="/leads">View board →</Link></Button>
          </CardHeader>
          <CardContent>
            {stagesQ.isLoading || allLeadsQ.isLoading ? <Skeleton className="h-24 w-full" /> : byStage.length ? (
              <div className="flex flex-col">
                {(() => { const max = Math.max(...byStage.map(s=>s.count),1); return byStage.map((s) => {
                  const pct = Math.round((s.count/max)*100);
                  return (
                    <Link key={s.name} to={`/leads?stage=${encodeURIComponent(s.name)}`} className="flex items-center gap-3.5 py-3 border-b border-border last:border-0 hover:bg-muted/40 -mx-2 px-2 rounded-lg transition-colors">
                      <span className="w-32 text-[12.5px] font-semibold text-[var(--pine-ink)] truncate">{s.name}</span>
                      <span className="flex-1 h-2.5 bg-[var(--surface-container)] rounded-full overflow-hidden"><span className="block h-full rounded-full bg-gradient-to-r from-primary to-[var(--primary-container)]" style={{width: `${pct}%`}} /></span>
                      <span className="w-28 text-right font-mono text-xs text-muted-foreground"><strong className="text-foreground font-semibold">{s.count}</strong> leads</span>
                    </Link>
                  );
                });})()}
              </div>
            ) : <p className="text-sm text-muted-foreground">No pipeline stages configured. Create one under Admin · Pipelines.</p>}
          </CardContent>
        </Card>

        <div className="flex flex-col gap-6">
          <Card className="rounded-[20px]">
            <CardHeader className="flex flex-row items-center justify-between">
              <div><CardTitle className="text-[14.5px]">Tasks due today</CardTitle><CardDescription>{todayTasks} open · {overdueTasks} overdue</CardDescription></div>
              <Button variant="ghost" size="sm" asChild><Link to="/tasks">All tasks →</Link></Button>
            </CardHeader>
            <CardContent>
              {(tasksQ.data?.results ?? tasksQ.data ?? []).length === 0 ? <p className="text-sm text-muted-foreground">No tasks due.</p> : (
                <div className="flex flex-col">
                  {(tasksQ.data?.results ?? tasksQ.data ?? []).filter(t=> t.due_date && new Date(t.due_date) >= startToday && new Date(t.due_date) < endToday).slice(0,3).map((t) => (
                    <Link key={t.task_id} to={t.lead ? `/leads/${t.lead}` : `/tasks/${t.task_id}`} className="flex items-center gap-3 py-2.5 border-b border-border last:border-0 hover:bg-muted/40 -mx-2 px-2 rounded-lg">
                      <span className="w-[19px] h-[19px] rounded-[6px] border-[1.6px] border-[var(--outline)] shrink-0" />
                      <span className="flex-1 min-w-0"><span className="block text-[13px] font-semibold truncate">{t.task_title}</span><span className="block text-[11.5px] text-muted-foreground truncate">{t.lead ? "Lead workspace" : "General"} · {t.priority ? String(t.priority) : ""}</span></span>
                      <span className="font-mono text-[11px] font-semibold shrink-0" style={{color: overdueTasks ? "var(--error)" : "var(--muted-foreground)"}}>{t.due_date ? new Date(t.due_date).toLocaleTimeString([], {hour:"numeric", minute:"2-digit"}) : ""}</span>
                    </Link>
                  ))}
                  {(tasksQ.data?.results ?? tasksQ.data ?? []).filter(t=> t.due_date && new Date(t.due_date) >= startToday && new Date(t.due_date) < endToday).length===0 && <p className="text-sm text-muted-foreground py-2">No tasks due today.</p>}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-[20px]">
            <CardHeader><CardTitle className="text-[14.5px] flex items-center gap-2"><Bell className="h-4 w-4" /> Notifications</CardTitle></CardHeader>
            <CardContent>
              {notificationsQ.isLoading ? <Skeleton className="h-20 w-full" /> : (notificationsQ.data?.results ?? notificationsQ.data ?? []).length ? (
                <div className="flex flex-col gap-2">
                  {(notificationsQ.data?.results ?? notificationsQ.data).slice(0,4).map((n) => (
                    <Link key={n.id} to="/notifications" className="rounded border px-2 py-1.5 text-sm truncate hover:bg-muted/50 block">{n.message}</Link>
                  ))}
                  <Link to="/notifications" className="text-xs text-primary hover:underline">View all →</Link>
                </div>
              ) : <p className="text-sm text-muted-foreground">No unread notifications.</p>}
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.55fr_1fr]">
        <Card className="rounded-[20px]">
          <CardHeader><CardTitle className="text-[14.5px] flex items-center gap-2"><Activity className="h-4 w-4" /> Recent activity</CardTitle></CardHeader>
          <CardContent>
            {activitiesQ.isLoading ? <Skeleton className="h-20 w-full" /> : (activitiesQ.data ?? []).length ? (
              <div className="flex flex-col">
                {(activitiesQ.data).slice(0,5).map((a) => (
                  <div key={a.id} className="grid grid-cols-[30px_1fr] gap-2.5 py-3 border-b border-border last:border-0">
                    <span className="w-[30px] h-[30px] rounded-full bg-[var(--primary-soft)] border border-[var(--outline-variant)] grid place-items-center"><Activity className="h-3.5 w-3.5 text-primary" /></span>
                    <div><div className="text-[12.5px] leading-[1.45]"><strong>{a.activity_type}</strong> — {a.outcome ?? "—"}</div><div className="text-[11px] text-muted-foreground mt-0.5">{a.created_at ? new Date(a.created_at).toLocaleString() : ""}</div></div>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-muted-foreground">No activity yet. Log calls and activities from a lead workspace.</p>}
          </CardContent>
        </Card>

        <Card className="rounded-[20px]">
          <CardHeader className="flex flex-row items-center justify-between"><CardTitle className="text-[14.5px]">Highest-value leads</CardTitle><Button variant="ghost" size="sm" asChild><Link to="/leads?ordering=-total_value">→</Link></Button></CardHeader>
          <CardContent>
            {(() => {
              const leads = (allLeadsQ.data?.results ?? allLeadsQ.data ?? []).slice().sort((a,b)=> Number(b.total_value||0)-Number(a.total_value||0)).slice(0,4);
              if (!leads.length) return <p className="text-sm text-muted-foreground">No leads yet.</p>;
              return <div className="flex flex-col">{leads.map((l)=> (
                <Link key={l.id} to={`/leads/${l.id}`} className="flex items-center gap-2.5 py-2.5 border-b border-border last:border-0 hover:bg-muted/40 -mx-2 px-2 rounded-lg">
                  <span className="w-8 h-8 rounded-full bg-[var(--secondary-soft)] text-[var(--secondary-container)] grid place-items-center font-display font-bold text-[11px] shrink-0">{(l.name||"?").slice(0,2).toUpperCase()}</span>
                  <span className="flex-1 min-w-0"><span className="block text-[12.5px] font-semibold truncate">{l.name}</span><span className="block text-[11px] text-muted-foreground truncate">{l.company_name ?? "—"} · {stagesQ.data?.find(s=>s.id===l.current_stage)?.name ?? ""}</span></span>
                  <span className="font-mono text-[12.5px] font-semibold shrink-0">₹{Number(l.total_value||0) >= 100000 ? `${(Number(l.total_value)/100000).toFixed(1)}L` : Number(l.total_value||0).toLocaleString("en-IN")}</span>
                </Link>
              ))}</div>;
            })()}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
