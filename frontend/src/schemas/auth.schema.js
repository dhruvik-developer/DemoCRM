import { z } from "zod";

// Mirrors backend accounts serializers (see frontend/docs/AUTH_CONTRACT.md).
// Note: register does NOT run validate_password server-side — weak passwords
// are accepted. The min-length rule here is UX guidance only.

export const loginSchema = z.object({
  email: z.string().min(1, "Email is required.").email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});

export const registerSchema = z.object({
  username: z.string().trim().min(1, "Username is required.").max(100),
  email: z.string().min(1, "Email is required.").email("Enter a valid email address."),
  phone_number: z
    .string()
    .trim()
    .regex(/^\d{10}$/, "Phone number must be exactly 10 digits."),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters.")
    .regex(/[a-zA-Z]/, "Password must contain at least one letter.")
    .refine((value) => !/^\d+$/.test(value), "Password cannot be all numbers."),
});

export const forgotPasswordSchema = z.object({
  email: z.string().min(1, "Email is required.").email("Enter a valid email address."),
});

export const resetPasswordSchema = z
  .object({
    email: z.string().min(1, "Email is required.").email("Enter a valid email address."),
    otp: z.string().regex(/^\d{6}$/, "OTP must be exactly 6 digits."),
    new_password: z
      .string()
      .min(8, "Password must be at least 8 characters.") // backend enforces validate_password here
      .regex(/[a-zA-Z]/, "Password must contain at least one letter.")
      .refine((value) => !/^\d+$/.test(value), "Password cannot be all numbers."),
    confirm_password: z.string().min(1, "Please confirm the password."),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });

export const changePasswordSchema = z
  .object({
    old_password: z.string().min(1, "Current password is required."),
    new_password: z
      .string()
      .min(8, "Password must be at least 8 characters.")
      .regex(/[a-zA-Z]/, "Password must contain at least one letter.")
      .refine((value) => !/^\d+$/.test(value), "Password cannot be all numbers."),
    confirm_new_password: z.string().min(1, "Please confirm the new password."),
  })
  .refine((data) => data.new_password === data.confirm_new_password, {
    message: "Passwords do not match.",
    path: ["confirm_new_password"],
  });
