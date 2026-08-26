import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import AuthLayout from "@/layouts/AuthLayout";
import FormField from "@/components/forms/FormField";
import { forgotPasswordSchema } from "@/schemas/auth.schema";
import { forgotPasswordRequest } from "@/features/auth/api";

export default function ForgotPasswordPage() {
  const [sentTo, setSentTo] = useState("");
  const [formError, setFormError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  const onSubmit = async (values) => {
    setFormError("");
    try {
      await forgotPasswordRequest(values);
      setSentTo(values.email);
    } catch {
      // Don't leak whether an email exists — show the generic sent state and
      // carry on; reset errors surface on the reset screen itself.
      setSentTo(values.email);
    }
  };

  if (sentTo) {
    return (
      <AuthLayout title="Check your email">
        <div className="flex flex-col gap-4 text-center text-sm text-muted-foreground">
          <p>
            If an account exists for <span className="font-medium">{sentTo}</span>, a
            6-digit OTP has been sent. It expires in 10 minutes and can be used once.
          </p>
          <Button asChild variant="outline">
            <Link to="/reset-password">Enter OTP</Link>
          </Button>
          <Link to="/login" className="hover:underline">
            Back to sign in
          </Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Forgot password?"
      subtitle="We'll email you a one-time password (OTP)"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <FormField id="email" label="Email" error={errors.email?.message}>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            {...register("email")}
          />
        </FormField>

        {formError ? (
          <p role="alert" className="text-sm text-destructive">
            {formError}
          </p>
        ) : null}

        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Sending…" : "Send OTP"}
        </Button>

        <p className="text-center text-sm text-muted-foreground">
          Remembered it?{" "}
          <Link to="/login" className="hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}
