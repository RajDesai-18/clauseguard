"use client";

import { useEffect } from "react";

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/**
 * Last-resort error boundary. Fires when an error breaks the root
 * layout itself (or anywhere `app/error.tsx` can't reach). Bypasses
 * the root layout entirely - we have to recreate <html>, <body>, and
 * the bond paper background ourselves.
 *
 * Because the font setup and design tokens live in the root layout
 * and globals.css (which is still loaded), we can rely on font-display
 * and the CSS variables surviving even when the layout itself fails.
 *
 * Copy is deliberately barer than the route-level error.tsx - if we
 * got here, the app is in a worse state and we shouldn't promise much.
 */
export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    console.error("Global error (root layout failed):", error);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          background: "var(--background, #f5f3ee)",
          color: "var(--foreground, #1a1a1a)",
          fontFamily: "system-ui, sans-serif",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "2rem",
          textAlign: "center",
        }}
      >
        <div style={{ maxWidth: "560px" }}>
          <p
            style={{
              fontFamily: "monospace",
              fontSize: "12px",
              textTransform: "uppercase",
              letterSpacing: "0.14em",
              opacity: 0.6,
              margin: 0,
            }}
          >
            No. 500 &mdash; Critical Filing Error
          </p>

          <h1
            style={{
              fontStyle: "italic",
              fontSize: "clamp(56px, 12vw, 120px)",
              lineHeight: 0.9,
              letterSpacing: "-0.04em",
              fontWeight: 400,
              margin: "2rem 0 0 0",
            }}
          >
            The system is down.
          </h1>

          <p
            style={{
              marginTop: "1.5rem",
              fontSize: "16px",
              lineHeight: 1.5,
              opacity: 0.7,
            }}
          >
            Something broke at the foundation. Please try again, or come back in a few minutes.
          </p>

          {error.digest && (
            <p
              style={{
                marginTop: "0.75rem",
                fontFamily: "monospace",
                fontSize: "11px",
                textTransform: "uppercase",
                letterSpacing: "0.12em",
                opacity: 0.4,
              }}
            >
              Reference: {error.digest}
            </p>
          )}

          <div style={{ marginTop: "2.5rem" }}>
            <button
              type="button"
              onClick={() => reset()}
              style={{
                background: "var(--foreground, #1a1a1a)",
                color: "var(--background, #f5f3ee)",
                border: "none",
                padding: "0.75rem 1.5rem",
                fontFamily: "inherit",
                fontSize: "14px",
                fontWeight: 500,
                cursor: "pointer",
                letterSpacing: "0.01em",
              }}
            >
              Try again
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
