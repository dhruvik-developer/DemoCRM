// Reusable "Log activity" dialog for both Lead and Customer detail pages.
// Exactly one of leadId/customerId must be provided (backend XOR rule) —
// the dialog receives the fixed id from its page and never asks the user.

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useCreateActivity } from "../hooks";
import { activitySchema, MANUAL_ACTIVITY_TYPES } from "@/schemas/activity.schema";
import FormField from "@/components/forms/FormField";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function toLocalInputValue(date) {
  const pad = (part) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

export default function ActivityCreateDialog({ leadId, customerId, open, onOpenChange }) {
  if (Boolean(leadId) === Boolean(customerId)) {
    throw new Error("ActivityCreateDialog requires exactly one of leadId or customerId.");
  }

  const createActivity = useCreateActivity();
  const [type, setType] = useState("");

  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(activitySchema),
    defaultValues: {
      activity_type: "",
      outcome: "",
      notes: "",
      follow_up_required: false,
      follow_up_date: "",
    },
  });

  const followUpRequired = watch("follow_up_required");

  const onSubmit = async (values) => {
    try {
      await createActivity.mutateAsync({
        ...(leadId ? { lead: leadId } : { customer: customerId }),
        activity_type: values.activity_type,
        outcome: values.outcome,
        notes: values.notes || undefined,
        follow_up_required: values.follow_up_required,
        follow_up_date:
          values.follow_up_required && values.follow_up_date
            ? new Date(values.follow_up_date).toISOString()
            : undefined,
      });
      onOpenChange(false);
    } catch (error) {
      // Business-rule failures arrive as {"detail": "..."} — shown inline.
      const message = error.normalized?.message ?? "Could not log the activity.";
      setError("root", { message });
    }
  };

  const minDate = toLocalInputValue(new Date(Date.now() + 60 * 1000));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Log activity</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <FormField id="activity_type" label="Type" error={errors.activity_type?.message}>
            <Select value={type} onValueChange={(value) => { setType(value); setValue("activity_type", value); }}>
              <SelectTrigger>
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent>
                {MANUAL_ACTIVITY_TYPES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {value.charAt(0) + value.slice(1).toLowerCase().replaceAll("_", " ")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>

          <FormField id="outcome" label="Outcome" error={errors.outcome?.message}>
            <Input id="outcome" maxLength={255} {...register("outcome")} />
          </FormField>

          <FormField id="notes" label="Notes" error={errors.notes?.message}>
            <Textarea id="notes" rows={3} {...register("notes")} />
          </FormField>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="h-4 w-4"
              checked={followUpRequired}
              onChange={(event) => setValue("follow_up_required", event.target.checked)}
            />
            Requires a follow-up
            {/* Backend auto-creates a follow-up Task when this is checked. */}
          </label>

          {followUpRequired ? (
            <FormField
              id="follow_up_date"
              label="Follow-up date"
              error={errors.follow_up_date?.message}
              help="Must be in the future — a follow-up task is created automatically."
            >
              <Input
                id="follow_up_date"
                type="datetime-local"
                min={minDate}
                {...register("follow_up_date")}
              />
            </FormField>
          ) : null}

          {errors.root ? (
            <p role="alert" className="text-sm text-destructive">
              {errors.root.message}
            </p>
          ) : null}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createActivity.isPending}>
              {createActivity.isPending ? "Saving…" : "Log activity"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
