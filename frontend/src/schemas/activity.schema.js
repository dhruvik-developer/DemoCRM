import { z } from "zod";

// Mirrors ActivitySerializer + CRMService.create_activity rules:
// - exactly one of lead/customer (enforced by which page opens the dialog —
//   the dialog receives the fixed id and never asks)
// - outcome required, max 255 chars
// - follow_up_required ⇒ follow_up_date required AND in the future
// - CONVERTED leads cannot receive new activities (UI hides the button)

export const MANUAL_ACTIVITY_TYPES = ["CALL", "EMAIL", "MEETING", "DEMO", "FOLLOW_UP"];

export const activitySchema = z
  .object({
    activity_type: z.enum(MANUAL_ACTIVITY_TYPES, {
      message: "Select an activity type.",
    }),
    outcome: z.string().trim().min(1, "Outcome is required.").max(255),
    notes: z.string().trim().max(2000).optional().or(z.literal("")),
    follow_up_required: z.boolean(),
    follow_up_date: z.string().optional().or(z.literal("")),
  })
  .superRefine((values, ctx) => {
    if (values.follow_up_required) {
      if (!values.follow_up_date) {
        ctx.addIssue({
          code: "custom",
          path: ["follow_up_date"],
          message: "A future date is required when a follow-up is needed.",
        });
        return;
      }
      const parsed = new Date(values.follow_up_date);
      if (Number.isNaN(parsed.getTime())) {
        ctx.addIssue({
          code: "custom",
          path: ["follow_up_date"],
          message: "Enter a valid date and time.",
        });
      } else if (parsed.getTime() <= Date.now()) {
        ctx.addIssue({
          code: "custom",
          path: ["follow_up_date"],
          message: "The follow-up date must be in the future.",
        });
      }
    }
  });
