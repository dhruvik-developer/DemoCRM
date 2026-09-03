import { useEffect, useRef, useState } from "react";
import { useLogAttempt, useAttemptHistory } from "@/features/callforms/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

const OUTCOMES = ["CONNECTED", "NO_ANSWER", "BUSY", "CALLBACK", "COMPLETED", "LOST_SUGGESTED"];

function formatDuration(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(sec % 60).padStart(2, "0");
  return `00:${m}:${s}`;
}

export default function CallAttemptPanel({ leadId, stageId, activityId, templateVersionId }) {
  const attemptsQ = useAttemptHistory(leadId);
  const logAttempt = useLogAttempt();
  const [outcome, setOutcome] = useState("CONNECTED");
  const [notes, setNotes] = useState("");
  const [isLive, setIsLive] = useState(false);
  const [startAt, setStartAt] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef(null);

  const rawAttempts = attemptsQ.data ?? [];
  const attempts = (Array.isArray(rawAttempts) ? rawAttempts : rawAttempts?.results ?? []).filter(Boolean);
  // timeline endpoint returns mixed submissions/attempts; fallback to separate history if needed

  useEffect(() => {
    if (isLive) {
      intervalRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [isLive]);

  const handleStart = () => {
    setStartAt(new Date());
    setElapsed(0);
    setIsLive(true);
  };

  const handleEnd = async () => {
    const endAt = new Date();
    const startISO = startAt ? startAt.toISOString() : new Date(Date.now() - elapsed * 1000).toISOString();
    const endISO = endAt.toISOString();
    setIsLive(false);
    try {
      await logAttempt.mutateAsync({ lead_id: leadId, stage_id: stageId, activity_id: activityId, template_version_id: templateVersionId, outcome, notes: notes || undefined, start_time: startISO, end_time: endISO });
      setNotes("");
      setStartAt(null);
      setElapsed(0);
    } catch (err) {
      void err;
      // keep live state off even on error to avoid stuck timer
      setIsLive(false);
    }
  };

  return (
    <Card className="rounded-[14px] border-[#E2E8F0] shadow-[0_1px_2px_rgba(0,0,0,0.05)] overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold">Call workspace</CardTitle>
          <Badge variant="secondary" className="font-bold">{attempts.length} attempts</Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="rounded-[10px] bg-[#0F172A] text-white p-[10px_16px] flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-[12.5px] font-semibold">
            <span className={`h-2 w-2 rounded-full ${isLive ? "bg-[#10B981] animate-pulse shadow-[0_0_0_4px_rgba(16,185,129,0.25)]" : "bg-[#64748B]"}`} />
            <span>{isLive ? "Active Live Call" : "Live Call"}</span>
            <span className="font-mono text-[13.5px] text-[#94A3B8] ml-2">{isLive ? formatDuration(elapsed) : attempts.length ? `${attempts.length} logged` : "No active call"}</span>
          </div>
          <div className="flex items-center gap-2">
            {!isLive ? (
              <Button size="sm" className="h-7 bg-[#10B981] hover:bg-[#059669] text-white font-semibold" onClick={handleStart}>Start Call</Button>
            ) : (
              <Button size="sm" className="h-7 bg-[#DC2626] hover:bg-[#B91C1C] text-white font-semibold" onClick={handleEnd} disabled={logAttempt.isPending}>End Call{logAttempt.isPending ? "…" : ""}</Button>
            )}
            <Badge className="bg-white/10 text-white border-white/20 text-[11px] hidden sm:inline-flex">Outcome: {outcome}</Badge>
          </div>
        </div>
        <div className="rounded-lg border bg-muted/30 p-3 flex flex-col gap-2">
          <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{isLive ? "During call — set outcome & notes then End Call" : "Log call"}</div>
          <div className="grid gap-2 md:grid-cols-[160px_1fr]">
            <Select value={outcome} onValueChange={setOutcome}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{OUTCOMES.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent>
            </Select>
            <Textarea placeholder="Notes (optional)" value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
          </div>
          {!isLive ? (
            <Button size="sm" className="w-fit bg-[#2563EB] hover:bg-[#1D4ED8]" disabled={logAttempt.isPending}
              onClick={async () => {
                try {
                  await logAttempt.mutateAsync({ lead_id: leadId, stage_id: stageId, activity_id: activityId, template_version_id: templateVersionId, outcome, notes: notes || undefined });
                  setNotes("");
                } catch (err) {
                  void err;
                }
              }}>
              {logAttempt.isPending ? "Logging…" : "Log call"}
            </Button>
          ) : (
            <p className="text-[11px] text-muted-foreground">Timer running • {formatDuration(elapsed)} — click <span className="font-semibold text-[#DC2626]">End Call</span> to save with duration. Outcome and notes will be saved.</p>
          )}
        </div>

        {attemptsQ.isLoading ? <p className="text-sm text-muted-foreground">Loading…</p> : attempts.length ? (
          <div className="flex flex-col gap-1.5">
            {attempts.slice(0,5).map((a, i) => (
              <div key={a.id ?? i} className="flex items-center justify-between rounded border px-3 py-1.5 text-sm">
                <span className="font-medium">{a.outcome ?? "—"} {a.duration_seconds != null ? <span className="ml-1 font-mono text-xs text-muted-foreground">({formatDuration(a.duration_seconds)})</span> : null}</span>
                <span className="text-xs text-muted-foreground">{a.start_time ? new Date(a.start_time).toLocaleString() : ""}</span>
              </div>
            ))}
          </div>
        ) : <p className="text-sm text-muted-foreground">No call attempts yet. Hit Start Call to begin timing.</p>}
      </CardContent>
    </Card>
  );
}
