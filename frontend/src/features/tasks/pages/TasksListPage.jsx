// Tasks list — server-side visibility (Admin/Manager: all, Employee: own).
// Status/priority names resolve from the G7 workaround constants.

import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  CheckCircle2,
  CheckSquare,
  Clock,
  Plus,
  Search,
  UserCheck,
  MessageSquareText,
  Pencil,
  Pin,
  Trash2,
  CalendarClock,
  CalendarRange,
  Flag,
  ListTodo,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { TASK_STATUSES, taskPriorityName, taskStatusName } from "@/utils/taskMasterData";
import { useTasks, useDeleteTask, useTaskKpi, useUpdateTaskStatus } from "../hooks";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import RecordNotesPanel from "@/features/notes/components/RecordNotesPanel";
import ListControls from "@/components/common/ListControls";
import { usePinnedRecords } from "@/hooks/usePinnedRecords";

import { useUsers } from "@/features/admin/hooks";

const INBOX_TABS = [
  { key: "all", label: "All", icon: ListTodo },
  { key: "overdue", label: "Overdue", icon: Clock },
  { key: "today", label: "Today", icon: CalendarClock },
  { key: "upcoming", label: "Upcoming", icon: CalendarRange },
  { key: "completed", label: "Completed", icon: CheckCircle2 },
];

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

function TaskStatusCell({ task, isManagerOrAdmin }) {
  if (!isManagerOrAdmin) {
    return <EmployeeTaskStatusSelect task={task} />;
  }
  const s = taskStatusName(task.status) || "Pending";
  const isDone = s.toLowerCase() === "completed";
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
        isDone
          ? "bg-success-soft text-success border-success-border"
          : "bg-surface-container text-muted-foreground border-border"
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${isDone ? "bg-success" : "bg-muted-foreground"}`} />
      {s}
    </span>
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
  const isManagerOrAdmin = Boolean(resolved?.isAdmin || hasPermission(resolved, "assign_task"));

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
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6 p-6 lg:p-8">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-[28px] font-extrabold tracking-tight text-[#113D37] dark:text-[#E8F0E9]">Tasks & Follow-ups</h1>
          <p className="text-[13px] text-muted-foreground mt-0.5">Manage assignments, track deadlines, and maintain pipeline momentum.</p>
        </div>
        {canCreate ? (
          <Button asChild className="bg-[#FF6A3D] text-[#2B1206] hover:bg-[#E0532A] hover:text-white rounded-[9px] font-semibold">
            <Link to="/tasks/new"><Plus className="h-4 w-4 mr-1" /> New task</Link>
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

      {/* Toolbar: Filter Tabs & Search */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5">
          {INBOX_TABS.map(({ key, label, icon: Icon }) => {
            const isActive = (inbox === "all" && key === "all") || inbox === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => updateParam("inbox", key === "all" ? "" : key)}
                className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
                  isActive
                    ? "bg-primary-soft border-primary/30 text-primary shadow-xs"
                    : "bg-surface border-border text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`}
              >
                <Icon className={`h-3.5 w-3.5 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
                {label}
              </button>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex items-center bg-surface border border-border rounded-[10px] px-3 py-1.5 w-64 md:w-72 shadow-sm">
            <Search className="h-4 w-4 text-muted-foreground mr-2 shrink-0" />
            <input
              placeholder="Search tasks…"
              className="bg-transparent border-none outline-none text-xs text-foreground placeholder:text-muted-foreground w-full"
              defaultValue={search}
              key={search}
              onChange={(event) => updateParam("search", event.target.value)}
            />
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
      </div>

      {tasksQuery.isError ? (
        <PageError error={tasksQuery.error} onRetry={tasksQuery.refetch} />
      ) : (
        <div className="rounded-[16px] bg-surface border border-border shadow-sm overflow-hidden">
          <DataTable
            columns={[
              {
                key: "pin",
                header: "",
                className: "w-10",
                render: (task) => (
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    title={pins.isPinned(task.task_id) ? "Unpin task" : "Pin task"}
                    onClick={(event) => {
                      event.stopPropagation();
                      pins.togglePin(task.task_id);
                    }}
                  >
                    <Pin className={pins.isPinned(task.task_id) ? "fill-primary text-primary" : "text-muted-foreground"} />
                  </Button>
                ),
              },
              {
                key: "task_title",
                header: "Task Description",
                sortable: true,
                render: (task) => {
                  const to = task.lead ? `/leads/${task.lead}` : `/tasks/${task.task_id}`;
                  const priority = taskPriorityName(task.priority);
                  const isHigh = priority?.toLowerCase() === "high";
                  const isCompleted = taskStatusName(task.status)?.toLowerCase() === "completed";

                  return (
                    <div className="flex items-center gap-3 py-1">
                      <div
                        className={`w-5 h-5 rounded-[6px] border flex items-center justify-center shrink-0 transition-colors ${
                          isCompleted
                            ? "bg-success border-success text-white"
                            : "border-border bg-surface hover:border-primary"
                        }`}
                      >
                        {isCompleted && <CheckCircle2 className="h-3.5 w-3.5" />}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <Link
                            to={to}
                            onClick={(event) => event.stopPropagation()}
                            className={`font-semibold text-[13.5px] text-foreground hover:text-primary transition-colors truncate ${
                              isCompleted ? "line-through text-muted-foreground" : ""
                            }`}
                          >
                            {task.task_title}
                          </Link>
                          {isHigh && (
                            <span className="w-1.5 h-1.5 rounded-full bg-destructive" title="High Priority" />
                          )}
                        </div>
                        {task.lead ? (
                          <span className="text-[11px] text-muted-foreground block truncate">
                            Linked to lead workspace
                          </span>
                        ) : null}
                      </div>
                    </div>
                  );
                },
              },
              {
                key: "status",
                header: "Status",
                render: (task) => <TaskStatusCell task={task} isManagerOrAdmin={isManagerOrAdmin} />,
              },
              {
                key: "priority",
                header: "Priority",
                render: (task) => {
                  const n = taskPriorityName(task.priority) || "Normal";
                  const isHigh = n.toLowerCase() === "high";
                  const isMed = n.toLowerCase() === "medium";
                  return (
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${
                        isHigh
                          ? "bg-destructive/10 text-destructive border border-destructive/20"
                          : isMed
                            ? "bg-warning-soft text-warning border border-warning-border"
                            : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {n}
                    </span>
                  );
                },
              },
              {
                key: "due_date",
                header: "Due Date",
                sortable: true,
                render: (task) => {
                  if (!task.due_date) return <span className="text-muted-foreground text-xs">—</span>;
                  const d = new Date(task.due_date);
                  const isOverdue = d < now && taskStatusName(task.status)?.toLowerCase() !== "completed";
                  return (
                    <span
                      className={`font-mono text-xs font-semibold ${
                        isOverdue ? "text-destructive" : "text-foreground"
                      }`}
                    >
                      {d.toLocaleDateString()} {d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
                    </span>
                  );
                },
              },
              {
                key: "assigned_to",
                header: "Assignee",
                render: (task) => (
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <UserCheck className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="truncate max-w-36">{findUserName(task.assigned_to)}</span>
                  </div>
                ),
              },
              {
                key: "notes",
                header: "Notes",
                className: "w-16",
                render: (task) => (
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    title="Add note"
                    aria-label={`Notes for ${task.task_title}`}
                    onClick={(event) => {
                      event.stopPropagation();
                      setNotesRecord({ type: "task", id: task.task_id, title: task.task_title });
                    }}
                  >
                    <MessageSquareText />
                  </Button>
                ),
              },
              {
                key: "actions",
                header: "",
                render: (task) => {
                  if (!isManagerOrAdmin) {
                    return null;
                  }
                  return (
                    <div className="flex items-center justify-end gap-1">
                      <Button asChild variant="ghost" size="sm" onClick={(event) => event.stopPropagation()}>
                        <Link to={`/tasks/${task.task_id}`}>Open →</Link>
                      </Button>
                      <Button asChild variant="ghost" size="icon" className="size-8 text-muted-foreground hover:text-foreground" title="Edit task" onClick={(event) => event.stopPropagation()}>
                        <Link to={`/tasks/${task.task_id}`}>
                          <Pencil className="size-4" />
                        </Link>
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                        title="Delete task"
                        onClick={(event) => {
                          event.stopPropagation();
                          setTaskToDelete(task);
                        }}
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
        </div>
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
