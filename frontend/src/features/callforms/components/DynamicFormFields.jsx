// Renders a dynamic form from CallForms template field definitions.
// Types: text, textarea, number, boolean, date, time, select.

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

export default function DynamicFormFields({
  fields,
  values,
  errors = {},
  onChange,
  stepView = true,
}) {
  if (!fields?.length) {
    return <p className="text-sm text-muted-foreground">This form has no fields.</p>;
  }

  const set = (key, value) => onChange({ ...values, [key]: value });

  return (
    <div className="flex flex-col gap-4">
      {stepView && fields.length > 1 ? (
        <div className="flex items-center justify-between border-b pb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          <span>Form Fields Workflow</span>
          <span>{fields.length} Step{fields.length > 1 ? "s" : ""}</span>
        </div>
      ) : null}

      {fields.map((field, index) => {
        const id = `dyn_${field.field_key}`;
        const value = values[field.field_key] ?? "";
        const fieldError = errors[field.field_key];

        return (
          <div
            key={field.id ?? field.field_key}
            className="flex flex-col gap-1.5 rounded-lg border bg-card p-3.5 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <label htmlFor={id} className="text-sm font-semibold text-foreground">
                {field.label}
                {field.is_required ? <span className="text-destructive"> *</span> : null}
              </label>
              <span className="text-[11px] font-medium text-muted-foreground px-2 py-0.5 bg-muted rounded">
                Step {index + 1} of {fields.length}
              </span>
            </div>

            {field.field_type === "textarea" ? (
              <Textarea
                id={id}
                rows={2}
                value={value}
                className={fieldError ? "border-destructive focus-visible:ring-destructive" : ""}
                onChange={(e) => set(field.field_key, e.target.value)}
              />
            ) : field.field_type === "boolean" ? (
              <label className="flex items-center gap-2 text-sm cursor-pointer pt-1">
                <input
                  id={id}
                  type="checkbox"
                  className="h-4 w-4 rounded border-gray-300 text-primary"
                  checked={Boolean(value)}
                  onChange={(e) => set(field.field_key, e.target.checked)}
                />
                <span className="font-medium">Yes / Confirmed</span>
              </label>
            ) : field.field_type === "select" ? (
              <Select value={value} onValueChange={(next) => set(field.field_key, next)}>
                <SelectTrigger id={id} className={fieldError ? "border-destructive focus:ring-destructive" : ""}>
                  <SelectValue placeholder="Select option…" />
                </SelectTrigger>
                <SelectContent>
                  {(field.options ?? []).map((option) => (
                    <SelectItem key={String(option)} value={String(option)}>
                      {String(option)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Input
                id={id}
                type={
                  field.field_type === "number"
                    ? "number"
                    : field.field_type // date / time / text map directly
                }
                value={value}
                className={fieldError ? "border-destructive focus-visible:ring-destructive" : ""}
                onChange={(e) => set(field.field_key, e.target.value)}
              />
            )}

            {fieldError ? (
              <p role="alert" className="text-xs text-destructive font-medium mt-0.5">
                {fieldError}
              </p>
            ) : null}

            {field.help_text && !fieldError ? (
              <p className="text-xs text-muted-foreground">{field.help_text}</p>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
