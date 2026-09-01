// Client-side required-field check for dynamic CallForms data. The server
// re-validates (including select options) — this is UX only.
// Kept out of DynamicFormFields.jsx so that file stays component-only
// (react-refresh rule).

export function validateDynamicData(fields, data) {
  const errors = {};
  for (const field of fields ?? []) {
    const val = data[field.field_key];
    const empty = val === "" || val == null || (Array.isArray(val) && val.length === 0);
    if (field.is_required && empty) {
      errors[field.field_key] = `${field.label} is required.`;
      continue;
    }
    if (!empty && field.validation_rules?.file_types && field.field_type === "file") {
      const allowed = String(field.validation_rules.file_types).split(",").map((s) => s.trim().toLowerCase().replace(".", "")).filter(Boolean);
      const vals = Array.isArray(val) ? val : [val];
      for (const v of vals) {
        const ext = String(v).split(".").pop()?.toLowerCase() ?? "";
        if (allowed.length && ext && !allowed.includes(ext)) {
          errors[field.field_key] = `File type .${ext} not allowed. Allowed: ${allowed.join(", ")}`;
          break;
        }
      }
    }
  }
  return errors;
}
