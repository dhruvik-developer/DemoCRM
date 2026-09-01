// Renders a dynamic form from CallForms template field definitions.
// Types: text, textarea, number, boolean, date, time, datetime, select, radio, checkbox, file.

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
  onDelete,
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
        const value = values[field.field_key] ?? (field.field_type === "checkbox" ? [] : "");
        const fieldError = errors[field.field_key];
        const autoSelect = field.validation_rules?.auto_select === true;
        const fileTypes = field.validation_rules?.file_types ?? "";

        return (
          <div
            key={field.id ?? field.field_key}
            className="flex flex-col gap-1.5 rounded-lg border bg-card p-3.5 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <label htmlFor={id} className="text-sm font-semibold text-foreground">
                {field.label}
                {field.is_required ? <span className="text-destructive"> *</span> : null}
                {autoSelect ? <span className="ml-2 text-[10px] font-normal text-muted-foreground">(auto)</span> : null}
              </label>
              <div className="flex items-center gap-2">
                {onDelete && String(field.id ?? "").startsWith("adhoc_") ? (
                  <button type="button" onClick={() => onDelete(field.field_key)} className="text-[11px] text-destructive hover:underline">Delete</button>
                ) : null}
                <span className="text-[11px] font-medium text-muted-foreground px-2 py-0.5 bg-muted rounded">
                  Step {index + 1} of {fields.length}
                </span>
              </div>
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
              <Select value={String(value)} onValueChange={(next) => set(field.field_key, next)}>
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
            ) : field.field_type === "radio" ? (
              <div className="flex flex-col gap-1.5 pt-1" role="radiogroup">
                {(field.options ?? []).map((option) => (
                  <label key={String(option)} className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="radio"
                      name={id}
                      value={String(option)}
                      checked={String(value) === String(option)}
                      onChange={() => set(field.field_key, String(option))}
                      className="h-4 w-4 text-primary"
                    />
                    <span>{String(option)}</span>
                  </label>
                ))}
              </div>
            ) : field.field_type === "checkbox" ? (
              <div className="flex flex-col gap-1.5 pt-1">
                {(field.options ?? []).map((option) => {
                  const arr = Array.isArray(value) ? value : [];
                  const checked = arr.map(String).includes(String(option));
                  return (
                    <label key={String(option)} className="flex items-center gap-2 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => {
                          const next = e.target.checked
                            ? [...arr, String(option)]
                            : arr.filter((v) => String(v) !== String(option));
                          set(field.field_key, next);
                        }}
                        className="h-4 w-4 rounded border-gray-300 text-primary"
                      />
                      <span>{String(option)}</span>
                    </label>
                  );
                })}
              </div>
            ) : field.field_type === "file" ? (
              <div className="flex flex-col gap-1">
                <Input
                  id={id}
                  type="file"
                  multiple={field.validation_rules?.max_files !== 1}
                  accept={fileTypes ? fileTypes.split(",").map((t) => `.${t.trim()}`).join(",") : undefined}
                  className={fieldError ? "border-destructive" : ""}
                  onChange={(e) => {
                    const files = Array.from(e.target.files ?? []).map((f) => f.name);
                    const maxFiles = field.validation_rules?.max_files ?? 3;
                    const limited = files.slice(0, maxFiles);
                    set(field.field_key, limited.length === 1 ? limited[0] : limited);
                  }}
                />
                {fileTypes ? <p className="text-[11px] text-muted-foreground">Allowed: {fileTypes}</p> : null}
                {value ? <p className="text-xs text-muted-foreground truncate">Selected: {Array.isArray(value) ? value.join(", ") : String(value)}</p> : null}
              </div>
            ) : (
              <Input
                id={id}
                type={
                  field.field_type === "number"
                    ? "number"
                    : field.field_type === "datetime"
                      ? "datetime-local"
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
