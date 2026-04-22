"use client";

import { usePathname } from "next/navigation";

/**
 * Top bar for the authenticated app shell.
 *
 * 56px height (denser than marketing's 72px), sticky, NO scroll-frost.
 * The marketing nav frosts on scroll because there's a hero behind it
 * worth seeing through; here, the surface behind the bar is just the
 * tool's own content, and frosting would be theatrical.
 *
 * Layout: page title left, account avatar right. Title is derived from
 * pathname — keeping it stateless avoids prop drilling from every page.
 *
 * Per MASTER.md v1.2: no Gambetta italic, no editorial decoration. The
 * bar is a thin reference strip. Restraint is the design.
 */
export function AppTopBar() {
  const pathname = usePathname();
  const title = titleFromPath(pathname);

  return (
    <header className="bg-background border-border/40 sticky top-0 z-20 h-14 border-b">
      <div className="flex h-full items-center justify-between px-6 md:px-10">
        <h1 className="text-heading-md font-display text-foreground font-medium tracking-[-0.01em]">
          {title}
        </h1>
        <div className="flex items-center gap-3">
          <AvatarPlaceholder />
        </div>
      </div>
    </header>
  );
}

/**
 * Phase 4B placeholder. Foreground initials on bg-muted, with a subtle
 * 1px inset that gives the avatar a slight pressed-in quality on bond
 * paper without resorting to a drop shadow. Replaced with real avatar
 * + dropdown when auth lands in Phase 4C.
 */
function AvatarPlaceholder() {
  return (
    <div
      aria-label="Account (placeholder, auth coming in Phase 4C)"
      className="bg-muted text-foreground text-caption relative flex size-8 items-center justify-center rounded-sm font-mono"
      style={{
        boxShadow: "inset 0 1px 0 0 rgb(0 0 0 / 0.04), inset 0 -1px 0 0 rgb(255 255 255 / 0.4)",
      }}
    >
      RD
    </div>
  );
}

function titleFromPath(pathname: string): string {
  if (pathname === "/dashboard") return "Dashboard";
  if (pathname === "/upload") return "Upload";
  if (pathname.startsWith("/contract/")) return "Contract";
  if (pathname === "/contracts") return "Contracts";
  if (pathname === "/settings") return "Settings";
  return "ClauseGuard";
}
