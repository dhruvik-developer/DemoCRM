import { useState } from "react";
import { useLogAttempt, useLeadTimeline } from "@/features/callforms/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

const OUTCOMES = ["CONNECTED", "NO_ANSWER", "BUSY", "CALLBACK", "COMPLETED", "LOST_SUGGESTED"];

export default function CallAttemptPanel({ leadId, stageId, activityId, templateVersionId }) {
  const timelineQ = useLeadTimeline({ lead_id: leadId });
  const logAttempt = useLogAttempt();
  const [outcome, setOutcome] = useState("CONNECTED");
  const [notes, setNotes] = useState("");
  const rawAttempts =
    timelineQ.data?.call_attempts ??
    timelineQ.data?.attempts ??
    (Array.isArray(timelineQ.data) ? timelineQ.data : timelineQ.data?.results ?? []);
  const attempts = Array.isArray(rawAttempts) ? rawAttempts.filter(Boolean) : [];
  // timeline endpoint returns mixed submissions/attempts; fallback to separate history if needed

  return (
    <Card className="rounded-xl">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Call workspace</CardTitle>
          <Badge variant="secondary">{attempts.length} attempts</Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="rounded-lg border bg-muted/30 p-3 flex flex-col gap-2">
          <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Log call</div>
          <div className="grid gap-2 md:grid-cols-[160px_1fr]">
            <Select value={outcome} onValueChange={setOutcome}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{OUTCOMES.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent>
            </Select>
            <Textarea placeholder="Notes (optional)" value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
          </div>
          <Button size="sm" className="w-fit bg-[#2563EB] hover:bg-[#1D4ED8]" disabled={logAttempt.isPending}
            onClick={async () => {
              try {
                await logAttempt.mutateAsync({ lead_id: leadId, stage_id: stageId, activity_id: activityId, template_version_id: templateVersionId, outcome, notes: notes || undefined });
                setNotes("");
              } catch (err) {
                // error handled by mutation toast
                void err;
              }
            }}>
            {logAttempt.isPending ? "Logging…" : "Log call"}
          </Button>
        </div>

        {timelineQ.isLoading ? <p className="text-sm text-muted-foreground">Loading…</p> : attempts.length ? (
          <div className="flex flex-col gap-1.5">
            {attempts.slice(0,5).map((a, i) => (
              <div key={a.id ?? i} className="flex items-center justify-between rounded border px-3 py-1.5 text-sm">
                <span className="font-medium">{a.outcome ?? "—"}</span>
                <span className="text-xs text-muted-foreground">{a.start_time ? new Date(a.start_time).toLocaleString() : ""}</span>
              </div>
            ))}
          </div>
        ) : <p className="text-sm text-muted-foreground">No call attempts yet.</p>}
      </CardContent>
    </Card>
  );
}
