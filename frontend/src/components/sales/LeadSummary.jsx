import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

function Row({ label, value }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</span>
      <span className="text-sm font-medium text-foreground">{value ?? "—"}</span>
    </div>
  );
}

export default function LeadSummary({ lead, sourceName, pipelineName, assignedLabel }) {
  return (
    <Card className="rounded-xl">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">Lead information</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-2">
        <Row label="Owner" value={assignedLabel} />
        <Row label="Source" value={sourceName} />
        <Row label="Company" value={lead.company_name} />
        <Row label="Pipeline" value={pipelineName} />
        <Row label="Email" value={lead.email} />
        <Row label="Phone" value={lead.phone} />
      </CardContent>
    </Card>
  );
}

export function TaskSummary({ task }) {
  if (!task) {
    return (
      <Card className="rounded-xl border-dashed">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Current task</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No open task linked to this lead. Create a follow-up or activity to generate one.</p>
        </CardContent>
      </Card>
    );
  }
  return (
    <Card className="rounded-xl">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold">Current task</CardTitle>
          <Badge variant="secondary">{task.status_name ?? task.status ?? "Open"}</Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-1">
        <div className="text-sm font-medium">{task.task_title ?? task.title}</div>
        <div className="text-xs text-muted-foreground truncate">{task.description ?? "—"}</div>
        <div className="flex gap-2 text-xs text-muted-foreground">
          <span>{task.due_date ? new Date(task.due_date).toLocaleString() : "No due date"}</span>
          {task.priority_name ? <><span>·</span><span>{task.priority_name}</span></> : null}
        </div>
      </CardContent>
    </Card>
  );
}
