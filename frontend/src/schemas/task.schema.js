import { z } from "zod";

// Mirrors TaskSerializer / Task.clean rules:
// - task_title strip-required, 3–200 chars
// - lead REQUIRED
// - if customer is set it must belong to that lead (rule #12) — v1 UI does
//   not offer customer selection on create, so this cannot be violated
// - due_date, when provided, must not be in the past

export const taskSchema = z.object({
  task_title: z
    .string()
    .trim()
    .min(3, "Title must be at least 3 characters.")
    .max(200, "Title must be at most 200 characters."),
  description: z.string().trim().max(5000).optional().or(z.literal("")),
  lead: z.string().uuid("A lead is required for every task."),
  status: z.union([z.string(), z.number()]).optional(),
  priority: z.union([z.string(), z.number()]).optional(),
  category: z.union([z.string(), z.number()]).optional(),
  assigned_to: z.string().optional().or(z.literal("")),
  due_date: z
    .string()
    .optional()
    .or(z.literal(""))
    .refine((value) => {
      if (!value) return true;
      const parsed = new Date(value);
      return !Number.isNaN(parsed.getTime()) && parsed.getTime() > Date.now();
    }, "The due date must be in the future."),
});

export const assignTaskSchema = z.object({
  // G6: manual UUID until a user-list endpoint ships.
  assigned_to: z.string().uuid("Enter a valid user UUID."),
});
