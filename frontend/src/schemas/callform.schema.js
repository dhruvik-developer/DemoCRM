import { z } from "zod";

// Mirrors CallForms serializers: field_key regex ^[a-z0-9_]+$, SELECT fields
// require non-empty options, template names are case-insensitively unique.

export const callTemplateSchema = z.object({
  name: z.string().trim().min(1, "Name is required."),
});

export const callFieldSchema = z
  .object({
    field_key: z
      .string()
      .trim()
      .regex(/^[a-z0-9_]+$/, "Lowercase letters, digits and underscores only."),
    label: z.string().trim().min(1, "Label is required."),
    field_type: z.enum(["text", "textarea", "number", "boolean", "date", "time", "datetime", "select", "radio", "checkbox", "file"]),
    is_required: z.boolean(),
    help_text: z.string().trim().optional().or(z.literal("")),
    options_text: z.string().optional().or(z.literal("")),
    file_types: z.string().optional().or(z.literal("")),
    max_files: z.coerce.number().int().min(1).max(10).optional(),
    auto_select: z.boolean().optional(),
  })
  .refine((values) => !["select", "radio", "checkbox"].includes(values.field_type) || (values.options_text ?? "").trim() !== "", {
    message: "SELECT/RADIO/CHECKBOX fields need at least one option.",
    path: ["options_text"],
  });

export const triggerRuleSchema = z.object({
  version: z.string().uuid("Select a template version."),
  trigger_condition: z.enum(["ALWAYS", "FOLLOW_UP_REQUIRED", "OUTCOME_MATCH", "FIELD_VALUE_MATCH"]),
  task_title_template: z.string().trim().min(1, "Title template is required."),
  due_days_offset: z.coerce.number().int().min(0),
  assignee_rule: z.enum(["CONDUCTING_AGENT", "LEAD_OWNER", "SPECIFIC_USER"]),
  create_reminder: z.boolean(),
});

export const adhocProposalSchema = z.object({
  template_version: z.string().uuid("Select a template version."),
  field_key: z
    .string()
    .trim()
    .regex(/^[a-z0-9_]+$/, "Lowercase letters, digits and underscores only."),
  label: z.string().trim().min(1, "Label is required."),
});
