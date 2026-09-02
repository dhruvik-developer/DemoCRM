// Core CallForms flow: pick a lead → load its stage forms → log a call attempt
// (with duration timer + outcome + auto-followup) → render template fields
// dynamically (radio/checkbox/file/datetime) → submit. Supports multiple
// forms per stage via tabs and role-filtered visibility.

import { useEffect, useMemo, useRef, useState } from "react";
import {
  useLeadPrimaryForm,
  useLeadStageForms,
  useLeadTimeline,
  useLogAttempt,
  useSubmitForm,
  useAttemptHistory,
} from "../hooks";
import LeadSelect from "@/features/leads/components/LeadSelect";
import DynamicFormFields from "../components/DynamicFormFields";
import { validateDynamicData } from "../dynamicFormValidate";
import EmptyState from "@/components/common/EmptyState";
import PageLoader from "@/components/common/PageLoader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const ATTEMPT_OUTCOMES = ["NO_ANSWER", "BUSY", "CONNECTED", "CALLBACK", "WRONG_NUMBER", "DO_NOT_CALL"];

function formatDuration(sec) {
  if (sec == null) return "—";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function Timeline({ leadId }) {
  const timelineQuery = useLeadTimeline(leadId ? { lead_id: leadId } : null);
  if (!leadId || timelineQuery.isLoading || timelineQuery.isError) return null;
  const data = timelineQuery.data;
  const entries = Array.isArray(data) ? data : (data?.timeline ?? data?.results ?? []);
  if (!entries.length) return null;
  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Lead timeline</CardTitle></CardHeader>
      <CardContent className="flex flex-col gap-2">
        {entries.map((entry) => (
          <div key={entry.id ?? entry.timestamp} className="border-b pb-2 text-sm last:border-b-0 last:pb-0">
            <div className="flex items-center gap-2">
              <Badge variant="outline">{entry.entry_type ?? entry.event_type ?? entry.type}</Badge>
              <span className="text-xs text-muted-foreground">
                {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : entry.created_at ? new Date(entry.created_at).toLocaleString() : ""}
              </span>
              {entry.details?.duration_seconds != null ? <span className="text-xs text-muted-foreground">⏱ {formatDuration(entry.details.duration_seconds)}</span> : null}
            </div>
            <p className="text-muted-foreground text-xs mt-1">{entry.actor ? `${entry.actor} — ` : ""}{entry.details?.outcome ?? entry.details?.template_name ?? ""}</p>
            {entry.details?.notes ? <p className="text-xs italic">{entry.details.notes}</p> : null}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function AttemptHistory({ leadId }) {
  const q = useAttemptHistory(leadId);
  if (!leadId || q.isLoading || !q.data?.length) return null;
  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Call log ({q.data.length})</CardTitle></CardHeader>
      <CardContent className="flex flex-col gap-2">
        {q.data.map((a) => (
          <div key={a.id} className="flex items-center justify-between border-b pb-2 text-sm last:border-0">
            <span>#{a.attempt_number} — {a.outcome_display ?? a.outcome} {a.suggest_mark_lost ? <Badge variant="destructive" className="ml-2">suggest lost</Badge> : null}</span>
            <span className="text-xs text-muted-foreground">{a.duration_seconds != null ? formatDuration(a.duration_seconds) : "—"} {a.created_at ? new Date(a.created_at).toLocaleDateString() : ""}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default function CallFormSubmitPage() {
  const [leadId, setLeadId] = useState("");
  const primaryFormQuery = useLeadPrimaryForm(leadId);
  const stageFormsQuery = useLeadStageForms(leadId);
  const logAttempt = useLogAttempt();
  const submitForm = useSubmitForm();

  const [attemptOutcome, setAttemptOutcome] = useState("CONNECTED");
  const [attemptId, setAttemptId] = useState(null);
  const [suggestLost, setSuggestLost] = useState(false);
  const [dynamicData, setDynamicData] = useState({});
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [callNotes, setCallNotes] = useState("");
  const [activeFormIdx, setActiveFormIdx] = useState(0);

  // Call duration timer
  const [timerRunning, setTimerRunning] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [startTime, setStartTime] = useState(null);
  const timerRef = useRef(null);

  // Auto-followup controls
  const [autoFollowup, setAutoFollowup] = useState(true);
  const [callbackDate, setCallbackDate] = useState("");

  const needsCallback = ["NO_ANSWER", "BUSY", "CALLBACK"].includes(attemptOutcome);

  useEffect(() => {
    if (timerRunning) {
      timerRef.current = setInterval(() => setElapsedSec((s) => s + 1), 1000);
    } else if (timerRef.current) clearInterval(timerRef.current);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [timerRunning]);

  const startCall = () => {
    setStartTime(new Date().toISOString());
    setElapsedSec(0);
    setTimerRunning(true);
  };
  const endCall = () => {
    setTimerRunning(false);
  };

  const stageForms = stageFormsQuery.data?.forms ?? [];
  const hasMultiForms = stageForms.length > 1;
  // Prefer multi-form list; fallback to primary single form
  const form = hasMultiForms ? stageForms[activeFormIdx] : primaryFormQuery.data;
  const fields = useMemo(() => (hasMultiForms ? (form?.fields ?? []) : (form?.fields ?? [])), [form, hasMultiForms]);
  const versionLocked = Boolean(form?.template_version?.is_locked);
  const displayForm = hasMultiForms ? form : primaryFormQuery.data;

  // Auto-select defaults when form loads
  useEffect(() => {
    if (!fields.length) return;
    const defaults = {};
    let changed = false;
    for (const f of fields) {
      if (f.validation_rules?.auto_select && f.options?.length && dynamicData[f.field_key] == null) {
        defaults[f.field_key] = f.field_type === "checkbox" ? [String(f.options[0])] : String(f.options[0]);
        changed = true;
      }
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (changed) setDynamicData((prev) => ({ ...defaults, ...prev }));
  }, [fields, dynamicData]);

  const onLogAttempt = async () => {
    const endTime = timerRunning || elapsedSec > 0 ? new Date().toISOString() : null;
    if (timerRunning) setTimerRunning(false);
    try {
      const attempt = await logAttempt.mutateAsync({
        lead_id: leadId,
        stage_id: displayForm?.stage_id ?? primaryFormQuery.data?.stage_id ?? stageFormsQuery.data?.stage_id,
        activity_id: displayForm?.activity?.id ?? primaryFormQuery.data?.activity?.id,
        template_version_id: displayForm?.template_version?.id ?? primaryFormQuery.data?.template_version?.id,
        outcome: attemptOutcome,
        notes: callNotes,
        start_time: startTime,
        end_time: endTime,
        followup_due_date: needsCallback && callbackDate ? new Date(callbackDate).toISOString() : undefined,
        auto_create_followup: needsCallback ? autoFollowup : false,
      });
      setAttemptId(attempt.id);
      setSuggestLost(Boolean(attempt.suggest_mark_lost));
    } catch {
      // Toasted by the mutation.
    }
  };

  const onSubmitForm = async () => {
    const errors = validateDynamicData(fields, dynamicData);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    const tvId = displayForm?.template_version?.id;
    if (!tvId) return;
    try {
      await submitForm.mutateAsync({
        lead_id: leadId,
        template_version_id: tvId,
        call_attempt_id: attemptId ?? undefined,
        data: dynamicData,
      });
      setSubmitted(true);
    } catch {
      // Toasted by the mutation.
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
      <h1 className="text-2xl font-semibold tracking-tight">Log a call & submit form</h1>

      <Card>
        <CardHeader><CardTitle className="text-base">1. Lead</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-3">
          <LeadSelect value={leadId} onChange={(value) => { setLeadId(value); setSubmitted(false); setAttemptId(null); setSuggestLost(false); setDynamicData({}); setActiveFormIdx(0); }} />
          {(primaryFormQuery.isLoading || stageFormsQuery.isLoading) && leadId ? <PageLoader label="Loading forms…" /> : null}
          {leadId && !primaryFormQuery.isLoading && !stageFormsQuery.isLoading && !displayForm ? (
            stageFormsQuery.data?.stage_id ? (
              <EmptyState title="Access restricted — contact your manager" description="Your role is not in allowed_roles for this stage's forms, or no form is linked to the stage." />
            ) : (
              <p className="text-sm text-muted-foreground">No call form is configured for this lead&apos;s current stage.</p>
            )
          ) : null}
          {displayForm ? (
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <Badge variant="outline">{displayForm.activity?.name ?? "Activity"}</Badge>
              {displayForm.activity?.form_type ? <Badge variant="secondary">{displayForm.activity.form_type}</Badge> : null}
              <span className="text-muted-foreground">Template: {displayForm.call_template?.name ?? displayForm.template_version?.version_label ?? "—"}</span>
              {versionLocked ? <Badge variant="destructive">Version locked</Badge> : null}
              {hasMultiForms ? <Badge variant="secondary">{stageForms.length} forms in stage</Badge> : null}
              {displayForm.activity?.editable_roles?.length ? <Badge variant="outline" className="text-[10px]">Editable: {displayForm.activity.editable_roles.join(", ")}</Badge> : null}
            </div>
          ) : null}
        </CardContent>
      </Card>

      {displayForm && !hasMultiForms ? (
        <>
          <Card>
            <CardHeader><CardTitle className="text-base">2. Call — outcome & duration</CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Call outcome">
                {ATTEMPT_OUTCOMES.map((outcome) => (
                  <Button key={outcome} type="button" size="sm" role="radio" aria-checked={attemptOutcome === outcome} aria-label={outcome.replaceAll("_", " ")} variant={attemptOutcome === outcome ? "default" : "outline"} onClick={() => setAttemptOutcome(outcome)}>
                    {outcome.replaceAll("_", " ").toLowerCase()}
                  </Button>
                ))}
              </div>
              <div className="flex items-center gap-3 rounded-md border bg-muted/30 px-3 py-2">
                <span className="text-sm font-mono font-semibold">{formatDuration(elapsedSec)}</span>
                <span className="text-xs text-muted-foreground">{timerRunning ? "● recording" : "idle"}</span>
                <div className="ml-auto flex gap-2">
                  {!timerRunning ? <Button size="sm" variant="outline" onClick={startCall}>Start</Button> : <Button size="sm" variant="outline" onClick={endCall}>Stop</Button>}
                  <Button size="sm" variant="ghost" onClick={() => { setTimerRunning(false); setElapsedSec(0); setStartTime(null); }}>Reset</Button>
                </div>
              </div>
              <Textarea placeholder="Call notes (optional)" value={callNotes} onChange={(e) => setCallNotes(e.target.value)} rows={2} />
              {needsCallback ? (
                <div className="flex flex-col gap-2 rounded-md border bg-amber-50 p-3 dark:bg-amber-950">
                  <label className="flex items-center gap-2 text-sm font-medium">
                    <input type="checkbox" checked={autoFollowup} onChange={(e) => setAutoFollowup(e.target.checked)} className="h-4 w-4" />
                    Auto-create follow-up / callback task
                  </label>
                  {autoFollowup ? (
                    <div className="flex flex-col gap-1">
                      <label className="text-xs text-muted-foreground">Callback date & time (optional — defaults to next business day)</label>
                      <Input type="datetime-local" value={callbackDate} onChange={(e) => setCallbackDate(e.target.value)} />
                    </div>
                  ) : null}
                </div>
              ) : null}
              {!attemptId ? (
                <Button className="w-fit" disabled={logAttempt.isPending || Boolean(primaryFormQuery.data?.template_version?.is_locked)} onClick={onLogAttempt}>
                  {logAttempt.isPending ? "Logging…" : `Log call${needsCallback && autoFollowup ? " & schedule follow-up" : ""}`}
                </Button>
              ) : (
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">Attempt #{attemptId.slice(0, 8)} logged — {formatDuration(elapsedSec)}</Badge>
                  <Button size="sm" variant="ghost" onClick={() => { setAttemptId(null); setSuggestLost(false); }}>Log another</Button>
                </div>
              )}
              {suggestLost ? (
                <p role="alert" className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
                  Multiple consecutive failed attempts — consider marking this lead lost (threshold reached).
                </p>
              ) : null}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="text-base">3. Form</CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-4">
              <DynamicFormFields fields={fields} values={dynamicData} errors={fieldErrors} onChange={setDynamicData} />
              {submitted ? (
                <p className="rounded-md border border-green-300 bg-green-50 px-3 py-2 text-xs text-green-900">Submitted. Attempt marked COMPLETED and lead data synced.</p>
              ) : (
                <Button className="w-fit" disabled={!attemptId || Boolean(primaryFormQuery.data?.template_version?.is_locked) || submitForm.isPending} onClick={onSubmitForm}>
                  {submitForm.isPending ? "Submitting…" : "Submit form"}
                </Button>
              )}
              {!attemptId ? <p className="text-xs text-muted-foreground">Log a call above before submitting the form.</p> : null}
            </CardContent>
          </Card>
          <AttemptHistory leadId={leadId} />
          <Timeline leadId={leadId} />
        </>
      ) : null}

      {hasMultiForms ? (
        <>
          <Card>
            <CardHeader><CardTitle className="text-base">2. Call — outcome & duration</CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Call outcome">
                {ATTEMPT_OUTCOMES.map((outcome) => (
                  <Button key={outcome} type="button" size="sm" role="radio" aria-checked={attemptOutcome === outcome} aria-label={outcome.replaceAll("_", " ")} variant={attemptOutcome === outcome ? "default" : "outline"} onClick={() => setAttemptOutcome(outcome)}>
                    {outcome.replaceAll("_", " ").toLowerCase()}
                  </Button>
                ))}
              </div>
              <div className="flex items-center gap-3 rounded-md border bg-muted/30 px-3 py-2">
                <span className="text-sm font-mono font-semibold">{formatDuration(elapsedSec)}</span>
                <span className="text-xs text-muted-foreground">{timerRunning ? "● recording" : "idle"}</span>
                <div className="ml-auto flex gap-2">
                  {!timerRunning ? <Button size="sm" variant="outline" onClick={startCall}>Start</Button> : <Button size="sm" variant="outline" onClick={endCall}>Stop</Button>}
                  <Button size="sm" variant="ghost" onClick={() => { setTimerRunning(false); setElapsedSec(0); setStartTime(null); }}>Reset</Button>
                </div>
              </div>
              <Textarea placeholder="Call notes (optional)" value={callNotes} onChange={(e) => setCallNotes(e.target.value)} rows={2} />
              {needsCallback ? (
                <div className="flex flex-col gap-2 rounded-md border bg-amber-50 p-3 dark:bg-amber-950">
                  <label className="flex items-center gap-2 text-sm font-medium">
                    <input type="checkbox" checked={autoFollowup} onChange={(e) => setAutoFollowup(e.target.checked)} className="h-4 w-4" />
                    Auto-create follow-up / callback task
                  </label>
                  {autoFollowup ? (
                    <div className="flex flex-col gap-1">
                      <label className="text-xs text-muted-foreground">Callback date & time (optional — defaults to next business day)</label>
                      <Input type="datetime-local" value={callbackDate} onChange={(e) => setCallbackDate(e.target.value)} />
                    </div>
                  ) : null}
                </div>
              ) : null}
              {!attemptId ? (
                <Button className="w-fit" disabled={logAttempt.isPending} onClick={onLogAttempt}>
                  {logAttempt.isPending ? "Logging…" : `Log call${needsCallback && autoFollowup ? " & schedule follow-up" : ""}`}
                </Button>
              ) : (
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">Attempt #{attemptId.slice(0, 8)} logged — {formatDuration(elapsedSec)}</Badge>
                  <Button size="sm" variant="ghost" onClick={() => { setAttemptId(null); setSuggestLost(false); }}>Log another</Button>
                </div>
              )}
              {suggestLost ? (
                <p role="alert" className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
                  Multiple consecutive failed attempts — consider marking this lead lost (threshold reached).
                </p>
              ) : null}
            </CardContent>
          </Card>
          <div className="flex flex-col gap-4">
            {stageForms.map((sf) => {
              const sfFields = sf.fields ?? [];
              const sfLocked = Boolean(sf.template_version?.is_locked);
              const sfErrors = sf.template_version?.id === displayForm?.template_version?.id ? fieldErrors : {};
              const handleSfSubmit = async () => {
                const errs = validateDynamicData(sfFields, dynamicData);
                setFieldErrors(errs);
                if (Object.keys(errs).length) return;
                if (!sf.template_version?.id) return;
                try {
                  await submitForm.mutateAsync({ lead_id: leadId, template_version_id: sf.template_version.id, call_attempt_id: attemptId ?? undefined, data: dynamicData });
                  setSubmitted(true);
                } catch {
                  // handled by toast
                }
              };
              return (
                <Card key={sf.activity.id}>
                  <CardHeader><CardTitle className="text-base">Form — {sf.activity.name} <Badge variant="secondary" className="ml-2">{sf.activity.form_type ?? "CALL"}</Badge> {sf.call_template?.name ? <span className="text-xs font-normal text-muted-foreground ml-2">Template: {sf.call_template.name} {sf.template_version?.version_label} {sfLocked ? "🔒" : ""}</span> : null}</CardTitle></CardHeader>
                  <CardContent className="flex flex-col gap-4">
                    <DynamicFormFields fields={sfFields} values={dynamicData} errors={sfErrors} onChange={setDynamicData} />
                    {submitted ? (
                      <p className="rounded-md border border-green-300 bg-green-50 px-3 py-2 text-xs text-green-900">Submitted.</p>
                    ) : (
                      <Button className="w-fit" disabled={!attemptId || sfLocked || submitForm.isPending} onClick={handleSfSubmit}>
                        {submitForm.isPending ? "Submitting…" : `Submit ${sf.activity.name}`}
                      </Button>
                    )}
                    {!attemptId ? <p className="text-xs text-muted-foreground">Log a call above before submitting.</p> : null}
                  </CardContent>
                </Card>
              );
            })}
          </div>
          <AttemptHistory leadId={leadId} />
          <Timeline leadId={leadId} />
        </>
      ) : null}

      {!leadId ? (
        <div className="flex items-center gap-2">
          <Input placeholder="…or paste a lead UUID" value={leadId} onChange={(event) => setLeadId(event.target.value)} />
        </div>
      ) : null}
    </div>
  );
}
