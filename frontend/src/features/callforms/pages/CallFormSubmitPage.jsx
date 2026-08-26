// Core CallForms flow: pick a lead → load its stage's primary form → log a
// call attempt → render the template fields dynamically → submit.
// A submission marks the attempt COMPLETED and locks that version server-side.

import { useState } from "react";
import {
  useLeadPrimaryForm,
  useLeadTimeline,
  useLogAttempt,
  useSubmitForm,
} from "../hooks";
import LeadSelect from "@/features/leads/components/LeadSelect";
import DynamicFormFields from "../components/DynamicFormFields";
import { validateDynamicData } from "../dynamicFormValidate";
import PageLoader from "@/components/common/PageLoader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const ATTEMPT_OUTCOMES = [
  "NO_ANSWER",
  "BUSY",
  "CONNECTED",
  "CALLBACK",
  "LOST_SUGGESTED",
];

function Timeline({ leadId }) {
  const timelineQuery = useLeadTimeline(leadId ? { lead_id: leadId } : null);
  if (!leadId || timelineQuery.isLoading || timelineQuery.isError) return null;
  const entries = Array.isArray(timelineQuery.data)
    ? timelineQuery.data
    : (timelineQuery.data?.results ?? []);
  if (!entries.length) return null;

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Lead timeline</CardTitle></CardHeader>
      <CardContent className="flex flex-col gap-2">
        {entries.map((entry) => (
          <div key={entry.id ?? entry.timestamp} className="border-b pb-2 text-sm last:border-b-0 last:pb-0">
            <div className="flex items-center gap-2">
              <Badge variant="outline">{entry.event_type ?? entry.type}</Badge>
              <span className="text-xs text-muted-foreground">
                {entry.created_at ? new Date(entry.created_at).toLocaleString() : ""}
              </span>
            </div>
            {entry.summary ? (
              <p className="text-muted-foreground">{entry.summary}</p>
            ) : null}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default function CallFormSubmitPage() {
  const [leadId, setLeadId] = useState("");
  const primaryFormQuery = useLeadPrimaryForm(leadId);
  const logAttempt = useLogAttempt();
  const submitForm = useSubmitForm();

  const [attemptOutcome, setAttemptOutcome] = useState("CONNECTED");
  const [attemptId, setAttemptId] = useState(null);
  const [suggestLost, setSuggestLost] = useState(false);
  const [dynamicData, setDynamicData] = useState({});
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitted, setSubmitted] = useState(false);

  const form = primaryFormQuery.data;
  const fields = form?.fields ?? [];
  const versionLocked = Boolean(form?.template_version?.is_locked);

  const onStartAttempt = async () => {
    try {
      const attempt = await logAttempt.mutateAsync({
        lead_id: leadId,
        stage_id: form?.stage?.id,
        activity_id: form?.activity?.id,
        template_version_id: form?.template_version?.id,
        outcome: attemptOutcome,
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
    try {
      await submitForm.mutateAsync({
        lead_id: leadId,
        template_version_id: form.template_version.id,
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
          <LeadSelect value={leadId} onChange={(value) => { setLeadId(value); setSubmitted(false); setAttemptId(null); setSuggestLost(false); }} />
          {primaryFormQuery.isLoading && leadId ? <PageLoader label="Loading primary form…" /> : null}
          {leadId && !primaryFormQuery.isLoading && !form ? (
            <p className="text-sm text-muted-foreground">
              No primary call form is configured for this lead's current stage.
            </p>
          ) : null}
          {form ? (
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <Badge variant="outline">{form.activity?.name ?? "Activity"}</Badge>
              <span className="text-muted-foreground">
                Template: {form.call_template?.name ?? form.template_version?.version_label ?? "—"}
              </span>
              {versionLocked ? (
                <Badge variant="destructive">Version locked (has submissions)</Badge>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>

      {form ? (
        <>
          <Card>
            <CardHeader><CardTitle className="text-base">2. Attempt outcome</CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-3">
              <div className="flex flex-wrap gap-2">
                {ATTEMPT_OUTCOMES.map((outcome) => (
                  <Button
                    key={outcome}
                    type="button"
                    size="sm"
                    variant={attemptOutcome === outcome ? "default" : "outline"}
                    onClick={() => setAttemptOutcome(outcome)}
                  >
                    {outcome.replaceAll("_", " ").toLowerCase()}
                  </Button>
                ))}
              </div>
              {!attemptId ? (
                <Button className="w-fit" disabled={logAttempt.isPending || versionLocked} onClick={onStartAttempt}>
                  {logAttempt.isPending ? "Logging…" : "Start attempt"}
                </Button>
              ) : (
                <Badge variant="secondary">Attempt logged</Badge>
              )}
              {suggestLost ? (
                <p role="alert" className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
                  Multiple consecutive failed attempts — consider marking this lead lost
                  (threshold reached). Suggestion only; use the Lead → Mark lost action to confirm.
                </p>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">3. Form</CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-4">
              <DynamicFormFields fields={fields} values={dynamicData} onChange={setDynamicData} />
              {Object.entries(fieldErrors).map(([key, message]) => (
                <p key={key} role="alert" className="text-xs text-destructive">{message}</p>
              ))}
              {submitted ? (
                <p className="rounded-md border border-green-300 bg-green-50 px-3 py-2 text-xs text-green-900 dark:border-green-800 dark:bg-green-950 dark:text-green-200">
                  Submitted. The attempt was marked COMPLETED and this version is now locked.
                </p>
              ) : (
                <Button
                  className="w-fit"
                  disabled={!attemptId || versionLocked || submitForm.isPending}
                  onClick={onSubmitForm}
                >
                  {submitForm.isPending ? "Submitting…" : "Submit form"}
                </Button>
              )}
            </CardContent>
          </Card>

          <Timeline leadId={leadId} />
        </>
      ) : null}

      {/* Manual ID fallback for environments without the leads list */}
      {!leadId ? (
        <div className="flex items-center gap-2">
          <Input
            placeholder="…or paste a lead UUID"
            value={leadId}
            onChange={(event) => setLeadId(event.target.value)}
          />
        </div>
      ) : null}
    </div>
  );
}
