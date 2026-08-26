// Trigger rules (auto Task/Followup/Reminder on form submission) + adhoc
// field proposals with review flow. Version selection via dropdown.

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import {
  useAdhocProposals,
  useCreateAdhocProposal,
  useCreateTriggerRule,
  useDeleteTriggerRule,
  useReviewAdhocProposal,
  useTriggerRules,
  useVersions,
} from "../hooks";
import { adhocProposalSchema, triggerRuleSchema } from "@/schemas/callform.schema";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import FormField from "@/components/forms/FormField";
import PageError from "@/components/common/PageError";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

function VersionSelect({ value, onChange, id, label }) {
  const versionsQuery = useVersions();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">{label}</label>
      <select
        id={id}
        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">Select version…</option>
        {(versionsQuery.data ?? []).map((version) => (
          <option key={version.id} value={version.id}>
            v{version.version_number} ({version.template_details?.name ?? version.template?.slice(0, 8) ?? ""})
          </option>
        ))}
      </select>
    </div>
  );
}

export default function CallFormRulesPage() {
  const [versionId] = useState("");
  const rulesQuery = useTriggerRules(versionId || undefined);
  const createRule = useCreateTriggerRule();
  const deleteRule = useDeleteTriggerRule();

  const ruleForm = useForm({
    resolver: zodResolver(triggerRuleSchema),
    defaultValues: {
      version: "",
      trigger_condition: "ALWAYS",
      task_title_template: "Follow-up with {lead_name}",
      due_days_offset: 1,
      assignee_rule: "CONDUCTING_AGENT",
      create_reminder: true,
    },
  });

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <h1 className="text-2xl font-semibold tracking-tight">Trigger rules</h1>

      <Card>
        <CardHeader><CardTitle className="text-base">New rule</CardTitle></CardHeader>
        <CardContent>
          <form
            className="grid gap-3 md:grid-cols-3"
            onSubmit={ruleForm.handleSubmit((values) =>
              createRule
                .mutateAsync({
                  version: values.version,
                  trigger_condition: values.trigger_condition,
                  task_title_template: values.task_title_template,
                  due_days_offset: Number(values.due_days_offset),
                  assignee_rule: values.assignee_rule,
                  create_reminder: values.create_reminder,
                })
                .then(() => ruleForm.reset()),
            )}
          >
            <div className="md:col-span-3">
              <VersionSelect
                id="rule_version"
                label="Template version"
                value={ruleForm.watch("version")}
                onChange={(value) => ruleForm.setValue("version", value)}
              />
            </div>
            <FormField id="rule_condition" label="Condition" error={ruleForm.formState.errors.trigger_condition?.message}>
              <select
                id="rule_condition"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                {...ruleForm.register("trigger_condition")}
              >
                <option value="ALWAYS">Always</option>
                <option value="FOLLOW_UP_REQUIRED">Follow-up required</option>
                <option value="OUTCOME_MATCH">Outcome match</option>
                <option value="FIELD_VALUE_MATCH">Field value match</option>
              </select>
            </FormField>
            <FormField id="rule_title" label="Task title template" error={ruleForm.formState.errors.task_title_template?.message}>
              <Input id="rule_title" {...ruleForm.register("task_title_template")} />
            </FormField>
            <FormField id="rule_due" label="Due in days" error={ruleForm.formState.errors.due_days_offset?.message}>
              <Input id="rule_due" type="number" min={0} {...ruleForm.register("due_days_offset")} />
            </FormField>
            <label className="flex items-center gap-2 text-sm md:col-span-2">
              <input type="checkbox" className="h-4 w-4" {...ruleForm.register("create_reminder")} />
              Also create a reminder
            </label>
            <Button type="submit" className="self-end" disabled={createRule.isPending}>
              Create rule
            </Button>
          </form>
        </CardContent>
      </Card>

      {rulesQuery.isError ? (
        <PageError error={rulesQuery.error} onRetry={rulesQuery.refetch} />
      ) : (
        <DataTable
          columns={[
            { key: "task_title_template", header: "Task title" },
            {
              key: "trigger_condition",
              header: "Condition",
              render: (row) => <Badge variant="outline">{row.trigger_condition}</Badge>,
            },
            { key: "due_days_offset", header: "Due (days)" },
            { key: "assignee_rule", header: "Assignee" },
            {
              key: "actions",
              header: "",
              render: (row) => (
                <div className="text-right">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-destructive"
                    onClick={() => deleteRule.mutateAsync(row.id)}
                  >
                    Delete
                  </Button>
                </div>
              ),
            },
          ]}
          rows={rulesQuery.data ?? []}
          getRowId={(row) => row.id}
          isLoading={rulesQuery.isLoading}
          emptyState={<EmptyState title="No trigger rules" description={versionId ? undefined : "Pick a template version above to filter."} />}
          page={1}
          pageSize={Math.max((rulesQuery.data ?? []).length, 1)}
          count={(rulesQuery.data ?? []).length}
        />
      )}
    </div>
  );
}

export function AdhocProposalsPage() {
  const proposalsQuery = useAdhocProposals();
  const createProposal = useCreateAdhocProposal();
  const review = useReviewAdhocProposal();

  const proposalForm = useForm({
    resolver: zodResolver(adhocProposalSchema),
    defaultValues: { template_version: "", field_key: "", label: "" },
  });
  const [rejectId, setRejectId] = useState(null);

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <h1 className="text-2xl font-semibold tracking-tight">Ad-hoc field proposals</h1>

      <Card>
        <CardHeader><CardTitle className="text-base">Propose a field</CardTitle></CardHeader>
        <CardContent>
          <form
            className="grid gap-3 md:grid-cols-4"
            onSubmit={proposalForm.handleSubmit((values) =>
              createProposal.mutateAsync(values).then(() => proposalForm.reset()),
            )}
          >
            <div className="md:col-span-2">
              <VersionSelect
                id="adhoc_version"
                label="Template version"
                value={proposalForm.watch("template_version")}
                onChange={(value) => proposalForm.setValue("template_version", value)}
              />
            </div>
            <FormField id="adhoc_key" label="Key" error={proposalForm.formState.errors.field_key?.message}>
              <Input id="adhoc_key" {...proposalForm.register("field_key")} />
            </FormField>
            <FormField id="adhoc_label" label="Label" error={proposalForm.formState.errors.label?.message}>
              <Input id="adhoc_label" {...proposalForm.register("label")} />
            </FormField>
            <Button type="submit" className="self-end" disabled={createProposal.isPending}>
              Submit proposal
            </Button>
          </form>
        </CardContent>
      </Card>

      <DataTable
        columns={[
          {
            key: "field_key",
            header: "Field",
            render: (row) => (
              <span>
                <span className="font-mono text-xs">{row.field_key}</span> — {row.label}
              </span>
            ),
          },
          {
            key: "status",
            header: "Status",
            render: (row) => (
              <Badge variant={row.status === "PENDING" ? "secondary" : row.status === "APPROVED" ? "default" : "destructive"}>
                {row.status.toLowerCase()}
              </Badge>
            ),
          },
          {
            key: "actions",
            header: "Review",
            render: (row) =>
              row.status === "PENDING" ? (
                <div className="flex justify-end gap-1">
                  <Button
                    size="sm"
                    disabled={review.isPending}
                    onClick={() => review.mutateAsync({ proposalId: row.id, status: "APPROVED" })}
                  >
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => setRejectId(row.id)}
                  >
                    Reject…
                  </Button>
                </div>
              ) : null,
          },
        ]}
        rows={proposalsQuery.data ?? []}
        getRowId={(row) => row.id}
        isLoading={proposalsQuery.isLoading}
        emptyState={<EmptyState title="No proposals" />}
        page={1}
        pageSize={Math.max((proposalsQuery.data ?? []).length, 1)}
        count={(proposalsQuery.data ?? []).length}
      />

      <ConfirmRejectDialog rejectId={rejectId} onClose={() => setRejectId(null)} onConfirm={(reason) => review.mutateAsync({ proposalId: rejectId, status: "REJECTED", rejection_reason: reason })} loading={review.isPending} />
    </div>
  );
}

function ConfirmRejectDialog({ rejectId, onClose, onConfirm, loading }) {
  if (!rejectId) return null;
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reject proposal?</DialogTitle>
        </DialogHeader>
        <RejectionForm onClose={onClose} onConfirm={onConfirm} loading={loading} />
      </DialogContent>
    </Dialog>
  );
}

function RejectionForm({ onClose, onConfirm, loading }) {
  const [reason, setReason] = useState("");
  return (
    <form onSubmit={(event) => { event.preventDefault(); onConfirm(reason); }} className="flex flex-col gap-3">
      <FormField id="rejection_reason" label="Reason (optional)">
        <Input id="rejection_reason" value={reason} onChange={(e) => setReason(e.target.value)} />
      </FormField>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
        <Button type="submit" variant="destructive" disabled={loading}>
          {loading ? "Saving…" : "Reject"}
        </Button>
      </DialogFooter>
    </form>
  );
}
