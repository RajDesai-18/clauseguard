"use client";

import { forwardRef, useId, useState } from "react";
import type { InputHTMLAttributes } from "react";

interface AuthInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "type"> {
  label: string;
  error?: string;
  helperText?: string;
  type?: InputHTMLAttributes<HTMLInputElement>["type"];
  /** Renders a Show/Hide text toggle at the right edge. Only meaningful for type="password". */
  withPasswordToggle?: boolean;
}

export const AuthInput = forwardRef<HTMLInputElement, AuthInputProps>(function AuthInput(
  { label, error, helperText, className, type = "text", withPasswordToggle = false, ...inputProps },
  ref
) {
  const reactId = useId();
  const inputId = `auth-input-${reactId}`;
  const helperId = error || helperText ? `${inputId}-helper` : undefined;

  const [revealed, setRevealed] = useState(false);
  const isPasswordToggle = withPasswordToggle && type === "password";
  const effectiveType = isPasswordToggle && revealed ? "text" : type;

  const hasError = Boolean(error);

  return (
    <div className="w-full">
      <div className="flex items-baseline justify-between">
        <label
          htmlFor={inputId}
          className="text-foreground/85 block font-mono text-[12px] font-medium tracking-[0.12em] uppercase"
        >
          {label}
        </label>
        {isPasswordToggle && (
          <button
            type="button"
            onClick={() => setRevealed((r) => !r)}
            className="text-muted-foreground hover:text-foreground font-mono text-[11px] tracking-[0.14em] uppercase transition-colors duration-150 [transition-timing-function:var(--ease-out-strong)]"
            aria-pressed={revealed}
            aria-controls={inputId}
          >
            {revealed ? "Hide" : "Show"}
          </button>
        )}
      </div>
      <input
        ref={ref}
        id={inputId}
        type={effectiveType}
        aria-invalid={hasError || undefined}
        aria-describedby={helperId}
        className={[
          "text-body text-foreground mt-2 w-full bg-transparent py-2.5",
          "border-border/60 border-b",
          "placeholder:text-muted-foreground/60 outline-none",
          "transition-[border-color,border-bottom-width,padding-bottom] duration-150 [transition-timing-function:var(--ease-out-strong)]",
          "focus:border-foreground focus:border-b-2 focus:pb-[9px]",
          hasError ? "border-destructive focus:border-destructive" : "",
          className ?? "",
        ]
          .filter(Boolean)
          .join(" ")}
        {...inputProps}
      />
      {(error || helperText) && (
        <p
          id={helperId}
          className={[
            "text-caption mt-2 font-mono",
            hasError ? "text-destructive" : "text-muted-foreground",
          ].join(" ")}
        >
          {error ?? helperText}
        </p>
      )}
    </div>
  );
});
