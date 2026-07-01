"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ComponentProps } from "react";

/**
 * Client wrapper around next-themes. Kept as its own file so the root
 * layout stays a Server Component and only this subtree is client-side.
 *
 * Config rationale:
 * - attribute="class" toggles `.dark` on <html>, which is exactly what
 *   globals.css keys off (@custom-variant dark (&:is(.dark *))).
 * - defaultTheme="light" because the bond-paper light theme is our
 *   primary; dark is the secondary "paper turned over" mode.
 * - enableSystem lets the OS preference win on first visit until the
 *   user makes an explicit choice.
 */
export function ThemeProvider({ children, ...props }: ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
