import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Clock } from "lucide-react";

const PALETTE = [
  "var(--info)",
  "var(--warning)",
  "var(--secondary)",
  "var(--primary)",
  "var(--success)",
];

const STATUS_DOT = {
  ACTIVE: "bg-success",
  CONVERTED: "bg-success",
  LOST: "bg-error",
  REJECTED: "bg-error",
  PENDING: "bg-warning",
};

function initialsFromLead(lead) {
  const raw =
    lead?.assigned_to_name ??
    lead?.assigned_to_full_name ??
    lead?.owner_name ??
    lead?.assignee_name ??
    null;

  if (raw && typeof raw === "string" && raw.trim()) {
    const parts = raw.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  const at = lead?.assigned_to;
  if (at && typeof at === "object") {
    const name = at.full_name || at.username || at.email || "";
    if (name) {
      const p = String(name).trim().split(/\s+/);
      if (p.length === 1) return p[0].slice(0, 2).toUpperCase();
      return (p[0][0] + p[p.length - 1][0]).toUpperCase();
    }
  }
  if (typeof at === "string" && at) {
    // fallback: first 2 chars of uuid
    return at.slice(0, 2).toUpperCase();
  }
  // try owner initials field
  const fallback = lead?.owner_initials ?? lead?.assigned_initials ?? "";
  if (fallback) return String(fallback).slice(0, 2).toUpperCase();
  return "—";
}

function formatValue(lead) {
  const raw = lead?.total_value ?? lead?.value ?? lead?.amount ?? null;
  if (raw == null || raw === "") return null;
  const num = Number(raw);
  if (Number.isNaN(num)) return String(raw);
  // show compact Lakh if large, else locale
  if (num >= 100000) return `₹${(num / 100000).toFixed(1)}L`;
  return `₹${num.toLocaleString("en-IN")}`;
}

function isOverdue(lead) {
  const raw = lead?.due_date ?? lead?.dueDate ?? lead?.next_follow_up ?? lead?.follow_up_date ?? null;
  if (!raw) return false;
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return false;
  return d < new Date();
}

function dueLabel(lead) {
  const raw = lead?.due_date ?? lead?.dueDate ?? lead?.next_follow_up ?? lead?.follow_up_date ?? null;
  if (!raw) return null;
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return String(raw);
  const overdue = d < new Date();
  // simple label: Overdue or Due <date>
  if (overdue) return "Overdue";
  return `Due ${d.toLocaleDateString()}`;
}

export default function KanbanBoard({ stages = [], leads = [], isLoading = false, onLeadClick, onMoveStage }) {
  const navigate = useNavigate();

  const sortedStages = useMemo(() => {
    return [...(stages ?? [])].sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));
  }, [stages]);

  const leadsByStage = useMemo(() => {
    const map = new Map();
    for (const s of sortedStages) map.set(String(s.id), []);
    const unassigned = [];
    for (const lead of leads ?? []) {
      const key = String(lead.current_stage ?? lead.stage ?? lead.stage_id ?? "");
      if (map.has(key)) map.get(key).push(lead);
      else unassigned.push(lead);
    }
    return { map, unassigned };
  }, [sortedStages, leads]);

  if (isLoading) {
    return (
      <div className="flex gap-4 overflow-x-auto pb-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="min-w-[280px] flex-1 bg-surface-container rounded-[16px] border border-outline-variant p-4">
            <div className="h-4 w-24 bg-surface-dim rounded animate-pulse mb-3" />
            <div className="space-y-3">
              <div className="h-24 bg-surface rounded-[12px] animate-pulse" />
              <div className="h-24 bg-surface rounded-[12px] animate-pulse" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!sortedStages.length) {
    return (
      <div className="rounded-[16px] border border-outline-variant bg-surface-container p-8 text-center text-sm text-on-surface-variant">
        No pipeline stages found.
      </div>
    );
  }

  const handleLeadClick = (lead) => {
    if (onLeadClick) return onLeadClick(lead);
    navigate(`/leads/${lead.id}`);
  };

  return (
    <div className="flex gap-4 overflow-x-auto pb-2">
      {sortedStages.map((stage, idx) => {
        const stageLeads = leadsByStage.map.get(String(stage.id)) ?? [];
        const count = stageLeads.length;
        const total = stageLeads.reduce((sum, l) => sum + (Number(l.total_value ?? l.value ?? 0) || 0), 0);
        const totalLabel = total ? (total >= 100000 ? `₹${(total / 100000).toFixed(1)}L total` : `₹${total.toLocaleString("en-IN")} total`) : "—";
        const barColor = PALETTE[idx % PALETTE.length] ?? "var(--outline-variant)";

        return (
          <div
            key={stage.id}
            className="flex min-w-[280px] flex-1 flex-col bg-surface-container rounded-[16px] border border-outline-variant overflow-hidden"
            onDragOver={(e) => {
              if (onMoveStage) e.preventDefault();
            }}
            onDrop={(e) => {
              if (!onMoveStage) return;
              e.preventDefault();
              const leadId = e.dataTransfer.getData("text/plain");
              if (leadId) onMoveStage(leadId, stage.id);
            }}
          >
            <div className="h-1 w-full shrink-0" style={{ background: barColor }} />
            <div className="flex items-center justify-between px-3 pt-3 pb-2">
              <div className="min-w-0">
                <div className="text-[13px] font-semibold text-on-surface truncate">{stage.name}</div>
                <div className="font-mono text-[11px] text-on-surface-variant">{totalLabel}</div>
              </div>
              <span className="ml-2 inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-surface px-2 font-mono text-[11px] font-semibold text-on-surface-variant border border-outline-variant">
                {count}
              </span>
            </div>
            <div className="flex flex-col gap-3 px-2.5 pb-3 min-h-[120px]">
              {stageLeads.map((lead) => {
                const dotClass = STATUS_DOT[lead.status] ?? "bg-primary";
                const overdue = isOverdue(lead);
                const val = formatValue(lead);
                const ownerInitials = initialsFromLead(lead);
                const label = dueLabel(lead);
                return (
                  <div
                    key={lead.id}
                    draggable={Boolean(onMoveStage)}
                    onDragStart={(e) => {
                      if (onMoveStage) e.dataTransfer.setData("text/plain", String(lead.id));
                    }}
                    onClick={() => handleLeadClick(lead)}
                    className="bg-surface rounded-[12px] border border-outline-variant shadow-sm hover:border-border-hover p-3 flex flex-col gap-2 cursor-pointer transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <div className="font-display text-sm font-semibold text-on-surface truncate">{lead.name ?? "Untitled lead"}</div>
                        {lead.company_name ? <div className="text-[11px] text-on-surface-variant truncate">{lead.company_name}</div> : null}
                        {val ? <div className="font-mono text-xs text-on-surface-variant mt-1">{val}</div> : null}
                      </div>
                      <span className={`mt-1 h-1.5 w-1.5 rounded-full shrink-0 ${dotClass}`} aria-hidden />
                    </div>
                    <div className="flex items-center justify-between gap-2 mt-1">
                      {label ? (
                        <span className={`inline-flex items-center gap-1 text-[11px] ${overdue ? "text-error font-medium" : "text-on-surface-variant"}`}>
                          <Clock className="h-3 w-3 shrink-0" />
                          {label}
                        </span>
                      ) : (
                        <span />
                      )}
                      <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-soft text-primary font-mono text-[10px] font-bold">
                        {ownerInitials}
                      </span>
                    </div>
                  </div>
                );
              })}
              {count === 0 ? <div className="rounded-[12px] border border-dashed border-outline-variant bg-surface/60 p-4 text-center text-xs text-on-surface-variant">No leads</div> : null}
            </div>
          </div>
        );
      })}
      {leadsByStage.unassigned.length > 0 ? (
        <div className="flex min-w-[280px] flex-1 flex-col bg-surface-container rounded-[16px] border border-outline-variant overflow-hidden">
          <div className="h-1 w-full shrink-0" style={{ background: "var(--outline-variant)" }} />
          <div className="flex items-center justify-between px-3 pt-3 pb-2">
            <div className="min-w-0">
              <div className="text-[13px] font-semibold text-on-surface">Unassigned</div>
              <div className="font-mono text-[11px] text-on-surface-variant">
                {(() => {
                  const t = leadsByStage.unassigned.reduce((s, l) => s + (Number(l.total_value ?? 0) || 0), 0);
                  return t ? `₹${t.toLocaleString("en-IN")} total` : "—";
                })()}
              </div>
            </div>
            <span className="ml-2 inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-surface px-2 font-mono text-[11px] font-semibold text-on-surface-variant border border-outline-variant">
              {leadsByStage.unassigned.length}
            </span>
          </div>
          <div className="flex flex-col gap-3 px-2.5 pb-3 min-h-[120px]">
            {leadsByStage.unassigned.map((lead) => {
              const dotClass = STATUS_DOT[lead.status] ?? "bg-primary";
              const overdue = isOverdue(lead);
              const val = formatValue(lead);
              return (
                <div
                  key={lead.id}
                  onClick={() => handleLeadClick(lead)}
                  className="bg-surface rounded-[12px] border border-outline-variant shadow-sm hover:border-border-hover p-3 flex flex-col gap-2 cursor-pointer"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-display text-sm font-semibold text-on-surface truncate">{lead.name}</div>
                    <span className={`mt-1 h-1.5 w-1.5 rounded-full shrink-0 ${dotClass}`} />
                  </div>
                  {val ? <div className="font-mono text-xs text-on-surface-variant">{val}</div> : null}
                  <div className="flex items-center justify-between">
                    <span className={`inline-flex items-center gap-1 text-[11px] ${overdue ? "text-error" : "text-on-surface-variant"}`}>
                      <Clock className="h-3 w-3" />
                      {dueLabel(lead) ?? ""}
                    </span>
                    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary-soft text-primary font-mono text-[10px] font-bold">
                      {initialsFromLead(lead)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
