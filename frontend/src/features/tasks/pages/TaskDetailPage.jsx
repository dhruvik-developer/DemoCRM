// Task detail: info card + Assign / Status / soft-Delete actions, each gated
// on its codename. Employees can only act on their own tasks (server-side).

import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { taskPriorityName, taskStatusName, TASK_STATUSES } from "@/utils/taskMasterData";
import { toast } from "sonner";
import { useLead, useProgressLead } from "@/features/leads/hooks";
import { useLeadPrimaryForm, useLogAttempt, useSubmitForm } from "@/features/callforms/hooks";
import DynamicFormFields from "@/features/callforms/components/DynamicFormFields";
import { useMasterDataMaps, usePipelineStages } from "@/features/crm/hooks";
import { useAssignTask, useDeleteTask, useTask, useUpdateTaskStatus } from "../hooks";
import { useUsers } from "@/features/admin/hooks";
import PageError from "@/components/common/PageError";
import PageLoader from "@/components/common/PageLoader";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import FormField from "@/components/forms/FormField";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function Field({ label, value }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className="text-sm">{value ?? "—"}</span>
    </div>
  );
}

function TaskCallWorkspace({ task, updateStatus }) {
  const leadId = task.lead;
  const leadQuery = useLead(leadId);
  const primaryFormQuery = useLeadPrimaryForm(leadId);
  const submitForm = useSubmitForm();
  const logAttempt = useLogAttempt();
  const progressLead = useProgressLead(leadId);
  const masterData = useMasterDataMaps();

  const stagesQuery = usePipelineStages(leadQuery.data?.pipeline);

  const [formValues, setFormValues] = useState({});
  const [fieldErrors, setFieldErrors] = useState({});

  const lead = leadQuery.data;
  const formData = primaryFormQuery.data;
  const customFields = formData?.fields ?? [];

  // Calculate next stage in pipeline
  const stages = stagesQuery.data ?? [];
  const currentStageIndex = stages.findIndex((st) => st.id === lead?.current_stage);
  const nextStage = currentStageIndex >= 0 ? stages[currentStageIndex + 1] : null;

  if (!leadId) return null;
  if (leadQuery.isLoading || primaryFormQuery.isLoading) {
    return (
      <Card>
        <CardContent className="py-6 text-center text-sm text-muted-foreground">
          Loading Call Workspace & Form Data…
        </CardContent>
      </Card>
    );
  }

  // Define default fallback fields if no custom form is assigned to current stage
  const fallbackFields = [
    {
      field_key: "call_outcome",
      label: "Step 1 — Call Outcome",
      field_type: "select",
      is_required: true,
      options: [
        "Call Connected - Interested",
        "Proposal Requested",
        "Follow-up Required",
        "Call Busy / No Answer",
        "Not Interested",
      ],
      step: 1,
    },
    {
      field_key: "client_feedback",
      label: "Step 1 — Client Feedback & Requirements",
      field_type: "textarea",
      is_required: false,
      placeholder: "Record client requirements and call notes during the call...",
      step: 1,
    },
    {
      field_key: "proposed_value",
      label: "Step 2 — Proposed Deal Value / Quotation Amount",
      field_type: "number",
      is_required: false,
      placeholder: "e.g. 50000.00",
      step: 2,
    },
    {
      field_key: "agreed_next_action",
      label: "Step 2 — Agreed Next Step / Meeting Date",
      field_type: "text",
      is_required: false,
      placeholder: "e.g. Send formal quotation tomorrow at 2 PM",
      step: 2,
    },
  ];

  const activeFields = customFields.length > 0 ? customFields : fallbackFields;

  const handleSaveForm = async (e) => {
    if (e) e.preventDefault();
    setFieldErrors({});

    const errors = {};
    for (const field of activeFields) {
      if (field.is_required && !formValues[field.field_key]) {
        errors[field.field_key] = `${field.label} is required.`;
      }
    }
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      toast.error("Please complete required form fields.");
      return false;
    }

    const versionId =
      formData?.template_version?.id ||
      formData?.template_version_id ||
      formData?.id;

    try {
      if (versionId) {
        await submitForm.mutateAsync({
          lead_id: leadId,
          template_version_id: versionId,
          data: formValues,
        });
      } else {
        await logAttempt.mutateAsync({
          lead_id: leadId,
          notes: JSON.stringify(formValues),
          outcome: formValues.call_outcome || "COMPLETED",
        });
      }
      toast.success("Call form responses saved!");
      return true;
    } catch {
      return false;
    }
  };

  const handleCompleteTask = async () => {
    const saved = await handleSaveForm();
    if (!saved && activeFields.some((f) => f.is_required)) return;

    try {
      const completedStatus = TASK_STATUSES.find(
        (s) => s.name.toLowerCase() === "completed",
      )?.id ?? 3;
      await updateStatus.mutateAsync(completedStatus);
      toast.success("Task marked as Completed!");
    } catch {
      // handled by mutation
    }
  };

  const handleMoveToNextStage = async () => {
    if (!nextStage) {
      toast.info("Lead is already at the final pipeline stage.");
      return;
    }

    const saved = await handleSaveForm();
    if (!saved && activeFields.some((f) => f.is_required)) return;

    try {
      await progressLead.mutateAsync(nextStage.id);
      // Mark task as completed
      const completedStatus = TASK_STATUSES.find(
        (s) => s.name.toLowerCase() === "completed",
      )?.id ?? 3;
      await updateStatus.mutateAsync(completedStatus);
      toast.success(`Submitted! Lead progressed to stage "${nextStage.name}".`);
    } catch {
      // handled by mutation
    }
  };

  return (
    <Card className="border-primary/40 bg-card shadow-md">
      <CardHeader className="border-b bg-muted/20 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <span>Call Workspace — {lead?.name || "Assigned Lead"}</span>
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Active Call Form Steps & Lead Information for live data entry.
            </p>
          </div>
          <Badge variant="default" className="text-xs">
            Current Stage: {masterData.stageName(lead?.current_stage) || "Lead Active"}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-6 pt-5">
        {/* Lead Basic Info Header Bar */}
        {lead ? (
          <div className="grid gap-3 rounded-lg border bg-muted/30 p-4 text-sm md:grid-cols-4">
            <div>
              <span className="text-xs font-medium uppercase text-muted-foreground">Phone</span>
              <p className="font-semibold text-foreground">{lead.phone || "—"}</p>
            </div>
            <div>
              <span className="text-xs font-medium uppercase text-muted-foreground">Email</span>
              <p className="font-semibold text-foreground">{lead.email || "—"}</p>
            </div>
            <div>
              <span className="text-xs font-medium uppercase text-muted-foreground">Company</span>
              <p className="font-semibold text-foreground">{lead.company_name || "—"}</p>
            </div>
            <div>
              <span className="text-xs font-medium uppercase text-muted-foreground">Pipeline / Stage</span>
              <p className="font-semibold text-foreground">
                {masterData.pipelineName(lead.pipeline) || "Sales"} / {masterData.stageName(lead.current_stage) || "Stage"}
              </p>
            </div>
          </div>
        ) : null}

        {/* Step-by-Step Interactive Call Form */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">
              Call Form Steps — {formData?.template_name || masterData.stageName(lead?.current_stage) || "Initial Contact"}
            </h3>
            {nextStage ? (
              <Badge variant="outline" className="text-xs">
                Next Step: {nextStage.name}
              </Badge>
            ) : null}
          </div>

          <DynamicFormFields
            fields={activeFields}
            values={formValues}
            errors={fieldErrors}
            onChange={setFormValues}
            stepView={true}
          />
        </div>

        {/* Live Action Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t">
          <Button
            type="button"
            variant="outline"
            disabled={submitForm.isPending}
            onClick={handleSaveForm}
          >
            {submitForm.isPending ? "Saving Form Data…" : "Save Form Answers"}
          </Button>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              disabled={updateStatus.isPending}
              onClick={handleCompleteTask}
            >
              {updateStatus.isPending ? "Completing Task…" : "Complete Task"}
            </Button>

            {nextStage ? (
              <Button
                type="button"
                disabled={progressLead.isPending || updateStatus.isPending || submitForm.isPending}
                onClick={handleMoveToNextStage}
              >
                {progressLead.isPending ? "Moving Stage…" : `Submit & Move to ${nextStage.name} →`}
              </Button>
            ) : null}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function AssignDialog({ taskId, open, onOpenChange }) {
  const assignTask = useAssignTask(taskId);
  const usersQuery = useUsers();
  const [selectedUser, setSelectedUser] = useState("");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign task to employee</DialogTitle>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!selectedUser) return;
            assignTask.mutateAsync(selectedUser).then(() => onOpenChange(false));
          }}
          className="flex flex-col gap-4"
        >
          <FormField id="assigned_to" label="Select Employee" required>
            <Select value={selectedUser} onValueChange={setSelectedUser}>
              <SelectTrigger>
                <SelectValue placeholder="Select Employee…" />
              </SelectTrigger>
              <SelectContent>
                {(usersQuery.data ?? []).map((user) => (
                  <SelectItem key={user.user_id} value={user.user_id}>
                    {user.full_name || user.username} {user.role ? `(${user.role})` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!selectedUser || assignTask.isPending}>
              {assignTask.isPending ? "Assigning…" : "Assign task"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function TaskDetailPage() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { resolved } = useAuth();
  const taskQuery = useTask(taskId);
  const usersQuery = useUsers();

  const [assignOpen, setAssignOpen] = useState(false);
  const [statusValue, setStatusValue] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const updateStatus = useUpdateTaskStatus(taskId);
  const deleteTask = useDeleteTask(taskId);

  if (taskQuery.isLoading) return <PageLoader label="Loading task…" />;
  if (taskQuery.isError) {
    return <PageError error={taskQuery.error} onRetry={taskQuery.refetch} />;
  }

  const task = taskQuery.data;
  const can = (codename) => hasPermission(resolved, codename);
  const selectedStatus = statusValue || String(task.status ?? "");

  const assignedUser = (usersQuery.data ?? []).find(
    (u) => String(u.user_id) === String(task.assigned_to),
  );
  const assignedName = assignedUser
    ? `${assignedUser.full_name || assignedUser.username} (${assignedUser.role || "Employee"})`
    : task.assigned_to
      ? `${String(task.assigned_to).slice(0, 8)}…`
      : "Unassigned";

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">{task.task_title}</h1>
          <Badge variant="outline">{taskStatusName(task.status)}</Badge>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {can("assign_task") ? (
            <Button variant="outline" size="sm" onClick={() => setAssignOpen(true)}>
              Assign
            </Button>
          ) : null}
          {can("change_taskstatus") ? (
            <div className="flex items-center gap-2">
              <Select value={selectedStatus} onValueChange={setStatusValue}>
                <SelectTrigger className="w-36">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TASK_STATUSES.map((option) => (
                    <SelectItem key={option.id} value={String(option.id)}>
                      {option.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                size="sm"
                disabled={!statusValue || Number(statusValue) === task.status || updateStatus.isPending}
                onClick={() => updateStatus.mutateAsync(Number(statusValue))}
              >
                {updateStatus.isPending ? "Saving…" : "Update status"}
              </Button>
            </div>
          ) : null}
          {can("delete_task") ? (
            <Button variant="destructive" size="sm" onClick={() => setDeleteOpen(true)}>
              Delete
            </Button>
          ) : null}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <Field label="Priority" value={taskPriorityName(task.priority)} />
          <Field label="Category" value={String(task.category ?? "—")} />
          <Field
            label="Due date"
            value={task.due_date ? new Date(task.due_date).toLocaleString() : null}
          />
          <Field label="Assigned to" value={assignedName} />
          {task.lead ? (
            <div className="flex flex-col gap-1">
              <span className="text-xs uppercase tracking-wide text-muted-foreground">Lead</span>
              {can("view_lead") ? (
                <Link to={`/leads/${task.lead}`} className="text-sm hover:underline">
                  View lead
                </Link>
              ) : (
                <span className="text-sm text-foreground">Assigned Lead</span>
              )}
            </div>
          ) : null}
        </CardContent>
      </Card>

      {task.description ? (
        <Card>
          <CardHeader>
            <CardTitle>Description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm">{task.description}</p>
          </CardContent>
        </Card>
      ) : null}

      <TaskCallWorkspace task={task} updateStatus={updateStatus} />

      <p className="text-sm text-muted-foreground">
        Meetings, follow-ups and reminders for this task arrive with Phases 10–11.
      </p>

      <Link to="/tasks" className="text-sm text-muted-foreground hover:underline">
        ← Back to tasks
      </Link>

      <AssignDialog taskId={taskId} open={assignOpen} onOpenChange={setAssignOpen} />

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete this task?"
        description="Tasks are soft-deleted (deactivated), not permanently removed."
        confirmLabel="Delete"
        destructive
        loading={deleteTask.isPending}
        onConfirm={() =>
          deleteTask.mutateAsync().then(() => {
            setDeleteOpen(false);
            navigate("/tasks");
          })
        }
      />
    </div>
  );
}
