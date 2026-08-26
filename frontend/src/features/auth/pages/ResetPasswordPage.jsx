import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import AuthLayout from "@/layouts/AuthLayout";
import FormField from "@/components/forms/FormField";
import { resetPasswordSchema } from "@/schemas/auth.schema";
import { resetPasswordRequest } from "@/features/auth/api";
import { normalizeApiError } from "@/utils/errors";

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [formError, setFormError] = useState("");

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { email: "", otp: "", new_password: "", confirm_password: "" },
  });

  const onSubmit = async (values) => {
    setFormError("");
    try {
      // Backend contract: { email, otp, new_password } — confirm field is UI-only.
      await resetPasswordRequest({
        email: values.email,
        otp: values.otp,
        new_password: values.new_password,
      });
      navigate("/login", {
        replace: true,
        state: { passwordReset: true },
      });
    } catch (error) {
      const normalized = error.normalized ?? normalizeApiError(error);
      for (const [field, messages] of Object.entries(normalized.fieldErrors)) {
        if (field in resetPasswordSchema.shape) {
          setError(field, { message: messages[0] });
        }
      }
      setFormError(
        normalized.message ||
          "Could not reset the password. Check the OTP and try again.",
      );
    }
  };

  return (
    <AuthLayout
      title="Reset password"
      subtitle="Enter the 6-digit OTP emailed to you (valid for 10 minutes)"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <FormField id="email" label="Email" error={errors.email?.message}>
          <Input id="email" type="email" autoComplete="email" {...register("email")} />
        </FormField>

        <FormField id="otp" label="OTP" error={errors.otp?.message}>
          <Input
            id="otp"
            inputMode="numeric"
            maxLength={6}
            placeholder="6-digit code"
            className="tracking-[0.5em]"
            {...register("otp")}
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
          id="confirm_password"
          label="Confirm new password"
          error={errors.confirm_password?.message}
        >
          <Input
            id="confirm_password"
            type="password"
            autoComplete="new-password"
            {...register("confirm_password")}
          />
        </FormField>

        {formError ? (
          <p role="alert" className="text-sm text-destructive">
            {formError}
          </p>
        ) : null}

        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Resetting…" : "Reset password"}
        </Button>

        <p className="text-center text-sm text-muted-foreground">
          Didn't get the OTP?{" "}
          <Link to="/forgot-password" className="hover:underline">
            Resend
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}
