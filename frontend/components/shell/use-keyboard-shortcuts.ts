"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useRail } from "@/components/shell/rail-context";

// g-prefix sequences: press `g`, then the second key within this window.
const SEQUENCE_TIMEOUT_MS = 1000;

const NAV_SEQUENCES: Record<string, string> = {
  d: "/dashboard",
  u: "/upload",
  s: "/search",
  ",": "/settings",
};

/**
 * Determine whether a keydown should be ignored because the user is
 * typing or holding a modifier. Keeps single-key shortcuts from firing
 * inside inputs (so `g`/`s`/`[` behave as literal keystrokes there) and
 * leaves browser/OS chords (Ctrl+S, Cmd+K) untouched.
 */
function shouldIgnore(e: KeyboardEvent): boolean {
  if (e.ctrlKey || e.metaKey || e.altKey) return true;
  const el = e.target as HTMLElement | null;
  if (!el) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable === true;
}

/**
 * Global keyboard shortcuts for the authenticated app.
 *
 * - g d / g u / g s / g , : navigate to the four primary sections
 * - [ : toggle the rail (collapse/expand), shared via RailContext
 * - ? : open the shortcuts overlay (handled by the caller via onToggleHelp)
 *
 * Sequences use a short timeout: pressing `g` arms navigation, and the
 * next key within one second completes it. All handlers no-op while the
 * user is typing or holding a modifier (see shouldIgnore).
 */
export function useKeyboardShortcuts(onToggleHelp: () => void) {
  const router = useRouter();
  const { toggle } = useRail();
  // Timestamp of the last `g` press; 0 means "not armed".
  const gArmedAt = useRef(0);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (shouldIgnore(e)) {
        gArmedAt.current = 0;
        return;
      }

      const now = Date.now();
      const gArmed = gArmedAt.current > 0 && now - gArmedAt.current < SEQUENCE_TIMEOUT_MS;

      // Second key of a g-sequence.
      if (gArmed && e.key in NAV_SEQUENCES) {
        e.preventDefault();
        gArmedAt.current = 0;
        router.push(NAV_SEQUENCES[e.key]);
        return;
      }

      // Arm the g-sequence.
      if (e.key === "g") {
        gArmedAt.current = now;
        return;
      }

      // Any other key cancels a pending sequence.
      gArmedAt.current = 0;

      // Single-key shortcuts.
      if (e.key === "[") {
        e.preventDefault();
        toggle();
        return;
      }
      if (e.key === "?") {
        e.preventDefault();
        onToggleHelp();
        return;
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [router, toggle, onToggleHelp]);
}
