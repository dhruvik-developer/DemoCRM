// Tasks list — server-side visibility (Admin/Manager: all, Employee: own).
// Status/priority names resolve from the G7 workaround constants.

import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { taskPriorityName, taskStatusName } from "@/utils/taskMasterData";
import { useTasks, useDeleteTask } from "../hooks";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Pencil, Trash2 } from "lucide-react";

import { useUsers } from "@/features/admin/hooks";

export default function TasksListPage() {
  const { resolved } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const usersQuery = useUsers();
  const [taskToDelete, setTaskToDelete] = useState(null);
  const deleteTask = useDeleteTask();

  const page = Number(searchParams.get("page") ?? "1");
  const search = searchParams.get("search") ?? "";
  const ordering = searchParams.get("ordering") ?? "";
  const inbox = searchParams.get("inbox") ?? "all"; // all | overdue | today | upcoming

  const updateParam = (key, value) => {
    setSearchParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (value) {
          next.set(key, value);
        } else {
          next.delete(key);
        }
        if (key !== "page") {
          next.delete("page");
        }
        return next;
      },
      { replace: true },
    );
  };

  const tasksQuery = useTasks({
    page,
    search: search || undefined,
    ordering: ordering || undefined,
  });

  let rows = tasksQuery.data?.results ?? [];
  const count = tasksQuery.data?.count ?? 0;
  const canCreate = hasPermission(resolved, "add_task");

  // Inbox filtering client-side per §13 (backend has no overdue/today param)
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const endToday = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  if (inbox === "overdue") rows = rows.filter((t) => t.due_date && new Date(t.due_date) < now);
  else if (inbox === "today") rows = rows.filter((t) => t.due_date && new Date(t.due_date) >= startToday && new Date(t.due_date) < endToday);
  else if (inbox === "upcoming") rows = rows.filter((t) => t.due_date && new Date(t.due_date) >= endToday);

  const findUserName = (assignee) => {
    if (!assignee) return "Unassigned";
    if (typeof assignee === "object") {
      return assignee.full_name || assignee.username || assignee.email;
    }
    const found = (usersQuery.data ?? []).find(
      (u) => String(u.user_id) === String(assignee),
    );
    return found?.full_name || found?.username || `${String(assignee).slice(0, 8)}…`;
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">My Tasks</h1>
        {canCreate ? (
          <Button asChild className="bg-[#2563EB] hover:bg-[#1D4ED8]">
            <Link to="/tasks/new">New task</Link>
          </Button>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {[
          ["all", "All"],
          ["overdue", "Overdue"],
          ["today", "Today"],
          ["upcoming", "Upcoming"],
        ].map(([key, label]) => (
          <Button key={key} variant={inbox === key ? "default" : "outline"} size="sm" onClick={() => updateParam("inbox", key === "all" ? "" : key)} className={inbox === key ? "bg-[#2563EB] hover:bg-[#1D4ED8]" : ""}>
            {label}
          </Button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <Input placeholder="Search tasks…" className="w-64" defaultValue={search} onChange={(event) => updateParam("search", event.target.value.trim())} />
        </div>
      </div>

      {tasksQuery.isError ? (
        <PageError error={tasksQuery.error} onRetry={tasksQuery.refetch} />
      ) : (
        <DataTable
          columns={[
            {
              key: "task_title",
              header: "Title",
              sortable: true,
              render: (task) => {
                const to = task.lead ? `/leads/${task.lead}` : `/tasks/${task.task_id}`;
                const priority = taskPriorityName(task.priority);
                const isHigh = priority?.toLowerCase() === "high";
                return (
                  <div className="flex items-center gap-2">
                    {isHigh ? <span className="h-6 w-1 rounded bg-[#2563EB]" /> : null}
                    <Link to={to} className="font-medium hover:underline">
                      {task.task_title}
                    </Link>
                    {task.lead ? <Badge variant="outline" className="text-[10px]">→ Workspace</Badge> : null}
                  </div>
                );
              },
            },
            {
              key: "status",
              header: "Status",
              render: (task) => (
                <Badge variant="outline">{taskStatusName(task.status)}</Badge>
              ),
            },
            {
              key: "priority",
              header: "Priority",
              render: (task) => {
                const n = taskPriorityName(task.priority);
                return n ? <Badge variant={n.toLowerCase() === "high" ? "destructive" : n.toLowerCase() === "medium" ? "secondary" : "outline"}>{n}</Badge> : "—";
              },
            },
            {
              key: "due_date",
              header: "Due",
              sortable: true,
              render: (task) =>
                task.due_date ? new Date(task.due_date).toLocaleString() : "—",
            },
            {
              key: "assigned_to",
              header: "Assigned to",
              render: (task) => findUserName(task.assigned_to),
            },
            {
              key: "actions",
              header: "",
              render: (task) => {
                const isManagerOrAdmin = Boolean(resolved?.isAdmin || hasPermission(resolved, "assign_task"));
                if (!isManagerOrAdmin) {
                  return null;
                }
                return (
                  <div className="flex items-center justify-end gap-1">
                    <Button asChild variant="ghost" size="sm">
                      <Link to={task.lead ? `/leads/${task.lead}` : `/tasks/${task.task_id}`}>Open →</Link>
                    </Button>
                    <Button asChild variant="ghost" size="icon" className="size-8 text-muted-foreground hover:text-foreground" title="Edit task">
                      <Link to={`/tasks/${task.task_id}`}>
                        <Pencil className="size-4" />
                      </Link>
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-8 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                      title="Delete task"
                      onClick={() => setTaskToDelete(task)}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </div>
                );
              },
            },
          ]}
          rows={rows}
          getRowId={(row) => row.task_id}
          isLoading={tasksQuery.isLoading}
          emptyState={
            <EmptyState
              title="No tasks found"
              description={
                search
                  ? "Try adjusting the search."
                  : canCreate
                    ? "Create your first task."
                    : "Nothing assigned to you yet."
              }
              ctaLabel={canCreate && !search ? "New task" : undefined}
              ctaTo={canCreate ? "/tasks/new" : undefined}
            />
          }
          sortValue={ordering}
          onSortChange={(value) => updateParam("ordering", value)}
          page={page}
          pageSize={10}
          count={count}
          onPageChange={(nextPage) => updateParam("page", String(nextPage))}
        />
      )}

      <ConfirmDialog
        open={Boolean(taskToDelete)}
        onOpenChange={(open) => {
          if (!open) setTaskToDelete(null);
        }}
        title="Delete Task"
        description={`Are you sure you want to delete "${taskToDelete?.task_title}"? This action will remove the task.`}
        confirmLabel="Delete"
        destructive
        loading={deleteTask.isPending}
        onConfirm={async () => {
          if (!taskToDelete) return;
          await deleteTask.mutateAsync(taskToDelete.task_id);
          setTaskToDelete(null);
        }}
      />
    </div>
  );
}
