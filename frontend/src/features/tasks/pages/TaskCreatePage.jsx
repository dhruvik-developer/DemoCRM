// Task create. Rules: lead required (rule #12); due date future; status/
// priority/category come from the G7 workaround constants until master-data
// endpoints exist. Only Admin/Manager reach this page in practice.

import { useState } from "react";
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
import DynamicFormFields from "@/features/callforms/components/DynamicFormFields";
import { Plus, Trash2 } from "lucide-react";
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
  const [customFields, setCustomFields] = useState([]);
  const [customValues, setCustomValues] = useState({});
  const [customErrors, setCustomErrors] = useState({});
  const [fieldDraft, setFieldDraft] = useState({ label: "", field_type: "text", options: "", is_required: false });

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
    const requiredErrors = Object.fromEntries(customFields.filter((field) => field.is_required && (customValues[field.field_key] === undefined || customValues[field.field_key] === "" || customValues[field.field_key] === null)).map((field) => [field.field_key, `${field.label} is required.`]));
    setCustomErrors(requiredErrors);
    if (Object.keys(requiredErrors).length) return;
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
        custom_fields: { definitions: customFields, values: customValues },
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

  const addCustomField = () => {
    const label = fieldDraft.label.trim();
    if (!label || customFields.length >= 25) return;
    const baseKey = label.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "field";
    let fieldKey = baseKey;
    let suffix = 2;
    while (customFields.some((field) => field.field_key === fieldKey)) fieldKey = `${baseKey}_${suffix++}`;
    const optionTypes = ["select", "radio", "checkbox"];
    setCustomFields((current) => [...current, { id: `custom_${Date.now()}`, field_key: fieldKey, label, field_type: fieldDraft.field_type, is_required: fieldDraft.is_required, options: optionTypes.includes(fieldDraft.field_type) ? fieldDraft.options.split(",").map((item) => item.trim()).filter(Boolean) : [] }]);
    setFieldDraft({ label: "", field_type: "text", options: "", is_required: false });
  };

  const removeCustomField = (fieldKey) => {
    setCustomFields((current) => current.filter((field) => field.field_key !== fieldKey));
    setCustomValues((current) => { const next = { ...current }; delete next[fieldKey]; return next; });
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

        <section className="mt-2 rounded-xl border bg-muted/15 p-4">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div><h2 className="font-semibold">Custom Fields</h2><p className="text-xs text-muted-foreground">Add extra fields to this task whenever you need them.</p></div>
            <span className="text-xs text-muted-foreground">{customFields.length}/25</span>
          </div>

          {customFields.length ? (
            <div className="mb-4 space-y-3">
              {customFields.map((field) => (
                <div key={field.field_key} className="relative">
                  <DynamicFormFields fields={[field]} values={customValues} errors={customErrors} onChange={(next) => { setCustomValues(next); setCustomErrors({}); }} stepView={false} />
                  <Button type="button" variant="ghost" size="icon-sm" className="absolute right-2 top-2 text-destructive" title="Remove field" onClick={() => removeCustomField(field.field_key)}><Trash2 /></Button>
                </div>
              ))}
            </div>
          ) : <p className="mb-4 rounded-lg border border-dashed p-4 text-center text-sm text-muted-foreground">No custom fields added yet.</p>}

          <div className="grid items-end gap-3 rounded-lg border bg-background p-3 md:grid-cols-2">
            <FormField id="custom_field_label" label="Field name"><Input id="custom_field_label" placeholder="e.g. Budget or Contact person" value={fieldDraft.label} onChange={(event) => setFieldDraft({ ...fieldDraft, label: event.target.value })} /></FormField>
            <FormField id="custom_field_type" label="Field type"><Select value={fieldDraft.field_type} onValueChange={(value) => setFieldDraft({ ...fieldDraft, field_type: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{["text", "textarea", "number", "date", "time", "boolean", "select", "radio", "checkbox"].map((type) => <SelectItem key={type} value={type}>{type[0].toUpperCase() + type.slice(1)}</SelectItem>)}</SelectContent></Select></FormField>
            {["select", "radio", "checkbox"].includes(fieldDraft.field_type) ? <FormField id="custom_field_options" label="Options"><Input id="custom_field_options" placeholder="Option one, Option two" value={fieldDraft.options} onChange={(event) => setFieldDraft({ ...fieldDraft, options: event.target.value })} /></FormField> : null}
            <label className="flex h-8 items-center gap-2 text-sm"><input type="checkbox" checked={fieldDraft.is_required} onChange={(event) => setFieldDraft({ ...fieldDraft, is_required: event.target.checked })} /> Required field</label>
            <Button type="button" variant="outline" disabled={!fieldDraft.label.trim() || customFields.length >= 25} onClick={addCustomField}><Plus /> Add field</Button>
          </div>
        </section>

        <Button type="submit" disabled={createTask.isPending} className="self-start">
          {createTask.isPending ? "Creating…" : "Create task"}
        </Button>
      </form>
    </div>
  );
}
