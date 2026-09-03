// Tasks list — server-side visibility (Admin/Manager: all, Employee: own).
// Status/priority names resolve from the G7 workaround constants.

import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { TASK_STATUSES, taskPriorityName, taskStatusName } from "@/utils/taskMasterData";
import { useTasks, useDeleteTask, useTaskKpi, useUpdateTaskStatus } from "../hooks";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageSquareText, Pencil, Pin, Trash2, CheckSquare, Clock, CalendarClock, CalendarRange, Flag, ListTodo } from "lucide-react";
import RecordNotesPanel from "@/features/notes/components/RecordNotesPanel";
import ListControls from "@/components/common/ListControls";
import { usePinnedRecords } from "@/hooks/usePinnedRecords";

import { useUsers } from "@/features/admin/hooks";

function KpiCard({ title, value, loading, icon: Icon, to }) {
  return (
    <Card className="rounded-xl">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {loading ? <Skeleton className="h-7 w-12" /> : <div className="text-2xl font-bold">{value ?? "—"}</div>}
        {to ? <Link to={to} className="text-xs text-[#2563EB] hover:underline">View →</Link> : null}
      </CardContent>
    </Card>
  );
}

function EmployeeTaskStatusSelect({ task }) {
  const updateStatus = useUpdateTaskStatus(task.task_id);

  return (
    <Select
      value={String(task.status ?? "")}
      disabled={updateStatus.isPending}
      onValueChange={(value) => updateStatus.mutate(Number(value))}
    >
      <SelectTrigger
        className="h-8 w-32"
        aria-label={`Update status for ${task.task_title}`}
        onClick={(event) => event.stopPropagation()}
      >
        <SelectValue placeholder="Select status" />
      </SelectTrigger>
      <SelectContent>
        {TASK_STATUSES.map((status) => (
          <SelectItem key={status.id} value={String(status.id)}>
            {status.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export default function TasksListPage() {
  const navigate = useNavigate();
  const { resolved } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const usersQuery = useUsers();
  const [taskToDelete, setTaskToDelete] = useState(null);
  const [notesRecord, setNotesRecord] = useState(null);
  const deleteTask = useDeleteTask();
  const kpi = useTaskKpi();

  const page = Number(searchParams.get("page") ?? "1");
  const search = searchParams.get("search") ?? "";
  const ordering = searchParams.get("ordering") ?? "";
  const inbox = searchParams.get("inbox") ?? "all"; // all | overdue | today | upcoming | completed
  const pinnedOnly = searchParams.get("pinned") === "1";
  const pins = usePinnedRecords("crm:pinned-tasks");

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
    page: pinnedOnly ? 1 : page,
    page_size: pinnedOnly ? 100 : 10,
    search: search || undefined,
    ordering: ordering || undefined,
  });

  let rows = tasksQuery.data?.results ?? [];
  let count = tasksQuery.data?.count ?? 0;
  const canCreate = hasPermission(resolved, "add_task");

  // Inbox filtering client-side per §13 (backend has no overdue/today param)
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const endToday = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  if (inbox === "overdue") rows = rows.filter((t) => t.due_date && new Date(t.due_date) < now && taskStatusName(t.status)?.toLowerCase() !== "completed");
  else if (inbox === "today") rows = rows.filter((t) => t.due_date && new Date(t.due_date) >= startToday && new Date(t.due_date) < endToday);
  else if (inbox === "upcoming") rows = rows.filter((t) => t.due_date && new Date(t.due_date) >= endToday);
  else if (inbox === "completed") rows = rows.filter((t) => taskStatusName(t.status)?.toLowerCase() === "completed");
  if (pinnedOnly) rows = rows.filter((task) => pins.isPinned(task.task_id));
  rows = pins.pinnedFirst(rows, (task) => task.task_id);
  if (pinnedOnly) count = rows.length;

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

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard title="Total tasks" value={kpi.data?.total} loading={kpi.isLoading} icon={ListTodo} />
        <KpiCard title="Open" value={kpi.data?.open} loading={kpi.isLoading} icon={CheckSquare} />
        <KpiCard title="Overdue" value={kpi.data?.overdue} loading={kpi.isLoading} icon={Clock} to="/tasks?inbox=overdue" />
        <KpiCard title="Due today" value={kpi.data?.today} loading={kpi.isLoading} icon={CalendarClock} to="/tasks?inbox=today" />
        <KpiCard title="Upcoming" value={kpi.data?.upcoming} loading={kpi.isLoading} icon={CalendarRange} to="/tasks?inbox=upcoming" />
        <KpiCard title="Completed" value={kpi.data?.completed} loading={kpi.isLoading} icon={CheckSquare} to="/tasks?inbox=completed" />
        <KpiCard title="High priority" value={kpi.data?.high_priority} loading={kpi.isLoading} icon={Flag} />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {[
          ["all", "All"],
          ["overdue", "Overdue"],
          ["today", "Today"],
          ["upcoming", "Upcoming"],
          ["completed", "Completed"],
        ].map(([key, label]) => (
          <Button key={key} variant={inbox === key ? "default" : "outline"} size="sm" onClick={() => updateParam("inbox", key === "all" ? "" : key)} className={inbox === key ? "bg-[#2563EB] hover:bg-[#1D4ED8]" : ""}>
            {label}
          </Button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <Input placeholder="Search tasks…" className="w-64" defaultValue={search} onChange={(event) => updateParam("search", event.target.value.trim())} />
        </div>
        <ListControls
          filterValue={inbox}
          filterOptions={[["all", "All tasks"], ["overdue", "Overdue"], ["today", "Due today"], ["upcoming", "Upcoming"], ["completed", "Completed"]].map(([value, label]) => ({ value, label }))}
          onFilterChange={(value) => updateParam("inbox", value === "all" ? "" : value)}
          sortValue={ordering}
          sortOptions={[{ value: "due_date", label: "Due date: oldest first" }, { value: "-due_date", label: "Due date: newest first" }, { value: "task_title", label: "Title: A–Z" }, { value: "-task_title", label: "Title: Z–A" }]}
          onSortChange={(value) => updateParam("ordering", value)}
          pinnedOnly={pinnedOnly}
          onPinnedOnlyChange={(value) => updateParam("pinned", value ? "1" : "")}
        />
      </div>

      {tasksQuery.isError ? (
        <PageError error={tasksQuery.error} onRetry={tasksQuery.refetch} />
      ) : (
        <DataTable
          columns={[
            {
              key: "pin",
              header: "",
              className: "w-10",
              render: (task) => <Button variant="ghost" size="icon-sm" title={pins.isPinned(task.task_id) ? "Unpin task" : "Pin task"} aria-label={pins.isPinned(task.task_id) ? "Unpin task" : "Pin task"} onClick={() => pins.togglePin(task.task_id)}><Pin className={pins.isPinned(task.task_id) ? "fill-primary text-primary" : "text-muted-foreground"} /></Button>,
            },
            {
              key: "task_title",
              header: "Title",
              sortable: true,
              render: (task) => {
                const priority = taskPriorityName(task.priority);
                const isHigh = priority?.toLowerCase() === "high";
                return (
                  <div className="flex items-center gap-2">
                    {isHigh ? <span className="h-6 w-1 rounded bg-[#2563EB]" /> : null}
                    <Link to={`/tasks/${task.task_id}`} className="font-medium hover:underline">
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
              render: (task) => <EmployeeTaskStatusSelect task={task} />,
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
              key: "notes",
              header: "Notes",
              className: "w-16",
              render: (task) => <Button variant="ghost" size="icon-sm" title="Add note" aria-label={`Notes for ${task.task_title}`} onClick={() => setNotesRecord({ type: "task", id: task.task_id, title: task.task_title })}><MessageSquareText /></Button>,
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
                      <Link to={`/tasks/${task.task_id}`}>Open →</Link>
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
          onRowClick={(task) => navigate(`/tasks/${task.task_id}`)}
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
          page={pinnedOnly ? 1 : page}
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
      <RecordNotesPanel record={notesRecord} onClose={() => setNotesRecord(null)} />
    </div>
  );
}
