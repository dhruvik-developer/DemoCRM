// Meeting request form. Backend rules encoded:
// - manager UUID required (must hold the Manager role server-side, else 400)
// - online meetings auto-generate a Google Meet link when none is given;
//   offline ones default the office location — shown as UI hints
// - lands in PENDING approval with the manager notified via Celery

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { MEETING_TYPES } from "@/utils/meetingMasterData";
import { useCreateMeeting } from "../hooks";
import TaskSelect from "@/features/tasks/components/TaskSelect";
import { createMeetingSchema } from "@/schemas/meeting.schema";
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

export default function MeetingCreatePage() {
  const navigate = useNavigate();
  const createMeeting = useCreateMeeting();
  const [typeId, setTypeId] = useState("1");
  const isOnline = typeId === "1";

  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(createMeetingSchema),
    defaultValues: {
      task_id: "",
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

  const taskId = useWatch({ control, name: "task_id" });

  const onSubmit = async (values) => {
    try {
      const meeting = await createMeeting.mutateAsync({
        task_id: values.task_id,
        lead: values.lead || undefined,
        meeting_status_id: 1, // Scheduled/Pending — G7 constant
        meeting_type_id: values.meeting_type_id,
        meeting_title: values.meeting_title,
        meeting_date: values.meeting_date,
        start_time: values.start_time,
        end_time: values.end_time,
        location: values.location || undefined,
        description: values.description || undefined,
        manager: values.manager,
      });
      navigate(`/meetings/${meeting.meeting_id}`);
    } catch {
      // Errors are toasted by the mutation; keep the form filled for retry.
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Request meeting</h1>
        <Button variant="ghost" asChild>
          <Link to="/meetings">Cancel</Link>
        </Button>
      </div>

      <p className="rounded-md border border-blue-300 bg-blue-50 px-3 py-2 text-xs text-blue-900 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-200">
        The request goes to the selected manager as PENDING.{" "}
        {isOnline
          ? "A Google Meet link is generated automatically if you don't provide one."
          : "If no location is given, the office address is used."}
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <FormField id="task_id" label="Task ID" error={errors.task_id?.message}>
          <TaskSelect value={taskId} onChange={(value) => setValue("task_id", value)} />
        </FormField>

        <FormField id="manager" label="Manager user UUID" error={errors.manager?.message}
          help="Must be a user holding the Manager role."
        >
          <Input id="manager" placeholder="00000000-0000-4000-8000-…" {...register("manager")} />
        </FormField>

        <FormField id="meeting_title" label="Title" error={errors.meeting_title?.message}>
          <Input id="meeting_title" {...register("meeting_title")} />
        </FormField>

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

        <FormField id="description" label="Description" error={errors.description?.message}>
          <Textarea id="description" rows={3} {...register("description")} />
        </FormField>

        <Button type="submit" disabled={createMeeting.isPending} className="self-start">
          {createMeeting.isPending ? "Sending request…" : "Request meeting"}
        </Button>
      </form>
    </div>
  );
}
