// Task detail: info card + Assign / Status / soft-Delete actions, each gated
// on its codename. Employees can only act on their own tasks (server-side).

import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { taskPriorityName, taskStatusName, TASK_STATUSES } from "@/utils/taskMasterData";
import { useAssignTask, useDeleteTask, useTask, useUpdateTaskStatus } from "../hooks";
import { assignTaskSchema } from "@/schemas/task.schema";
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

function AssignDialog({ taskId, open, onOpenChange }) {
  const assignTask = useAssignTask(taskId);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: zodResolver(assignTaskSchema) });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign task</DialogTitle>
        </DialogHeader>
        {/* G6: manual UUID until a user-list endpoint exists. */}
        <form
          onSubmit={handleSubmit((values) =>
            assignTask.mutateAsync(values.assigned_to).then(() => onOpenChange(false)),
          )}
        >
          <FormField
            id="assigned_to"
            label="User UUID"
            error={errors.assigned_to?.message}
            help="A searchable user picker will replace this once the backend ships GET /users/."
          >
            <input
              id="assigned_to"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              placeholder="00000000-0000-4000-8000-…"
              {...register("assigned_to")}
            />
          </FormField>
          <DialogFooter className="mt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={assignTask.isPending}>
              {assignTask.isPending ? "Assigning…" : "Assign"}
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
          <Field label="Assigned to" value={task.assigned_to ? `${String(task.assigned_to).slice(0, 8)}…` : null} />
          {task.lead ? (
            <div className="flex flex-col gap-1">
              <span className="text-xs uppercase tracking-wide text-muted-foreground">Lead</span>
              <Link to={`/leads/${task.lead}`} className="text-sm hover:underline">
                View lead
              </Link>
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
