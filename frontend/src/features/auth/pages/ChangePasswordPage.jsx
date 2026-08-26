import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import FormField from "@/components/forms/FormField";
import { changePasswordSchema } from "@/schemas/auth.schema";
import { changePasswordRequest } from "@/features/auth/api";
import { normalizeApiError } from "@/utils/errors";

// Rendered as a page/modal under the authenticated area.
export default function ChangePasswordPage({ onSuccess }) {
  const [formError, setFormError] = useState("");
  const [succeeded, setSucceeded] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { old_password: "", new_password: "", confirm_new_password: "" },
  });

  const onSubmit = async (values) => {
    setFormError("");
    try {
      // Backend contract: { old_password, new_password } — confirm is UI-only.
      await changePasswordRequest({
        old_password: values.old_password,
        new_password: values.new_password,
      });
      setSucceeded(true);
      onSuccess?.();
    } catch (error) {
      const normalized = error.normalized ?? normalizeApiError(error);
      if (normalized.fieldErrors.old_password) {
        setError("old_password", { message: normalized.fieldErrors.old_password[0] });
      } else if (normalized.fieldErrors.new_password) {
        setError("new_password", { message: normalized.fieldErrors.new_password[0] });
      }
      setFormError(normalized.message || "Could not change the password.");
    }
  };

  if (succeeded) {
    return (
      <div className="flex flex-col gap-3 text-sm">
        <p className="font-medium">Password changed successfully.</p>
        <Button variant="outline" onClick={() => setSucceeded(false)}>
          Change again
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
      <FormField id="old_password" label="Current password" error={errors.old_password?.message}>
        <Input
          id="old_password"
          type="password"
          autoComplete="current-password"
          {...register("old_password")}
        />
      </FormField>

      <FormField id="new_password" label="New password" error={errors.new_password?.message}>
        <Input
          id="new_password"
          type="password"
          autoComplete="new-password"
          {...register("new_password")}
        />
      </FormField>

      <FormField
        id="confirm_new_password"
        label="Confirm new password"
        error={errors.confirm_new_password?.message}
      >
        <Input
          id="confirm_new_password"
          type="password"
          autoComplete="new-password"
          {...register("confirm_new_password")}
        />
      </FormField>

      {formError ? (
        <p role="alert" className="text-sm text-destructive">
          {formError}
        </p>
      ) : null}

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Saving…" : "Change password"}
      </Button>
    </form>
  );
}
