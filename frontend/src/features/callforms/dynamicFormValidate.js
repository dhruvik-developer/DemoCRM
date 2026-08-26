// Client-side required-field check for dynamic CallForms data. The server
// re-validates (including select options) — this is UX only.
// Kept out of DynamicFormFields.jsx so that file stays component-only
// (react-refresh rule).

export function validateDynamicData(fields, data) {
  const errors = {};
  for (const field of fields ?? []) {
    if (
      field.is_required &&
      (data[field.field_key] === "" || data[field.field_key] == null)
    ) {
      errors[field.field_key] = `${field.label} is required.`;
    }
  }
  return errors;
}
