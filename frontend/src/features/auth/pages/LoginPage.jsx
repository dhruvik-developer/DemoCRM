import { useEffect, useState, useRef } from "react";
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
import { Clock, ShieldAlert } from "lucide-react";

function formatCountdown(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const mins = Math.floor(s / 60);
  const secs = s % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [formError, setFormError] = useState("");
  const [lockInfo, setLockInfo] = useState(null); // { code, retryAfter, remaining, isPermanent }
  const intervalRef = useRef(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  // live countdown for cooldown lock
  useEffect(() => {
    if (!lockInfo || lockInfo.isPermanent || lockInfo.remaining <= 0) return;
    intervalRef.current = setInterval(() => {
      setLockInfo((prev) => {
        if (!prev || prev.isPermanent) return prev;
        const next = prev.remaining - 1;
        if (next <= 0) {
          clearInterval(intervalRef.current);
          return null; // auto-clear when countdown finishes
        }
        return { ...prev, remaining: next };
      });
    }, 1000);
    return () => clearInterval(intervalRef.current);
  }, [lockInfo]);

  const onSubmit = async (values) => {
    // prevent submit while cooldown active
    if (lockInfo && !lockInfo.isPermanent && lockInfo.remaining > 0) {
      return;
    }
    setFormError("");
    try {
      const tokens = await login(values);
      // clear any previous lock on success
      setLockInfo(null);
      clearInterval(intervalRef.current);
      // If backend signals must_change_password, force redirect to change screen
      if (tokens?.must_change_password) {
        navigate("/force-change-password", { replace: true });
        return;
      }
      const redirectTo = location.state?.from?.pathname ?? "/";
      navigate(redirectTo, { replace: true });
    } catch (error) {
      const data = error?.response?.data;
      const status = error?.response?.status;
      const code = data?.code;

      // 429 cooldown -> show live timer
      if (status === 429 && code === "login_cooldown") {
        const retryAfter = Number(data?.retry_after ?? 600);
        setLockInfo({
          code,
          retryAfter,
          remaining: retryAfter,
          isPermanent: false,
        });
        setFormError(""); // lock card will show message
        return;
      }

      // 403 permanent lock
      if (status === 403 && code === "account_locked") {
        setLockInfo({
          code,
          retryAfter: 0,
          remaining: 0,
          isPermanent: true,
        });
        setFormError("");
        return;
      }

      // also handle blocked returned as 403 cooldown edge (pre-check in view)
      if (status === 429 || status === 403) {
        // fallback: if message contains retry_after but no code
        if (data?.retry_after) {
          const retryAfter = Number(data.retry_after);
          setLockInfo({
            code: code || "login_cooldown",
            retryAfter,
            remaining: retryAfter,
            isPermanent: false,
          });
          setFormError("");
          return;
        }
      }

      const normalized = error.normalized ?? normalizeApiError(error);
      for (const [field, messages] of Object.entries(normalized.fieldErrors)) {
        if (field in loginSchema.shape) {
          setError(field, { message: messages[0] });
        }
      }
      if (normalized.status === 401 || normalized.status === 0 || !Object.keys(normalized.fieldErrors).length) {
        // for 400/401/403 without lock code, show generic message
        // but avoid overriding lockInfo already set
        if (!lockInfo) {
          setFormError(normalized.message || "Invalid email or password.");
        }
      }
    }
  };

  const isCooldownActive = lockInfo && !lockInfo.isPermanent && lockInfo.remaining > 0;
  const isPermanentlyLocked = lockInfo?.isPermanent;

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

        {/* Cooldown lock with live timer */}
        {isCooldownActive ? (
          <div
            role="alert"
            className="flex flex-col gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-3 text-sm text-amber-900 dark:bg-amber-950/30 dark:text-amber-200"
          >
            <div className="flex items-center gap-2 font-medium">
              <Clock className="h-4 w-4" />
              Too many failed attempts — blocked for 10 minutes
            </div>
            <p className="text-xs leading-relaxed">
              You entered wrong credentials 5 times. Please try again after the timer ends.
              Server says: Please try again in {Math.ceil(lockInfo.remaining / 60)} minute(s).
            </p>
            <div className="flex items-center justify-between rounded bg-white dark:bg-black/20 px-3 py-2">
              <span className="text-xs font-medium text-muted-foreground">Time remaining</span>
              <span className="font-mono text-lg font-bold tabular-nums">
                {formatCountdown(lockInfo.remaining)}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Next wrong attempt after cooldown will lock account permanently until Admin unlocks.
            </p>
          </div>
        ) : null}

        {/* Permanent lock */}
        {isPermanentlyLocked ? (
          <div
            role="alert"
            className="flex flex-col gap-2 rounded-md border border-destructive/50 bg-destructive/10 px-3 py-3 text-sm text-destructive"
          >
            <div className="flex items-center gap-2 font-medium">
              <ShieldAlert className="h-4 w-4" />
              Account permanently locked
            </div>
            <p className="text-xs leading-relaxed">
              Account locked due to repeated failed login attempts. Contact your Admin/Manager to unlock
              via <span className="font-mono">Admin Panel → Overview → Unlock User</span> or{" "}
              <span className="font-mono">Administration → Employees → Unlock</span>.
            </p>
          </div>
        ) : null}

        {/* Generic form error (401 etc.) - hidden when lock card is shown */}
        {formError && !isCooldownActive && !isPermanentlyLocked ? (
          <p role="alert" className="text-sm text-destructive">
            {formError}
          </p>
        ) : null}

        <Button type="submit" disabled={isSubmitting || isCooldownActive}>
          {isCooldownActive
            ? `Blocked — try in ${formatCountdown(lockInfo.remaining)}`
            : isSubmitting
              ? "Signing in..."
              : "Sign in"}
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
