// Meeting creation — Manager only.
// Manager selects: Task, Employee (from all employees), Title, Date/Time, Type.
// The manager field is auto-set to the logged-in manager's own user_id.

import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { MEETING_TYPES } from "@/utils/meetingMasterData";
import { useCreateMeeting } from "../hooks";
import { addMeetingParticipant } from "../api";
import { useUsers } from "@/features/admin/hooks";
import { useTask } from "@/features/tasks/hooks";
import TaskSelect from "@/features/tasks/components/TaskSelect";
import { createMeetingSchema } from "@/schemas/meeting.schema";
import FormField from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import DynamicFormFields from "@/features/callforms/components/DynamicFormFields";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Plus, Search, Trash2, Users } from "lucide-react";
import { toast } from "sonner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function ParticipantPicker({ open, onOpenChange, users, selected, onChange }) {
  const [search, setSearch] = useState("");
  const visibleUsers = users.filter((person) => `${person.full_name || ""} ${person.username || ""} ${person.email || ""}`.toLowerCase().includes(search.toLowerCase()));
  const toggle = (userId) => {
    const id = String(userId);
    onChange(selected.includes(id) ? selected.filter((value) => value !== id) : [...selected, id]);
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[80vh] overflow-hidden p-0 sm:max-w-lg">
        <DialogHeader className="border-b px-5 py-4"><DialogTitle>Add Participants</DialogTitle></DialogHeader>
        <div className="px-5 pt-4">
          <div className="relative"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" /><Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search users" className="pl-9" /></div>
          <div className="mt-3 flex justify-between text-sm"><span>CRM users</span><span className="text-primary">Selected ({selected.length})</span></div>
        </div>
        <div className="max-h-80 overflow-y-auto px-5">
          {visibleUsers.map((person) => <label key={person.user_id} className="flex cursor-pointer items-start gap-3 border-b py-3 last:border-0"><input type="checkbox" className="mt-1 size-4 accent-blue-600" checked={selected.includes(String(person.user_id))} onChange={() => toggle(person.user_id)} /><span className="min-w-0"><strong className="block text-sm font-medium">{person.full_name || person.username}</strong><span className="block truncate text-xs text-muted-foreground">{person.email || "No email address"}</span></span></label>)}
          {!visibleUsers.length ? <p className="py-10 text-center text-sm text-muted-foreground">No users found.</p> : null}
        </div>
        <DialogFooter><Button type="button" onClick={() => onOpenChange(false)}>Done</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function MeetingCreatePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialTaskId = searchParams.get("task_id") ?? "";
  const { user, resolved } = useAuth();
  const createMeeting = useCreateMeeting();
  const { data: users = [] } = useUsers();
  const [typeId, setTypeId] = useState("1");
  const [participantOpen, setParticipantOpen] = useState(false);
  const [participantIds, setParticipantIds] = useState([]);
  const [customFields, setCustomFields] = useState([]);
  const [customValues, setCustomValues] = useState({});
  const [customErrors, setCustomErrors] = useState({});
  const [fieldDraft, setFieldDraft] = useState({ label: "", field_type: "text", options: "", is_required: false });
  const isOnline = typeId === "1";

  const isManager = String(resolved?.roleName || "").toLowerCase() === "manager";
  const canCreate = hasPermission(resolved, "add_meeting");

  const {
    register,
    handleSubmit,
    getValues,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(createMeetingSchema),
    defaultValues: {
      task_id: initialTaskId,
      lead: "",
      meeting_title: "",
      meeting_date: "",
      start_time: "",
      end_time: "",
      meeting_type_id: 1,
      location: "",
      description: "",
      manager: "",
    },
  });

  const selectedTaskId = watch("task_id");
  const { data: taskData } = useTask(selectedTaskId);

  // All employees for the "Who is this meeting with?" field
  const employeeOptions = users.filter((u) => {
    const role = (u.role || u.role_name || "").toLowerCase();
    return role === "employee" || role.includes("employee");
  });
  // Fallback: show all users if no employee role found
  const displayEmployees = employeeOptions.length > 0 ? employeeOptions : users;
  const managerOptions = users.filter((u) =>
    String(u.role || u.role_name || "").toLowerCase().includes("manager"),
  );

  // Pre-fill manager field with the logged-in manager's own user_id
  useEffect(() => {
    if (isManager && user?.user_id) {
      setValue("manager", String(user.user_id), { shouldValidate: true });
    }
  }, [isManager, user, setValue]);

  // Auto-populate from selected task
  useEffect(() => {
    if (taskData) {
      if (taskData.lead) {
        setValue("lead", String(taskData.lead));
      }
      if (!getValues("meeting_title")) {
        setValue("meeting_title", `Meeting: ${taskData.task_title}`);
      }
    }
  }, [taskData, getValues, setValue]);

  const onSubmit = async (values) => {
    const requiredErrors = Object.fromEntries(customFields.filter((field) => field.is_required && (customValues[field.field_key] === undefined || customValues[field.field_key] === "" || customValues[field.field_key] === null)).map((field) => [field.field_key, `${field.label} is required.`]));
    setCustomErrors(requiredErrors);
    if (Object.keys(requiredErrors).length) return;
    try {
      const meeting = await createMeeting.mutateAsync({
        task_id: values.task_id,
        lead: values.lead || undefined,
        meeting_status_id: 1,
        meeting_type_id: values.meeting_type_id,
        meeting_title: values.meeting_title,
        meeting_date: values.meeting_date,
        start_time: values.start_time,
        end_time: values.end_time,
        location: values.location || undefined,
        description: values.description || undefined,
        manager: values.manager, // auto-set to logged-in manager
        extra_fields: { definitions: customFields, values: customValues },
      });
      const results = await Promise.allSettled(participantIds.map((userId) => addMeetingParticipant(meeting.meeting_id, { user_id: userId, participant_role: "Attendee", is_required: true })));
      const failed = results.filter((result) => result.status === "rejected").length;
      if (failed) toast.warning(`Meeting created, but ${failed} participant${failed === 1 ? "" : "s"} could not be added.`);
      navigate(`/meetings/${meeting.meeting_id}`);
    } catch {
      // Errors are toasted by the mutation; keep the form filled for retry.
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

  if (!canCreate) {
    return (
      <div className="mx-auto flex w-full max-w-2xl flex-col items-center gap-4 p-12 text-center">
        <h2 className="text-xl font-semibold">Access Restricted</h2>
        <p className="text-sm text-muted-foreground">
          You do not have permission to schedule meetings.
        </p>
        <Button asChild variant="outline">
          <Link to="/meetings">Back to Meetings</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-black/45 p-4 pt-10 backdrop-blur-[1px]">
      <div className="w-full max-w-2xl overflow-hidden rounded-xl border bg-background shadow-2xl">
      <div className="flex items-center justify-between border-b px-6 py-5">
        <h1 className="text-xl font-semibold tracking-tight">Meeting Information</h1>
        <Button variant="ghost" size="sm" asChild>
          <Link to="/meetings">Cancel</Link>
        </Button>
      </div>

      <div className="max-h-[calc(100vh-10rem)] overflow-y-auto px-6 py-5">

      <p className="rounded-md border border-blue-300 bg-blue-50 px-3 py-2 text-xs text-blue-900 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-200">
        {isManager
          ? "Select the task and the employee this meeting is for. "
          : "Select the task and the manager who should approve this meeting. "}
        {isOnline
          ? "A Google Meet link is generated automatically."
          : "Office location is used if no location is provided."}
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>

        {/* Task */}
        <FormField id="task_id" label="Task" error={errors.task_id?.message}>
          <TaskSelect
            value={watch("task_id")}
            onChange={(value) => setValue("task_id", value, { shouldValidate: true })}
          />
        </FormField>

        {/* Employee — who is this meeting with */}
        {isManager ? <FormField
          id="employee"
          label="Employee (Meeting With)"
          help="Select the employee this meeting is scheduled for."
        >
          <Select
            value={watch("employee")}
            onValueChange={(value) => setValue("employee", value, { shouldValidate: true })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select employee…" />
            </SelectTrigger>
            <SelectContent>
              {displayEmployees.map((emp) => (
                <SelectItem key={emp.user_id} value={String(emp.user_id)}>
                  {emp.full_name || emp.username}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField> : (
          <FormField id="manager" label="Approving Manager" error={errors.manager?.message} required>
            <Select
              value={watch("manager")}
              onValueChange={(value) => setValue("manager", value, { shouldValidate: true })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select manager…" />
              </SelectTrigger>
              <SelectContent>
                {managerOptions.map((manager) => (
                  <SelectItem key={manager.user_id} value={String(manager.user_id)}>
                    {manager.full_name || manager.username}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
        )}

        <FormField id="participants" label="Participants">
          <div className="flex min-h-9 items-center justify-between rounded-lg border px-3 py-1.5">
            <div className="flex min-w-0 items-center gap-2 text-sm"><Users className="size-4 text-muted-foreground" /><span className="truncate">{participantIds.length ? `${participantIds.length} participant${participantIds.length === 1 ? "" : "s"} selected` : "None"}</span></div>
            <Button type="button" variant="ghost" size="sm" className="text-primary" onClick={() => setParticipantOpen(true)}><Plus /> Add</Button>
          </div>
        </FormField>

        {/* Title */}
        <FormField id="meeting_title" label="Meeting Title" error={errors.meeting_title?.message}>
          <Input
            id="meeting_title"
            placeholder="e.g. Product Demo with Client"
            {...register("meeting_title")}
          />
        </FormField>

        {/* Date / Time */}
        <div className="grid gap-4 md:grid-cols-3">
          <FormField id="meeting_date" label="Date" error={errors.meeting_date?.message}>
            <Input id="meeting_date" type="date" {...register("meeting_date")} />
          </FormField>
          <FormField id="start_time" label="Start" error={errors.start_time?.message}>
            <Input id="start_time" type="time" {...register("start_time")} />
          </FormField>
          <FormField id="end_time" label="End" error={errors.end_time?.message}>
            <Input id="end_time" type="time" {...register("end_time")} />
          </FormField>
        </div>

        {/* Meeting Type */}
        <FormField id="meeting_type_id" label="Type">
          <Select
            value={typeId}
            onValueChange={(value) => {
              setTypeId(value);
              setValue("meeting_type_id", Number(value));
            }}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MEETING_TYPES.map((option) => (
                <SelectItem key={option.id} value={String(option.id)}>
                  {option.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        {/* Location — offline only */}
        {!isOnline ? (
          <FormField
            id="location"
            label="Location"
            error={errors.location?.message}
            help="Leave blank to use the office location."
          >
            <Input id="location" {...register("location")} />
          </FormField>
        ) : null}

        {/* Description */}
        <FormField id="description" label="Description" error={errors.description?.message}>
          <Textarea
            id="description"
            rows={3}
            placeholder="Agenda, notes, or instructions…"
            {...register("description")}
          />
        </FormField>

        {false && <><FormField
          id="meeting_template"
          label="Meeting Template"
          help="Choose a template to display its custom fields for this meeting."
        >
          <Select
            value={templateId || "none"}
            onValueChange={(value) => {
              setTemplateId(value === "none" ? "" : value);
              setDynamicValues({});
              setDynamicErrors({});
            }}
          >
            <SelectTrigger id="meeting_template">
              <SelectValue placeholder="No custom template" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">No custom template</SelectItem>
              {meetingTemplates.map((template) => (
                <SelectItem key={template.id} value={String(template.id)}>
                  {template.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        {templateId ? (
          <div className="rounded-xl border bg-muted/20 p-4">
            <h2 className="mb-3 font-medium">
              {selectedTemplate?.name ?? "Custom meeting fields"}
            </h2>
            {fieldsQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading template fields…</p>
            ) : (
              <DynamicFormFields
                fields={dynamicFields}
                values={dynamicValues}
                errors={dynamicErrors}
                onChange={(nextValues) => {
                  setDynamicValues(nextValues);
                  setDynamicErrors({});
                }}
                stepView={false}
              />
            )}
          </div>
        ) : null}</>}

        <section className="rounded-xl border bg-muted/15 p-4">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div><h2 className="font-semibold">Custom Fields</h2><p className="text-xs text-muted-foreground">Add extra fields for this meeting.</p></div>
            <span className="text-xs text-muted-foreground">{customFields.length}/25</span>
          </div>
          {customFields.length ? <div className="mb-4 space-y-3">{customFields.map((field) => <div key={field.field_key} className="relative"><DynamicFormFields fields={[field]} values={customValues} errors={customErrors} onChange={(next) => { setCustomValues(next); setCustomErrors({}); }} stepView={false} /><Button type="button" variant="ghost" size="icon-sm" className="absolute right-2 top-2 text-destructive" title="Remove field" onClick={() => removeCustomField(field.field_key)}><Trash2 /></Button></div>)}</div> : <p className="mb-4 rounded-lg border border-dashed p-4 text-center text-sm text-muted-foreground">No custom fields added yet.</p>}
          <div className="grid items-end gap-3 rounded-lg border bg-background p-3 md:grid-cols-2">
            <FormField id="custom_field_label" label="Field name"><Input placeholder="e.g. Agenda or Contact person" value={fieldDraft.label} onChange={(event) => setFieldDraft({ ...fieldDraft, label: event.target.value })} /></FormField>
            <FormField id="custom_field_type" label="Field type"><Select value={fieldDraft.field_type} onValueChange={(value) => setFieldDraft({ ...fieldDraft, field_type: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{["text", "textarea", "number", "date", "time", "boolean", "select", "radio", "checkbox"].map((type) => <SelectItem key={type} value={type} className="capitalize">{type}</SelectItem>)}</SelectContent></Select></FormField>
            {["select", "radio", "checkbox"].includes(fieldDraft.field_type) ? <FormField id="custom_field_options" label="Options"><Input placeholder="Option one, Option two" value={fieldDraft.options} onChange={(event) => setFieldDraft({ ...fieldDraft, options: event.target.value })} /></FormField> : null}
            <label className="flex h-8 items-center gap-2 text-sm"><input type="checkbox" checked={fieldDraft.is_required} onChange={(event) => setFieldDraft({ ...fieldDraft, is_required: event.target.checked })} /> Required field</label>
            <Button type="button" variant="outline" disabled={!fieldDraft.label.trim() || customFields.length >= 25} onClick={addCustomField}><Plus /> Add field</Button>
          </div>
        </section>

        <Button
          type="submit"
          disabled={createMeeting.isPending}
          className="sticky -bottom-5 self-end bg-[#2563EB] hover:bg-[#1D4ED8]"
        >
          {createMeeting.isPending ? "Scheduling…" : "Schedule Meeting"}
        </Button>
      </form>
      </div>
      </div>
      <ParticipantPicker open={participantOpen} onOpenChange={setParticipantOpen} users={users.filter((person) => String(person.user_id) !== String(user?.user_id))} selected={participantIds} onChange={setParticipantIds} />
    </div>
  );
}

