"use client";

import type { ButtonHTMLAttributes } from "react";

type GoogleButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  label?: string;
};

export function GoogleButton({
  label = "Continue with Google",
  className,
  type = "button",
  ...buttonProps
}: GoogleButtonProps) {
  return (
    <button
      type={type}
      className={[
        "group relative flex w-full items-center justify-center gap-3 px-4 py-3",
        "border-foreground/30 text-body-sm text-foreground border bg-transparent",
        "transition-[border-color,transform] duration-200 [transition-timing-function:var(--ease-out-strong)]",
        "hover:border-foreground/60",
        "active:scale-[0.98]",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "focus-visible:border-foreground outline-none",
        className ?? "",
      ]
        .filter(Boolean)
        .join(" ")}
      {...buttonProps}
    >
      <GoogleGMark />
      <span>{label}</span>
    </button>
  );
}

function GoogleGMark() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 18 18"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      <path
        fill="#4285F4"
        d="M17.64 9.2045c0-.6381-.0573-1.2518-.1636-1.8409H9v3.4818h4.8436c-.2086 1.125-.8427 2.0782-1.7959 2.7164v2.2581h2.9087c1.7018-1.5668 2.6836-3.874 2.6836-6.6154z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.4673-.806 5.9564-2.1805l-2.9087-2.2581c-.806.54-1.8368.86-3.0477.86-2.344 0-4.3282-1.5831-5.0359-3.7104H.9573v2.3318C2.4382 15.9831 5.4818 18 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.9641 10.71c-.18-.54-.2823-1.1168-.2823-1.71s.1023-1.17.2823-1.71V4.9582H.9573C.3477 6.1732 0 7.5477 0 9s.3477 2.8268.9573 4.0418l3.0068-2.3318z"
      />
      <path
        fill="#EA4335"
        d="M9 3.5795c1.3214 0 2.5077.4541 3.4405 1.3459l2.5814-2.5814C13.4632.8918 11.4259 0 9 0 5.4818 0 2.4382 2.0168.9573 4.9582L3.9641 7.29C4.6718 5.1627 6.656 3.5795 9 3.5795z"
      />
    </svg>
  );
}

export function AuthDivider({ label = "or" }: { label?: string }) {
  return (
    <div className="my-6 flex items-center gap-4">
      <span className="bg-border/60 h-px flex-1" aria-hidden />
      <span className="text-caption text-muted-foreground font-mono lowercase">{label}</span>
      <span className="bg-border/60 h-px flex-1" aria-hidden />
    </div>
  );
}
