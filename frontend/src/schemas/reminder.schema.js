import { z } from "zod";

// Mirrors ReminderCreateView: message required; reminder_datetime must be in
// the future; at least one of task/meeting context is expected (the form
// enforces exactly one via radio).

export const createReminderSchema = z
  .object({
    context_task_id: z.string().optional().or(z.literal("")),
    context_meeting_id: z.string().optional().or(z.literal("")),
    reminder_type_id: z.coerce.number().int().positive("Select a type."),
    reminder_datetime: z
      .string()
      .min(1, "Date & time is required.")
      .refine((value) => {
        const parsed = new Date(value);
        return !Number.isNaN(parsed.getTime()) && parsed.getTime() > Date.now();
      }, "The reminder must be in the future."),
    message: z.string().trim().min(1, "Message is required."),
  })
  .superRefine((values, ctx) => {
    if (!values.context_task_id && !values.context_meeting_id) {
      ctx.addIssue({
        code: "custom",
        path: ["context_task_id"],
        message: "Attach the reminder to a task or a meeting.",
      });
    }
  });
