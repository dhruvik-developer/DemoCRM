import StatusBadge from "@/components/common/StatusBadge";
import { Badge } from "@/components/ui/badge";

export default function LeadHeader({ lead, pipelineName, stageName, sourceName }) {
  if (!lead) return null;
  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-[18px] font-semibold tracking-tight text-[#111214]">{lead.name}</h1>
            <StatusBadge status={lead.status} />
            {lead.company_name ? <Badge variant="outline">{lead.company_name}</Badge> : null}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span>{lead.company_name ?? "—"}</span>
            <span className="h-1 w-1 rounded-full bg-muted-foreground/40" />
            <span>{lead.email ?? "—"}</span>
            <span className="h-1 w-1 rounded-full bg-muted-foreground/40" />
            <span>{lead.phone ?? "—"}</span>
          </div>
        </div>
        <Badge variant={lead.status === "ACTIVE" ? "default" : "secondary"} className="uppercase tracking-wide text-[11px]">
          {lead.status}
        </Badge>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Pipeline</div>
          <div className="font-medium">{pipelineName ?? "—"}</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Current Stage</div>
          <div className="font-medium">{stageName ?? "—"}</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Source</div>
          <div className="font-medium">{sourceName ?? "—"}</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Value</div>
          <div className="font-medium">{lead.total_value ? `₹${lead.total_value}` : "—"}</div>
        </div>
      </div>
    </div>
  );
}
