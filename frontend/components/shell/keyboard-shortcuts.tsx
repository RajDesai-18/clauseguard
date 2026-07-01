"use client";

import { useCallback, useEffect, useState } from "react";

import { useKeyboardShortcuts } from "@/components/shell/use-keyboard-shortcuts";

const SHORTCUTS: { keys: string[]; label: string }[] = [
  { keys: ["g", "d"], label: "Go to Dashboard" },
  { keys: ["g", "u"], label: "Go to Upload" },
  { keys: ["g", "s"], label: "Go to Search" },
  { keys: ["g", ","], label: "Go to Settings" },
  { keys: ["["], label: "Collapse / expand sidebar" },
  { keys: ["?"], label: "Show this help" },
];

/**
 * Mounts the global keyboard shortcuts and renders the help overlay.
 * Lives once in the app shell. Renders nothing until `?` is pressed.
 */
export function KeyboardShortcuts() {
  const [helpOpen, setHelpOpen] = useState(false);

  const toggleHelp = useCallback(() => setHelpOpen((v) => !v), []);
  useKeyboardShortcuts(toggleHelp);

  // Esc closes the overlay.
  useEffect(() => {
    if (!helpOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setHelpOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [helpOpen]);

  if (!helpOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={() => setHelpOpen(false)}
    >
      <div className="bg-foreground/20 absolute inset-0" aria-hidden />
      <div
        onClick={(e) => e.stopPropagation()}
        className="border-border bg-background relative w-full max-w-[400px] rounded-sm border p-6 shadow-lg"
      >
        <p className="text-caption text-muted-foreground mb-4 font-mono uppercase">
          Keyboard shortcuts
        </p>
        <ul className="space-y-2.5">
          {SHORTCUTS.map((s) => (
            <li key={s.label} className="flex items-center justify-between gap-4">
              <span className="text-body-sm text-foreground">{s.label}</span>
              <span className="flex items-center gap-1">
                {s.keys.map((k, i) => (
                  <kbd
                    key={i}
                    className="border-border bg-muted text-foreground/80 inline-flex min-w-[22px] items-center justify-center rounded-[3px] border px-1.5 py-0.5 font-mono text-[11px]"
                  >
                    {k}
                  </kbd>
                ))}
              </span>
            </li>
          ))}
        </ul>
        <p className="text-caption text-muted-foreground/70 mt-5 normal-case">
          Press <kbd className="font-mono">Esc</kbd> to close.
        </p>
      </div>
    </div>
  );
}
