"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Logo } from "@/components/ui/logo";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/**
 * Route-level error boundary. Renders inside the root layout, so the
 * bond paper background and font wiring are preserved.
 *
 * `reset` re-attempts rendering the segment that threw. We expose this
 * as the primary CTA - "Try again" beats "Reload" because it doesn't
 * blow away the user's session, scroll state, or any client-side cache
 * unrelated to the error.
 */
export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    // In production this is where we'd ship to Sentry, Datadog, etc.
    // For now, console is fine - server-side errors are already in the
    // Next.js dev overlay or the production server logs.
    console.error("Route error:", error);
  }, [error]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-[640px] text-center">
        <p className="text-caption text-muted-foreground font-mono tracking-[0.14em] uppercase">
          <span>No. 500</span>
          <span className="text-border mx-2">—</span>
          <span>Filing Error</span>
        </p>

        <h1
          aria-label="Something went wrong"
          className="font-editorial text-foreground mt-8 leading-[0.9] tracking-[-0.04em] italic"
          style={{ fontSize: "clamp(72px, 14vw, 156px)" }}
        >
          Something <br className="hidden sm:block" />
          went sideways.
        </h1>

        <p className="text-body text-muted-foreground mx-auto mt-8 max-w-[52ch]">
          We hit a problem on our end. The team has been notified and the page should recover if you
          try again. If it keeps happening, head home and we&rsquo;ll look into it.
        </p>

        {error.digest && (
          <p className="text-caption text-muted-foreground/60 mt-4 font-mono tracking-[0.12em] uppercase">
            Reference: {error.digest}
          </p>
        )}

        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
          <button
            type="button"
            onClick={() => reset()}
            className="bg-foreground font-display text-body-sm text-background inline-flex w-full items-center justify-center px-6 py-3 font-medium transition-transform duration-200 [transition-timing-function:var(--ease-out-strong)] hover:scale-[1.01] active:scale-[0.98] sm:w-auto"
          >
            Try again
          </button>
          <Link
            href="/"
            className="text-caption text-muted-foreground decoration-muted-foreground/40 hover:text-foreground hover:decoration-foreground/80 font-mono tracking-[0.12em] uppercase underline underline-offset-4 transition-colors duration-150 [transition-timing-function:var(--ease-out-strong)]"
          >
            Return home
          </Link>
        </div>

        <div className="border-border/40 mt-16 flex justify-center border-t pt-8">
          <Logo size="md" />
        </div>
      </div>
    </main>
  );
}
