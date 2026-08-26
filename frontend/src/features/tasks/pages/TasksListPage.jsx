// Tasks list — server-side visibility (Admin/Manager: all, Employee: own).
// Status/priority names resolve from the G7 workaround constants.

import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { taskPriorityName, taskStatusName } from "@/utils/taskMasterData";
import { useTasks } from "../hooks";
import DataTable from "@/components/tables/DataTable";
import EmptyState from "@/components/common/EmptyState";
import PageError from "@/components/common/PageError";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function TasksListPage() {
  const { resolved } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const page = Number(searchParams.get("page") ?? "1");
  const search = searchParams.get("search") ?? "";
  const ordering = searchParams.get("ordering") ?? "";

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

  const rows = tasksQuery.data?.results ?? [];
  const count = tasksQuery.data?.count ?? 0;
  const canCreate = hasPermission(resolved, "add_task");

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Tasks</h1>
        {canCreate ? (
          <Button asChild>
            <Link to="/tasks/new">New task</Link>
          </Button>
        ) : null}
      </div>

      <Input
        placeholder="Search tasks…"
        className="w-64"
        defaultValue={search}
        onChange={(event) => updateParam("search", event.target.value.trim())}
      />

      {tasksQuery.isError ? (
        <PageError error={tasksQuery.error} onRetry={tasksQuery.refetch} />
      ) : (
        <DataTable
          columns={[
            {
              key: "task_title",
              header: "Title",
              sortable: true,
              render: (task) => (
                <Link to={`/tasks/${task.task_id}`} className="font-medium hover:underline">
                  {task.task_title}
                </Link>
              ),
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
              render: (task) => taskPriorityName(task.priority) ?? "—",
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
              render: (task) =>
                task.assigned_to ? `${String(task.assigned_to).slice(0, 8)}…` : "—",
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
    </div>
  );
}
