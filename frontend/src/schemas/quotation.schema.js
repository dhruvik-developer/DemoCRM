import { z } from "zod";

// Mirrors QuotationVersion.clean: total_amount must equal
// sum(quantity * unit_price) — enforced client-side in the draft editor too.

export const lineItemSchema = z.object({
  description: z.string().trim().min(1, "Description is required."),
  quantity: z.preprocess(
    (val) => (val === "" || val === undefined || val === null ? undefined : Number(val)),
    z
      .number({ message: "Quantity is required." })
      .min(1, "Quantity must be at least 1.")
      .refine((val) => Number.isInteger(val), {
        message: "Quantity must be a whole number.",
      }),
  ),
  unit_price: z.coerce
    .number({ message: "Unit price is required." })
    .min(0.01, "Unit price must be at least 0.01."),
});

export const createQuotationSchema = z.object({
  lead_id: z.string().uuid("A lead is required (quotations are created from ACTIVE leads)."),
  terms: z.string().trim().max(5000).optional().or(z.literal("")),
  notes: z.string().trim().max(2000).optional().or(z.literal("")),
  line_items: z.array(lineItemSchema).default([]),
});

export const draftUpdateSchema = z.object({
  terms: z.string().trim().max(5000).optional().or(z.literal("")),
  notes: z.string().trim().max(2000).optional().or(z.literal("")),
  line_items: z.array(lineItemSchema),
});

export const rejectQuotationSchema = z.object({
  rejection_reason: z.string().trim().min(1, "A reason is required."),
});

export const sendEmailSchema = z.object({
  recipient_email: z.email({ message: "Enter a valid email address." }),
  subject: z.string().trim().optional().or(z.literal("")),
  body: z.string().trim().optional().or(z.literal("")),
});
