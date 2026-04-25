"use client";

import { useState, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { z } from "zod";
import { authClient } from "@/lib/auth-client";
import { AuthInput } from "@/components/auth/auth-input";
import { AuthDivider, GoogleButton } from "@/components/auth/google-button";

const loginSchema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type FieldErrors = Partial<Record<"email" | "password", string>>;

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") ?? "/dashboard";

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

    const parsed = loginSchema.safeParse({ email, password });
    if (!parsed.success) {
      const errors: FieldErrors = {};
      for (const issue of parsed.error.issues) {
        const path = issue.path[0];
        if (path === "email" || path === "password") {
          errors[path] = issue.message;
        }
      }
      setFieldErrors(errors);
      return;
    }

    startTransition(async () => {
      const result = await authClient.signIn.email({
        email: parsed.data.email,
        password: parsed.data.password,
      });

      if (result.error) {
        setFormError(mapAuthError(result.error.message ?? "", result.error.status));
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
      setFormError(mapAuthError(result.error.message ?? "", result.error.status));
      setGoogleLoading(false);
    }
  };

  const submitting = isPending || googleLoading;

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="space-y-5">
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
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={fieldErrors.password}
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
        {isPending ? "Signing in..." : "Sign in"}
      </button>

      <AuthDivider />

      <GoogleButton onClick={handleGoogle} disabled={submitting} />
    </form>
  );
}

/**
 * Maps Better Auth error messages into copy that fits the auth chrome voice.
 * Better Auth surfaces a small set of canonical strings; anything we don't
 * recognize falls through to a generic "couldn't sign in" line.
 */
function mapAuthError(message: string, status?: number): string {
  const normalized = message.toLowerCase();

  if (
    normalized.includes("invalid email or password") ||
    normalized.includes("invalid credentials")
  ) {
    return "Email or password is incorrect.";
  }
  if (normalized.includes("user not found")) {
    return "No account exists with that email.";
  }
  if (normalized.includes("email not verified")) {
    return "Please verify your email before signing in.";
  }
  if (status === 429 || normalized.includes("rate limit")) {
    return "Too many attempts. Please wait a moment and try again.";
  }
  if (status && status >= 500) {
    return "Something went wrong on our end. Please try again.";
  }
  return "Couldn't sign in. Please check your details and try again.";
}
