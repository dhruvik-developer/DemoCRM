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
    <Card className="rounded-xl">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Form response history</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {submissions.slice(0, 10).map((row) => (
          <div key={row.id ?? row.submission_id} className="rounded-lg border bg-card p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {row.template_name ?? row.template_version ?? "Submission"} · {row.version_label ?? ""}
              </span>
              <span className="text-xs text-muted-foreground">{row.submitted_at ? new Date(row.submitted_at).toLocaleString() : row.created_at ? new Date(row.created_at).toLocaleString() : ""}</span>
            </div>
            {row.submitted_by_name || row.submitted_by ? (
              <div className="mt-1 text-xs text-muted-foreground">Submitted by {row.submitted_by_name ?? String(row.submitted_by).slice(0,8)}</div>
            ) : null}
            <div className="mt-2 grid gap-1 text-sm">
              {row.data ? Object.entries(row.data).map(([k,v]) => (
                <div key={k} className="flex justify-between gap-2">
                  <span className="font-medium text-muted-foreground">{labelMap[k] ?? k.replace(/_/g, " ")}</span>
                  <span className="font-medium">{String(v ?? "—")}</span>
                </div>
              )) : (
                <Badge variant="secondary">No field data</Badge>
              )}
            </div>
            <Button variant="ghost" size="sm" className="mt-2 h-6 text-xs" onClick={() => setOpenId(row.id ?? row.submission_id)}>View full response</Button>
            <Dialog open={openId === (row.id ?? row.submission_id)} onOpenChange={(o) => !o && setOpenId(null)}>
              <DialogContent><DialogHeader><DialogTitle>Full response</DialogTitle></DialogHeader><pre className="text-xs bg-muted p-2 rounded overflow-auto">{JSON.stringify(row.data ?? row, null, 2)}</pre></DialogContent>
            </Dialog>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
