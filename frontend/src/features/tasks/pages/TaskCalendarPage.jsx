import { Link } from "react-router-dom";

import PageError from "@/components/common/PageError";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import TaskCalendar from "../components/TaskCalendar";
import { useTasks } from "../hooks";

export default function TaskCalendarPage() {
  const { resolved } = useAuth();
  const tasksQuery = useTasks({ page: 1, page_size: 100, ordering: "due_date" });
  const canCreate = hasPermission(resolved, "add_task");

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Calendar</h1>
          <p className="mt-1 text-sm text-muted-foreground">View tasks by their due date.</p>
        </div>
        {canCreate ? <Button asChild><Link to="/tasks/new">New task</Link></Button> : null}
      </div>

      {tasksQuery.isError ? (
        <PageError error={tasksQuery.error} onRetry={tasksQuery.refetch} />
      ) : (
        <TaskCalendar tasks={tasksQuery.data?.results ?? []} isLoading={tasksQuery.isLoading} />
      )}
    </div>
  );
}
