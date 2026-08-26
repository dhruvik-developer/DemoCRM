// Reminders index — G8 interim UX (no list endpoint exists): create + open by
// ID. Delivery itself is handled server-side by Celery beat jobs.

import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { REMINDER_STATUSES, REMINDER_TYPES } from "@/utils/reminderMasterData";
import { useCreateReminder, useReminder, useUpdateReminderStatus } from "../hooks";
import TaskSelect from "@/features/tasks/components/TaskSelect";
import { createReminderSchema } from "@/schemas/reminder.schema";
import PageError from "@/components/common/PageError";
import PageLoader from "@/components/common/PageLoader";
import FormField from "@/components/forms/FormField";
import StatusBadge from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function ReminderLookup({ id }) {
  const reminderQuery = useReminder(id);
  const updateStatus = useUpdateReminderStatus(id);

  if (!id) return null;
  if (reminderQuery.isLoading) return <PageLoader label="Loading reminder…" />;
  if (reminderQuery.isError) {
    return <PageError error={reminderQuery.error} onRetry={reminderQuery.refetch} />;
  }

  const reminder = reminderQuery.data;
  const statusId = reminder.reminder_status_id?.id ?? reminder.reminder_status_id;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Reminder #{reminder.reminder_id}</CardTitle>
        <StatusBadge status={statusId === 2 ? "ACCEPTED" : undefined} />
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm">{reminder.message}</p>
        <p className="text-xs text-muted-foreground">
          Fires at {new Date(reminder.reminder_datetime).toLocaleString()} ·{" "}
          task #{reminder.task_id ?? "—"} / meeting #{reminder.meeting_id ?? "—"}
        </p>
        {statusId === 1 ? (
          <Button
            size="sm"
            variant="outline"
            className="w-fit"
            disabled={updateStatus.isPending}
            onClick={() => updateStatus.mutateAsync(2)}
          >
            Mark as sent
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}

export default function RemindersPage() {
  const [lookupId, setLookupId] = useState("");
  const [createdId, setCreatedId] = useState("");
  const createReminder = useCreateReminder();

  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(createReminderSchema),
    defaultValues: {
      context_task_id: "",
      context_meeting_id: "",
      reminder_type_id: String(REMINDER_TYPES[0]?.id ?? ""),
      reminder_datetime: "",
      message: "",
    },
  });

  const contextTaskId = useWatch({ control, name: "context_task_id" });
  const contextMeetingId = useWatch({ control, name: "context_meeting_id" });
  const reminderTypeId = useWatch({ control, name: "reminder_type_id" });
  const attachToTask = !contextMeetingId;

  const onSubmit = async (values) => {
    try {
      // Backend contract: {task_id?|meeting_id?, reminder_type_id,
      // reminder_status_id, reminder_datetime, message}
      const payload = {
        reminder_status_id: REMINDER_STATUSES[0]?.id ?? 1,
        reminder_type_id: values.reminder_type_id,
        reminder_datetime: new Date(values.reminder_datetime).toISOString(),
        message: values.message,
      };
      if (values.context_task_id) {
        payload.task_id = Number(values.context_task_id);
      } else {
        payload.meeting_id = Number(values.context_meeting_id);
      }
      const reminder = await createReminder.mutateAsync(payload);
      setCreatedId(reminder.reminder_id);
    } catch {
      // Toasted by the mutation.
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <h1 className="text-2xl font-semibold tracking-tight">Reminders</h1>

      <p className="rounded-md border border-blue-300 bg-blue-50 px-3 py-2 text-xs text-blue-900 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-200">
        No reminders list endpoint exists yet (BACKEND_GAPS.md G8). Create one
        below or open it by ID afterwards. Delivery is handled by backend jobs.
      </p>

      {createdId ? (
        <div className="flex flex-col gap-2 rounded-md border px-3 py-2 text-sm">
          Reminder #{createdId} created.
          <Button variant="outline" size="sm" className="w-fit" onClick={() => setLookupId(createdId)}>
            View it
          </Button>
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Open by ID</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-2">
          <Input
            inputMode="numeric"
            placeholder="Reminder ID"
            value={lookupId}
            onChange={(event) => setLookupId(event.target.value.replace(/\D/g, ""))}
          />
          <Button variant="outline" disabled={!lookupId}>
            Open
          </Button>
        </CardContent>
      </Card>

      <ReminderLookup id={lookupId || createdId} />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">New reminder</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
            <div className="grid gap-4 md:grid-cols-2">
              <FormField
                id="context_task_id"
                label={attachToTask ? "Task" : "Task (unused)"}
                error={!attachToTask ? undefined : errors.context_task_id?.message}
              >
                <TaskSelect
                  value={contextTaskId}
                  onChange={(value) => {
                    setValue("context_task_id", value);
                    if (value) setValue("context_meeting_id", "");
                  }}
                  disabled={!attachToTask}
                />
              </FormField>

              <FormField id="context_meeting_id" label="…or Meeting ID">
                <Input
                  inputMode="numeric"
                  placeholder="Meeting ID"
                  value={contextMeetingId}
                  onChange={(event) => {
                    setValue("context_meeting_id", event.target.value.replace(/\D/g, ""));
                    if (event.target.value) setValue("context_task_id", "");
                  }}
                />
              </FormField>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <FormField id="reminder_type" label="Type">
                <Select
                  value={reminderTypeId}
                  onValueChange={(value) => setValue("reminder_type_id", value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {REMINDER_TYPES.map((option) => (
                      <SelectItem key={option.id} value={String(option.id)}>
                        {option.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>

              <FormField id="reminder_datetime" label="When" error={errors.reminder_datetime?.message}>
                <Input id="reminder_datetime" type="datetime-local" {...register("reminder_datetime")} />
              </FormField>
            </div>

            <FormField id="message" label="Message" error={errors.message?.message}>
              <Textarea id="message" rows={3} {...register("message")} />
            </FormField>

            <Button type="submit" disabled={createReminder.isPending} className="self-start">
              {createReminder.isPending ? "Creating…" : "Create reminder"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
