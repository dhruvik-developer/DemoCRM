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

export default function DynamicFormFields({ fields, values, onChange }) {
  if (!fields?.length) {
    return <p className="text-sm text-muted-foreground">This form has no fields.</p>;
  }

  const set = (key, value) => onChange({ ...values, [key]: value });

  return (
    <div className="flex flex-col gap-4">
      {fields.map((field) => {
        const id = `dyn_${field.field_key}`;
        const value = values[field.field_key] ?? "";

        return (
          <div key={field.id ?? field.field_key} className="flex flex-col gap-1">
            <label htmlFor={id} className="text-sm font-medium">
              {field.label}
              {field.is_required ? <span className="text-destructive"> *</span> : null}
            </label>

            {field.field_type === "textarea" ? (
              <Textarea id={id} rows={2} value={value} onChange={(e) => set(field.field_key, e.target.value)} />
            ) : field.field_type === "boolean" ? (
              <label className="flex items-center gap-2 text-sm">
                <input
                  id={id}
                  type="checkbox"
                  className="h-4 w-4"
                  checked={Boolean(value)}
                  onChange={(e) => set(field.field_key, e.target.checked)}
                />
                Yes
              </label>
            ) : field.field_type === "select" ? (
              <Select value={value} onValueChange={(next) => set(field.field_key, next)}>
                <SelectTrigger id={id}>
                  <SelectValue placeholder="Select…" />
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
                onChange={(e) => set(field.field_key, e.target.value)}
              />
            )}

            {field.help_text ? (
              <p className="text-xs text-muted-foreground">{field.help_text}</p>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

