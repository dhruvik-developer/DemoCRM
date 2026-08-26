import { z } from "zod";

// Mirrors MeetingCreateView / serializer rules:
// - meeting_title strip-required (≥3)
// - meeting_date not in the past
// - end_time strictly after start_time
// - manager UUID required and must have the Manager role server-side (400 otherwise)

export const createMeetingSchema = z
  .object({
    task_id: z.coerce.number({ message: "Task ID is required." }).int().positive(),
    lead: z.string().uuid().optional().or(z.literal("")),
    meeting_title: z.string().trim().min(3, "Title must be at least 3 characters."),
    meeting_date: z
      .string()
      .min(1, "Date is required.")
      .refine((value) => {
        const parsed = new Date(`${value}T23:59:59`);
        return !Number.isNaN(parsed.getTime()) && parsed.getTime() >= Date.now() - 60000;
      }, "The date cannot be in the past."),
    start_time: z.string().min(1, "Start time is required."),
    end_time: z.string().min(1, "End time is required."),
    meeting_type_id: z.coerce.number().int(),
    location: z.string().trim().max(255).optional().or(z.literal("")),
    description: z.string().trim().max(2000).optional().or(z.literal("")),
    manager: z.string().uuid("Enter the manager's user UUID."),
  })
  .superRefine((values, ctx) => {
    if (values.start_time && values.end_time && values.end_time <= values.start_time) {
      ctx.addIssue({
        code: "custom",
        path: ["end_time"],
        message: "End time must be after the start time.",
      });
    }
  });

export const approvalDecisionSchema = z.object({
  rejection_reason: z.string().trim().max(500).optional().or(z.literal("")),
});

export const rescheduleMeetingSchema = z.object({
  meeting_date: z.string().optional().or(z.literal("")),
  start_time: z.string().optional().or(z.literal("")),
  end_time: z.string().optional().or(z.literal("")),
  location: z.string().trim().max(255).optional().or(z.literal("")),
});
