import { useLeadTimeline, useLeadPrimaryForm } from "@/features/callforms/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useState } from "react";

export default function FormResponseHistory({ leadId }) {
  const q = useLeadTimeline({ lead_id: leadId });
  const primary = useLeadPrimaryForm(leadId);
  const items = q.data ?? [];
  // API returns timeline feed newest-first already; normalize
  const submissions = Array.isArray(items) ? items : items.results ?? [];
  const labelMap = Object.fromEntries((primary.data?.fields ?? []).map((f) => [f.field_key, f.label]));
  const [openId, setOpenId] = useState(null);

  if (q.isLoading) return <div className="text-sm text-muted-foreground">Loading history…</div>;
  if (!submissions.length) {
    return (
      <Card className="rounded-xl border-dashed">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Form response history</CardTitle></CardHeader>
        <CardContent><p className="text-sm text-muted-foreground">No submissions yet. Fill the current stage form above.</p></CardContent>
      </Card>
    );
  }

  return (
    <Card className="rounded-[14px] border-[#E2E8F0] shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
      <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-bold">Submitted Responses History</CardTitle>
        <Badge className="bg-[#ECFDF5] text-[#047857] border-[#A7F3D0] font-bold text-[11px]">{submissions.length} Submissions Stored</Badge>
      </CardHeader>
      <CardContent className="flex max-h-[500px] flex-col gap-3 overflow-y-auto pr-1">
        {submissions.slice(0, 10).map((row, idx) => (
          <div key={row.id ?? row.submission_id} className="rounded-[6px] border border-[#E2E8F0] p-[14px_16px] bg-[#FAFBFC]" style={{ borderLeftWidth: "3.5px", borderLeftColor: idx === 0 ? "#4F46E5" : "#94A3B8" }}>
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-[12.5px] font-bold text-[#0F172A]">{row.template_name ?? row.template_version ?? "Submission"} · {row.version_label ?? ""}</div>
                <div className="mt-0.5 text-[11px] text-muted-foreground">Submitted by {row.submitted_by_name ?? (row.submitted_by ? String(row.submitted_by).slice(0,8) : "—")} • {row.submitted_at ? new Date(row.submitted_at).toLocaleString() : row.created_at ? new Date(row.created_at).toLocaleString() : ""}</div>
              </div>
              <Badge className="bg-[#ECFDF5] text-[#047857] border-[#A7F3D0] text-[11px] font-bold uppercase">Verified</Badge>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-x-3.5 gap-y-2">
              {row.data ? Object.entries(row.data).map(([k,v]) => (
                <div key={k} className="flex flex-col">
                  <span className="text-[10px] font-bold uppercase text-[#94A3B8]">{labelMap[k] ?? k.replace(/_/g, " ")}</span>
                  <span className="mt-0.5 text-[12px] font-semibold text-[#0F172A] line-clamp-2">{String(v ?? "—")}</span>
                </div>
              )) : (
                <Badge variant="secondary">No field data</Badge>
              )}
            </div>
            <Button variant="ghost" size="sm" className="mt-3 h-6 text-xs" onClick={() => setOpenId(row.id ?? row.submission_id)}>View full response</Button>
            <Dialog open={openId === (row.id ?? row.submission_id)} onOpenChange={(o) => !o && setOpenId(null)}>
              <DialogContent><DialogHeader><DialogTitle>Full response</DialogTitle></DialogHeader><pre className="text-xs bg-muted p-2 rounded overflow-auto">{JSON.stringify(row.data ?? row, null, 2)}</pre></DialogContent>
            </Dialog>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
