"use client";

import { useEffect } from "react";
import Link from "next/link";
import { RotateCw } from "lucide-react";

/**
 * Error boundary for the authenticated app segment.
 *
 * Next App Router renders this in place of the segment's content when a
 * descendant throws during render. It sits inside (app)/layout, so the
 * rail and top bar stay put; only the main content area swaps to this
 * fallback. `reset()` re-renders the segment to retry.
 *
 * This catches the *unexpected* errors that per-page try/catch blocks
 * don't, e.g. a Client Component or hook throwing. Expected, handled
 * failures (a 404 from getContract, a structured API error) are dealt
 * with at the call site and never reach here.
 */
export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surface to the console for local debugging. In production this is
    // where you'd forward to an error reporter (Sentry, etc.).
    console.error("App segment error boundary caught:", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
      <div className="w-full max-w-[560px]">
        <p className="text-caption text-muted-foreground font-mono tracking-[0.14em] uppercase">
          <span>No. 500</span>
          <span className="text-border mx-2">—</span>
          <span>Unexpected Error</span>
        </p>

        <h1 className="font-display text-heading-lg text-foreground mt-6 font-medium tracking-[-0.02em]">
          Something went wrong on this page.
        </h1>
        <p className="text-body text-muted-foreground mt-3 leading-relaxed">
          The page hit an unexpected error. You can retry, or head back to your dashboard. If it
          keeps happening, the reference below helps us track it down.
        </p>

        {error.digest && (
          <p className="text-caption text-muted-foreground/70 mt-4 font-mono">
            Reference: {error.digest}
          </p>
        )}

        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
          <button
            type="button"
            onClick={reset}
            className="bg-foreground text-background hover:bg-foreground/90 font-display ease-out-strong inline-flex w-full items-center justify-center gap-2 rounded-sm px-5 py-2.5 text-[14px] font-medium transition-transform duration-200 hover:scale-[1.01] active:scale-[0.98] sm:w-auto"
          >
            <RotateCw className="size-3.5" strokeWidth={1.5} aria-hidden />
            Try again
          </button>
          <Link
            href="/dashboard"
            className="border-border bg-card hover:bg-foreground/4 hover:border-border/80 text-foreground/90 hover:text-foreground inline-flex w-full items-center justify-center rounded-sm border px-5 py-2.5 font-mono text-[11px] tracking-[0.08em] uppercase transition-colors duration-150 sm:w-auto"
          >
            Back to dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
