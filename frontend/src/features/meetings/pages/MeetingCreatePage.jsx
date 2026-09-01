// Meeting creation — Manager only.
// Manager selects: Task, Employee (from all employees), Title, Date/Time, Type.
// The manager field is auto-set to the logged-in manager's own user_id.

import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useAuth } from "@/hooks/useAuth";
import { hasPermission } from "@/utils/permissions";
import { MEETING_TYPES } from "@/utils/meetingMasterData";
import { useCreateMeeting } from "../hooks";
import { useUsers } from "@/features/admin/hooks";
import { useTask } from "@/features/tasks/hooks";
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
  const { user, resolved } = useAuth();
  const createMeeting = useCreateMeeting();
  const { data: users = [] } = useUsers();
  const [typeId, setTypeId] = useState("1");
  const isOnline = typeId === "1";

  const isManager = String(resolved?.roleName || "").toLowerCase() === "manager";
  const canCreate = hasPermission(resolved, "add_meeting");

  const {
    register,
    handleSubmit,
    setValue,
    watch,
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
      if (!watch("meeting_title")) {
        setValue("meeting_title", `Meeting: ${taskData.task_title}`);
      }
    }
  }, [taskData, setValue]);

  const onSubmit = async (values) => {
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
      });
      navigate(`/meetings/${meeting.meeting_id}`);
    } catch {
      // Errors are toasted by the mutation; keep the form filled for retry.
    }
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
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Schedule Meeting</h1>
        <Button variant="ghost" asChild>
          <Link to="/meetings">Cancel</Link>
        </Button>
      </div>

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

        <Button
          type="submit"
          disabled={createMeeting.isPending}
          className="self-start bg-[#2563EB] hover:bg-[#1D4ED8]"
        >
          {createMeeting.isPending ? "Scheduling…" : "Schedule Meeting"}
        </Button>
      </form>
    </div>
  );
}

