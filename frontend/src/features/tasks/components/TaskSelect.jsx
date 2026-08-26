// Task picker for meeting requests: uses the real tasks list when visible
// (Admin/Manager see all, Employees their own), manual ID entry otherwise.

import { useState } from "react";
import { useTasks } from "@/features/tasks/hooks";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function TaskSelect({ value, onChange }) {
  const [manualMode, setManualMode] = useState(false);
  const tasksQuery = useTasks({ page_size: 50 });
  const tasks = tasksQuery.data?.results ?? [];
  const canListTasks = !tasksQuery.isError && tasks.length > 0;

  if (manualMode || (!canListTasks && !tasksQuery.isLoading)) {
    return (
      <div className="flex flex-col gap-1">
        <Input
          inputMode="numeric"
          placeholder="Task ID"
          value={value}
          onChange={(event) => onChange(event.target.value.replace(/\D/g, ""))}
        />
        <button
          type="button"
          className="w-fit text-xs text-muted-foreground hover:underline"
          onClick={() => setManualMode(false)}
        >
          Try picking from the list instead
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <Select
        value={value || undefined}
        onValueChange={onChange}
      >
        <SelectTrigger>
          <SelectValue
            placeholder={tasksQuery.isLoading ? "Loading tasks…" : "Select task"}
          />
        </SelectTrigger>
        <SelectContent>
          {tasks.map((task) => (
            <SelectItem key={task.task_id} value={String(task.task_id)}>
              #{task.task_id} — {task.task_title}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <button
        type="button"
        className="w-fit text-xs text-muted-foreground hover:underline"
        onClick={() => setManualMode(true)}
      >
        Enter a task ID manually
      </button>
    </div>
  );
}
