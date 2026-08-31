// Task create. Rules: lead required (rule #12); due date future; status/
// priority/category come from the G7 workaround constants until master-data
// endpoints exist. Only Admin/Manager reach this page in practice.

import { Link, useNavigate } from "react-router-dom";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import {
  TASK_CATEGORIES,
  TASK_PRIORITIES,
  TASK_STATUSES,
} from "@/utils/taskMasterData";
import { useCreateTask, useTaskStatuses, useTaskCategories } from "../hooks";
import { useUsers } from "@/features/admin/hooks";
import LeadSelect from "@/features/leads/components/LeadSelect";
import { taskSchema } from "@/schemas/task.schema";
import FormField from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function TaskCreatePage() {
  const navigate = useNavigate();
  const createTask = useCreateTask();
  const usersQuery = useUsers();
  const { data: taskStatuses = [] } = useTaskStatuses();
  const { data: taskCategories = [] } = useTaskCategories();

  const {
    register,
    handleSubmit,
    setValue,
    control,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      task_title: "",
      description: "",
      due_date: "",
      status: String(TASK_STATUSES[0]?.id ?? ""),
      priority: String(TASK_PRIORITIES[1]?.id ?? TASK_PRIORITIES[0]?.id ?? ""),
      category: String(TASK_CATEGORIES[0]?.id ?? ""),
      assigned_to: "",
    },
  });

  const leadValue = useWatch({ control, name: "lead" });
  const statusValue = useWatch({ control, name: "status" });
  const priorityValue = useWatch({ control, name: "priority" });
  const categoryValue = useWatch({ control, name: "category" });
  const assignedToValue = useWatch({ control, name: "assigned_to" });

  const onSubmit = async (values) => {
    try {
      const statusId = Number(values.status || statusValue || taskStatuses[0]?.status_id || 1);
      const priorityId = Number(values.priority || priorityValue || 2);
      const categoryId = Number(values.category || categoryValue || taskCategories[0]?.category_id || 1);
      const assignedTo = values.assigned_to || assignedToValue || undefined;

      await createTask.mutateAsync({
        task_title: values.task_title,
        description: values.description || undefined,
        lead: values.lead,
        due_date: values.due_date
          ? new Date(values.due_date).toISOString()
          : undefined,
        status: statusId,
        priority: priorityId,
        category: categoryId,
        assigned_to: assignedTo,
      });
      navigate("/tasks");
    } catch (error) {
      const normalized = error.normalized ?? { fieldErrors: {} };
      for (const [field, messages] of Object.entries(normalized.fieldErrors)) {
        if (messages && messages[0]) {
          setError(field, { message: messages[0] });
        }
      }
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">New task</h1>
        <Button variant="ghost" asChild>
          <Link to="/tasks">Cancel</Link>
        </Button>
      </div>

      {/* G7 notice — remove when master-data endpoints ship. */}
      <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
        Status / Priority / Category options are hardcoded while the backend has
        no master-data endpoints (see BACKEND_GAPS.md G7). Verify IDs in Django admin.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <FormField id="task_title" label="Title" error={errors.task_title?.message}>
          <Input id="task_title" {...register("task_title")} />
        </FormField>

        <FormField id="description" label="Description" error={errors.description?.message}>
          <Textarea id="description" rows={3} {...register("description")} />
        </FormField>

        <div className="grid gap-4 md:grid-cols-2">
          <FormField id="lead" label="Lead" error={errors.lead?.message} help="Every task belongs to a lead.">
            <LeadSelect value={leadValue} onChange={(value) => setValue("lead", value)} />
          </FormField>

          <FormField id="assigned_to" label="Assigned To Employee" error={errors.assigned_to?.message}>
            <Select
              value={assignedToValue || ""}
              onValueChange={(value) => setValue("assigned_to", value)}
            >
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
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <FormField id="status" label="Status">
            <Select value={statusValue} onValueChange={(value) => setValue("status", value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(taskStatuses.length > 0
                  ? taskStatuses.map((s) => ({ id: s.status_id ?? s.id, name: s.status_name ?? s.name }))
                  : TASK_STATUSES
                ).map((option) => (
                  <SelectItem key={option.id} value={String(option.id)}>
                    {option.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>

          <FormField id="priority" label="Priority">
            <Select value={priorityValue} onValueChange={(value) => setValue("priority", value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TASK_PRIORITIES.map((option) => (
                  <SelectItem key={option.id} value={String(option.id)}>
                    {option.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <FormField id="category" label="Category">
            <Select value={categoryValue} onValueChange={(value) => setValue("category", value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(taskCategories.length > 0
                  ? taskCategories.map((c) => ({ id: c.category_id ?? c.id, name: c.category_name ?? c.name }))
                  : TASK_CATEGORIES
                ).map((option) => (
                  <SelectItem key={option.id} value={String(option.id)}>
                    {option.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>

          <FormField id="due_date" label="Due date" error={errors.due_date?.message}>
            <Input id="due_date" type="datetime-local" {...register("due_date")} />
          </FormField>
        </div>

        <Button type="submit" disabled={createTask.isPending} className="self-start">
          {createTask.isPending ? "Creating…" : "Create task"}
        </Button>
      </form>
    </div>
  );
}
