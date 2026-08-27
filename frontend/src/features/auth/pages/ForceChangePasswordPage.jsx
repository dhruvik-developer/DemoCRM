import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import AuthLayout from "@/layouts/AuthLayout";
import FormField from "@/components/forms/FormField";
import { changePasswordSchema } from "@/schemas/auth.schema";
import { changePasswordRequest } from "@/features/auth/api";
import { normalizeApiError } from "@/utils/errors";
import { useAuth } from "@/hooks/useAuth";

export default function ForceChangePasswordPage() {
  const navigate = useNavigate();
  const { refreshProfile, logout } = useAuth();
  const [formError, setFormError] = useState("");

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
      await changePasswordRequest({
        old_password: values.old_password,
        new_password: values.new_password,
      });
      await refreshProfile?.();
      navigate("/", { replace: true });
    } catch (error) {
      const normalized = error.normalized ?? normalizeApiError(error);
      if (normalized.fieldErrors?.old_password) {
        setError("old_password", { message: normalized.fieldErrors.old_password[0] });
      } else if (normalized.fieldErrors?.new_password) {
        setError("new_password", { message: normalized.fieldErrors.new_password[0] });
      }
      if (normalized.message && normalized.message.toLowerCase().includes("old password")) {
        setError("old_password", { message: normalized.message });
      }
      setFormError(normalized.message || "Could not change the password. Check your current password and try again.");
    }
  };

  return (
    <AuthLayout
      title="Change your password"
      subtitle="You are using a temporary password. Please set a new one to continue."
    >
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <div className="rounded-md bg-amber-50 p-3 text-sm text-amber-800 border border-amber-200">
          Your account was created by an Admin/Manager. For security, you must change the temporary password on first login.
        </div>

        <FormField id="old_password" label="Current (temporary) password" error={errors.old_password?.message}>
          <Input id="old_password" type="password" autoComplete="current-password" {...register("old_password")} />
        </FormField>

        <FormField id="new_password" label="New password" error={errors.new_password?.message}>
          <Input id="new_password" type="password" autoComplete="new-password" {...register("new_password")} />
        </FormField>

        <FormField id="confirm_new_password" label="Confirm new password" error={errors.confirm_new_password?.message}>
          <Input id="confirm_new_password" type="password" autoComplete="new-password" {...register("confirm_new_password")} />
        </FormField>

        {formError ? (
          <p role="alert" className="text-sm text-destructive">
            {formError}
          </p>
        ) : null}

        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Saving\u2026" : "Set new password and continue"}
        </Button>

        <Button type="button" variant="ghost" onClick={logout}>
          Log out
        </Button>
      </form>
    </AuthLayout>
  );
}
