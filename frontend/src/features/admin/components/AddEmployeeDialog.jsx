import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { registerRequest } from "@/features/auth/api";
import { registerSchema } from "@/schemas/auth.schema";
import { normalizeApiError } from "@/utils/errors";
import FormField from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function AddEmployeeDialog({ open, onOpenChange }) {
  const queryClient = useQueryClient();
  const [formError, setFormError] = useState("");

  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(registerSchema),
    defaultValues: { username: "", email: "", phone_number: "", password: "" },
  });

  const handleClose = (value) => {
    reset();
    setFormError("");
    onOpenChange(value);
  };

  const onSubmit = async (values) => {
    setFormError("");
    try {
      await registerRequest(values);
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      toast.success("Employee added successfully.");
      handleClose(false);
    } catch (error) {
      const normalized = error.normalized ?? normalizeApiError(error);
      for (const [field, messages] of Object.entries(normalized.fieldErrors)) {
        if (field in registerSchema.shape) {
          setError(field, { message: messages[0] });
        }
      }
      if (normalized.status !== 400 || !Object.keys(normalized.fieldErrors).length) {
        setFormError(normalized.message || "Registration failed. Please try again.");
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Employee</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-3" noValidate>
          <FormField id="emp_username" label="Username" error={errors.username?.message}>
            <Input id="emp_username" autoComplete="username" {...register("username")} />
          </FormField>

          <FormField id="emp_email" label="Email" error={errors.email?.message}>
            <Input id="emp_email" type="email" autoComplete="email" {...register("email")} />
          </FormField>

          <FormField id="emp_phone" label="Phone number" error={errors.phone_number?.message}>
            <Input
              id="emp_phone"
              inputMode="numeric"
              maxLength={10}
              placeholder="10-digit number"
              {...register("phone_number")}
            />
          </FormField>

          <FormField id="emp_password" label="Password" error={errors.password?.message}>
            <Input
              id="emp_password"
              type="password"
              autoComplete="new-password"
              {...register("password")}
            />
          </FormField>

          {formError ? (
            <p role="alert" className="text-sm text-destructive">
              {formError}
            </p>
          ) : null}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleClose(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Adding…" : "Add Employee"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
