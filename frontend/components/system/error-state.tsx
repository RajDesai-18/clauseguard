import type { ReactNode } from "react";

/**
 * Inline error surface for handled, in-content failures, e.g. an API
 * call that failed at a page or section level. Distinct from the
 * route-level error.tsx boundary (which catches *unexpected* throws and
 * takes over the whole content area); this is a composed block the page
 * renders deliberately when it knows something failed.
 *
 * Surfaces the backend's structured error message and, when present, the
 * request_id as a support reference, so users can quote it instead of
 * screenshotting a stack trace.
 */
export function ErrorState({
  title = "Something went wrong",
  message,
  requestId,
  action,
}: {
  title?: string;
  message: string;
  requestId?: string;
  action?: ReactNode;
}) {
  return (
    <div
      role="alert"
      className="border-destructive/40 bg-destructive/5 rounded-sm border px-6 py-6"
    >
      <p className="text-caption text-destructive mb-2 font-mono uppercase">{title}</p>
      <p className="text-body-sm text-foreground leading-relaxed">{message}</p>

      {requestId && (
        <p className="text-caption text-muted-foreground/70 mt-3 font-mono">
          Reference: {requestId}
        </p>
      )}

      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
