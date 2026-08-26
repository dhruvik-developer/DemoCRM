import { z } from "zod";

// Mirrors FollowUpSerializer rules. NOTE the payload key is `decription`
// (backend typo, G12) — the form field below maps it explicitly.

export const followUpSchema = z.object({
  task_id: z.coerce
    .number({ message: "Task is required." })
    .int()
    .positive("Task is required."),
  followup_status_id: z.coerce.number().int().positive("Select a status."),
  followup_type_id: z.coerce.number().int().positive("Select a type."),
  followup_date: z
    .string()
    .min(1, "Date is required.")
    .refine((value) => {
      const parsed = new Date(value);
      return !Number.isNaN(parsed.getTime()) && parsed.getTime() > Date.now();
    }, "The follow-up date must be in the future."),
  decription: z.string().trim().max(2000).optional().or(z.literal("")),
});
