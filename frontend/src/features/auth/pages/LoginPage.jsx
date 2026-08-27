import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import AuthLayout from "@/layouts/AuthLayout";
import FormField from "@/components/forms/FormField";
import { loginSchema } from "@/schemas/auth.schema";
import { useAuth } from "@/hooks/useAuth";
import { normalizeApiError } from "@/utils/errors";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [formError, setFormError] = useState("");

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = async (values) => {
    setFormError("");
    try {
      const tokens = await login(values);
      // If backend signals must_change_password, force redirect to change screen
      if (tokens?.must_change_password) {
        navigate("/force-change-password", { replace: true });
        return;
      }
      const redirectTo = location.state?.from?.pathname ?? "/";
      navigate(redirectTo, { replace: true });
    } catch (error) {
      const normalized = error.normalized ?? normalizeApiError(error);
      for (const [field, messages] of Object.entries(normalized.fieldErrors)) {
        if (field in loginSchema.shape) {
          setError(field, { message: messages[0] });
        }
      }
      if (normalized.status === 401 || !normalized.fieldErrors) {
        setFormError(
          normalized.message || "Invalid email or password.",
        );
      }
    }
  };

  return (
    <AuthLayout title="CRM" subtitle="Sign in to your account">
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <FormField id="email" label="Email" error={errors.email?.message}>
          <Input
            id="email"
            type="email"
            placeholder="you@company.com"
            autoComplete="email"
            {...register("email")}
          />
        </FormField>

        <FormField id="password" label="Password" error={errors.password?.message}>
          <Input
            id="password"
            type="password"
            placeholder="••••••••"
            autoComplete="current-password"
            {...register("password")}
          />
        </FormField>

        {formError ? (
          <p role="alert" className="text-sm text-destructive">
            {formError}
          </p>
        ) : null}

        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing in..." : "Sign in"}
        </Button>

        <div className="flex items-center justify-between text-sm">
          <Link to="/forgot-password" className="text-muted-foreground hover:underline">
            Forgot password?
          </Link>
          <span className="text-muted-foreground text-xs">New employee? Ask admin for your temporary password.</span>
        </div>
      </form>
    </AuthLayout>
  );
}
