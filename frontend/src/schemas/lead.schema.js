import { z } from "zod";

// Mirrors LeadSerializer validation (frontend/docs/API_CONTRACT.md):
// - phone regex ^[0-9+\-()\s]{7,20}$
// - source/pipeline/current_stage must reference active records
// - on CREATE the backend enforces current_stage === pipeline's first stage;
//   the create form auto-selects it instead of asking the user.

export const leadSchema = z.object({
  name: z.string().trim().min(1, "Name is required."),
  email: z
    .string()
    .trim()
    .refine((value) => value === "" || z.email().safeParse(value).success, {
      message: "Enter a valid email address.",
    }),
  phone: z
    .string()
    .trim()
    .regex(/^[0-9+\-()\s]{7,20}$/, "Enter a valid phone number (7–20 characters)."),
  company_name: z.string().trim().max(255).optional().or(z.literal("")),
  source: z.string().uuid("Select a lead source."),
  pipeline: z.string().uuid("Select a pipeline."),
  total_value: z
    .string()
    .optional()
    .or(z.literal(""))
    .refine((value) => value === "" || !Number.isNaN(Number(value)), {
      message: "Enter a numeric value.",
    }),
});

export const assignLeadSchema = z.object({
  // No GET /users/ endpoint exists yet (BACKEND_GAPS.md G6) — v1 uses manual
  // UUID entry until a user-list endpoint ships.
  assigned_to: z.string().uuid("Enter a valid user UUID."),
});

export const lostLeadSchema = z.object({
  lost_reason: z.string().trim().min(1, "A reason is required to mark a lead lost."),
});

export const convertLeadSchema = z.object({
  name: z.string().trim().min(1, "Name is required."),
  email: z.email({ message: "Enter a valid email address." }),
  phone: z
    .string()
    .trim()
    .regex(/^[0-9+\-()\s]{7,20}$/, "Enter a valid phone number (7–20 characters)."),
  company_name: z.string().trim().max(255).optional().or(z.literal("")),
  gst_number: z.string().trim().max(15).optional().or(z.literal("")),
});
