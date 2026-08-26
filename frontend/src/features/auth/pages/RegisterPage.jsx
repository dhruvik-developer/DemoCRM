import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import AuthLayout from "@/layouts/AuthLayout";
import FormField from "@/components/forms/FormField";
import { registerSchema } from "@/schemas/auth.schema";
import { registerRequest } from "@/features/auth/api";
import { normalizeApiError } from "@/utils/errors";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [formError, setFormError] = useState("");

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(registerSchema),
    defaultValues: { username: "", email: "", phone_number: "", password: "" },
  });

  const onSubmit = async (values) => {
    setFormError("");
    try {
      await registerRequest(values);
      navigate("/login", {
        replace: true,
        state: { registeredEmail: values.email },
      });
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
    <AuthLayout title="Create account" subtitle="Register to get started">
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <FormField id="username" label="Username" error={errors.username?.message}>
          <Input id="username" autoComplete="username" {...register("username")} />
        </FormField>

        <FormField id="email" label="Email" error={errors.email?.message}>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            {...register("email")}
          />
        </FormField>

        <FormField id="phone_number" label="Phone number" error={errors.phone_number?.message}>
          <Input
            id="phone_number"
            inputMode="numeric"
            maxLength={10}
            placeholder="10-digit number"
            {...register("phone_number")}
          />
        </FormField>

        <FormField id="password" label="Password" error={errors.password?.message}>
          <Input
            id="password"
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

        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creating account…" : "Create account"}
        </Button>

        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link to="/login" className="hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}
