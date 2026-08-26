// Task create. Rules: lead required (rule #12); due date future; status/
// priority/category come from the G7 workaround constants until master-data
// endpoints exist. Only Admin/Manager reach this page in practice.

import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import {
  TASK_CATEGORIES,
  TASK_PRIORITIES,
  TASK_STATUSES,
} from "@/utils/taskMasterData";
import { useCreateTask } from "../hooks";
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

  const {
    register,
    handleSubmit,
    setValue,
    watch,
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
    },
  });

  const onSubmit = async (values) => {
    try {
      await createTask.mutateAsync({
        task_title: values.task_title,
        description: values.description || undefined,
        lead: values.lead,
        due_date: values.due_date
          ? new Date(values.due_date).toISOString()
          : undefined,
        status: Number(values.status),
        priority: Number(values.priority),
        category: Number(values.category),
      });
      navigate("/tasks");
    } catch (error) {
      const normalized = error.normalized ?? { fieldErrors: {} };
      for (const [field, messages] of Object.entries(normalized.fieldErrors)) {
        const schemaField =
          field === "task_title" || field === "lead" ? field : null;
        if (schemaField) {
          setError(schemaField, { message: messages[0] });
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

        <FormField id="lead" label="Lead" error={errors.lead?.message} help="Every task belongs to a lead.">
          <LeadSelect value={watch("lead")} onChange={(value) => setValue("lead", value)} />
        </FormField>

        <div className="grid gap-4 md:grid-cols-2">
          <FormField id="status" label="Status">
            <Select value={watch("status")} onValueChange={(value) => setValue("status", value)}>
              <SelectTrigger>
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
          </FormField>

          <FormField id="priority" label="Priority">
            <Select value={watch("priority")} onValueChange={(value) => setValue("priority", value)}>
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
            <Select value={watch("category")} onValueChange={(value) => setValue("category", value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TASK_CATEGORIES.map((option) => (
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
