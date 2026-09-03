import StatusBadge from "@/components/common/StatusBadge";
import { Badge } from "@/components/ui/badge";

export default function LeadHeader({ lead, pipelineName, stageName, sourceName }) {
  if (!lead) return null;
  return (
    <div className="flex flex-col gap-3 rounded-[14px] border border-[#E2E8F0] bg-white p-[22px_26px] shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 text-[12px] font-semibold text-muted-foreground">
            <span>{pipelineName ? `Pipeline: ${pipelineName}` : "Pipeline"}</span>
            <span>•</span>
            <StatusBadge status={lead.status} />
            {stageName ? (
              <Badge className="bg-[#EEF2FF] text-[#4F46E5] border-[#C7D2FE] hover:bg-[#EEF2FF] text-[11px] font-bold uppercase tracking-wide">
                {stageName}
              </Badge>
            ) : null}
          </div>
          <h1 className="mt-1 text-[24px] font-extrabold tracking-[-0.03em] text-[#0F172A] leading-tight truncate">{lead.name}</h1>
          <div className="mt-1.5 flex flex-wrap items-center gap-3.5 text-[13px] text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">👤 {lead.company_name ?? "—"}</span>
            <span className="inline-flex items-center gap-1.5">✉️ {lead.email ?? "—"}</span>
            <span className="inline-flex items-center gap-1.5">📞 {lead.phone ?? "—"}</span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge variant={lead.status === "ACTIVE" ? "default" : "secondary"} className="uppercase tracking-wide text-[11px] shrink-0">
            {lead.status}
          </Badge>
          {lead.total_value ? (
            <span className="text-sm font-bold text-foreground">₹{lead.total_value}</span>
          ) : null}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4 border-t border-[#F1F5F9] pt-3.5 mt-1">
        <div>
          <div className="text-[10.5px] font-bold uppercase tracking-wider text-[#94A3B8]">Pipeline</div>
          <div className="mt-1 text-[13px] font-bold text-[#0F172A]">{pipelineName ?? "—"}</div>
        </div>
        <div>
          <div className="text-[10.5px] font-bold uppercase tracking-wider text-[#94A3B8]">Current Stage</div>
          <div className="mt-1 text-[13px] font-bold text-[#0F172A]">{stageName ?? "—"}</div>
        </div>
        <div>
          <div className="text-[10.5px] font-bold uppercase tracking-wider text-[#94A3B8]">Source</div>
          <div className="mt-1 text-[13px] font-bold text-[#0F172A]">{sourceName ?? "—"}</div>
        </div>
        <div>
          <div className="text-[10.5px] font-bold uppercase tracking-wider text-[#94A3B8]">Value</div>
          <div className="mt-1 text-[13px] font-bold text-[#0F172A]">{lead.total_value ? `₹${lead.total_value}` : "—"}</div>
        </div>
      </div>
    </div>
  );
}
