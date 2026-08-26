// Shared form field wrapper: label + control + inline error + optional help.

import { Label } from "@/components/ui/label";

export default function FormField({ id, label, error, help, children }) {
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {help && !error ? (
        <p className="text-xs text-muted-foreground">{help}</p>
      ) : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </div>
  );
}
