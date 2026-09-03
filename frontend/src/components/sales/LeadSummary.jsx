import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

function Row({ label, value }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10.5px] font-bold uppercase tracking-[0.05em] text-[#94A3B8]">{label}</span>
      <span className="text-[13px] font-bold text-[#0F172A] truncate">{value ?? "—"}</span>
    </div>
  );
}

export default function LeadSummary({ lead, sourceName, pipelineName, assignedLabel }) {
  return (
    <Card className="rounded-[14px] border-[#E2E8F0] shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
      <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-[14px] font-bold tracking-[-0.01em]">Lead Master Information</CardTitle>
        <span className="text-[11.5px] text-muted-foreground font-medium">{lead.id ? `ID: ${String(lead.id).slice(0,8).toUpperCase()}` : ""}</span>
      </CardHeader>
      <CardContent className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        <Row label="Assigned Owner" value={assignedLabel} />
        <Row label="Source" value={sourceName} />
        <Row label="Pipeline" value={pipelineName} />
        <Row label="Company" value={lead.company_name} />
      </CardContent>
    </Card>
  );
}

export function TaskSummary({ task }) {
  if (!task) {
    return (
      <Card className="rounded-[14px] border-dashed border-[#E2E8F0]">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold">Current Assigned Task</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-[13px] text-muted-foreground">No open task linked to this lead. Create a follow-up or activity to generate one.</p>
        </CardContent>
      </Card>
    );
  }
  const isHigh = (task.priority_name ?? "").toLowerCase().includes("high") || task.priority === "high";
  return (
    <Card className="rounded-[14px] border-[#E2E8F0] shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold">Current Assigned Task</CardTitle>
          <Badge className={isHigh ? "bg-[#FFFBEB] text-[#B45309] border-[#FDE68A] hover:bg-[#FFFBEB] font-bold uppercase text-[11px]" : ""} variant={isHigh ? "outline" : "secondary"}>
            {isHigh ? "High Priority" : task.status_name ?? task.status ?? "Open"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <div className="text-[14px] font-extrabold text-[#0F172A]">{task.task_title ?? task.title}</div>
        <div className="text-[12px] text-muted-foreground">{task.due_date ? `Due ${new Date(task.due_date).toLocaleString()}` : "No due date"}</div>
        {task.description ? (
          <div className="rounded-[6px] bg-[#F1F5F9] px-2.5 py-2 text-[11.5px] leading-relaxed">
            <span className="font-bold">Instruction:</span> {task.description}
          </div>
        ) : (
          <div className="text-xs text-muted-foreground truncate">{task.description ?? "—"}</div>
        )}
        <div className="flex gap-2 text-xs text-muted-foreground">
          <span>{task.due_date ? new Date(task.due_date).toLocaleDateString() : ""}</span>
          {task.priority_name ? <><span>·</span><span>{task.priority_name}</span></> : null}
        </div>
      </CardContent>
    </Card>
  );
}
