"use client";

import { useState, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { z } from "zod";
import { authClient } from "@/lib/auth-client";
import { AuthInput } from "@/components/auth/auth-input";
import { AuthDivider, GoogleButton } from "@/components/auth/google-button";

const signupSchema = z.object({
  name: z.string().min(1, "Name is required").max(100, "Name is too long"),
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .max(128, "Password is too long"),
});

type FieldErrors = Partial<Record<"name" | "email" | "password", string>>;

export function SignupForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") ?? "/dashboard";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [googleLoading, setGoogleLoading] = useState(false);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    setFieldErrors({});

    const parsed = signupSchema.safeParse({ name, email, password });
    if (!parsed.success) {
      const errors: FieldErrors = {};
      for (const issue of parsed.error.issues) {
        const path = issue.path[0];
        if (path === "name" || path === "email" || path === "password") {
          errors[path] = issue.message;
        }
      }
      setFieldErrors(errors);
      return;
    }

    startTransition(async () => {
      const result = await authClient.signUp.email({
        name: parsed.data.name,
        email: parsed.data.email,
        password: parsed.data.password,
      });

      if (result.error) {
        const mapped = mapAuthError(result.error.message ?? "", result.error.status);
        if (mapped.field) {
          setFieldErrors({ [mapped.field]: mapped.message });
        } else {
          setFormError(mapped.message);
        }
        return;
      }

      router.push(callbackUrl);
      router.refresh();
    });
  };

  const handleGoogle = async () => {
    setFormError(null);
    setGoogleLoading(true);

    const result = await authClient.signIn.social({
      provider: "google",
      callbackURL: callbackUrl,
    });

    if (result.error) {
      setFormError(mapAuthError(result.error.message ?? "", result.error.status).message);
      setGoogleLoading(false);
    }
  };

  const submitting = isPending || googleLoading;

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="space-y-5">
        <AuthInput
          label="Name"
          type="text"
          name="name"
          autoComplete="name"
          placeholder="Jane Doe"
          value={name}
          onChange={(e) => setName(e.target.value)}
          error={fieldErrors.name}
          disabled={submitting}
          required
        />
        <AuthInput
          label="Email"
          type="email"
          name="email"
          autoComplete="email"
          placeholder="you@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={fieldErrors.email}
          disabled={submitting}
          required
        />
        <AuthInput
          label="Password"
          type="password"
          name="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={fieldErrors.password}
          helperText={fieldErrors.password ? undefined : "At least 8 characters."}
          withPasswordToggle
          disabled={submitting}
          required
        />
      </div>

      {formError && (
        <p
          role="alert"
          className="text-caption text-destructive mt-5 font-mono tracking-[0.12em] uppercase"
        >
          {formError}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="bg-foreground font-display text-body-sm text-background mt-8 w-full py-3 font-medium transition-transform duration-200 [transition-timing-function:var(--ease-out-strong)] hover:scale-[1.01] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:scale-100"
      >
        {isPending ? "Creating account..." : "Create account"}
      </button>

      <p className="text-muted-foreground mt-4 text-center font-mono text-[11px] tracking-[0.12em] uppercase">
        By creating an account you agree to our terms and privacy policy.
      </p>

      <AuthDivider />

      <GoogleButton onClick={handleGoogle} disabled={submitting} label="Sign up with Google" />
    </form>
  );
}

interface MappedError {
  message: string;
  /** If set, the error attaches to a specific field instead of the form-level slot. */
  field?: "name" | "email" | "password";
}

/**
 * Maps Better Auth signup error messages into copy that fits the auth chrome voice.
 * Some errors (like "user already exists") are field-specific and surface inline
 * on the email input rather than as a form-level error.
 */
function mapAuthError(message: string, status?: number): MappedError {
  const normalized = message.toLowerCase();

  if (
    normalized.includes("user already exists") ||
    normalized.includes("already registered") ||
    normalized.includes("email already")
  ) {
    return { field: "email", message: "An account with this email already exists." };
  }
  if (normalized.includes("invalid email")) {
    return { field: "email", message: "Enter a valid email address." };
  }
  if (normalized.includes("password") && normalized.includes("weak")) {
    return { field: "password", message: "Choose a stronger password." };
  }
  if (status === 429 || normalized.includes("rate limit")) {
    return { message: "Too many attempts. Please wait a moment and try again." };
  }
  if (status && status >= 500) {
    return { message: "Something went wrong on our end. Please try again." };
  }
  return { message: "Couldn't create your account. Please check your details and try again." };
}
