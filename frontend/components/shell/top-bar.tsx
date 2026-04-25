import { headers } from "next/headers";
import { auth } from "@/lib/auth";
import { AccountMenu } from "@/components/shell/account-menu";
import { TopBarTitle } from "@/components/shell/top-bar-title";

/**
 * Top bar for the authenticated app shell.
 *
 * 56px height (denser than marketing's 72px), sticky, NO scroll-frost.
 * The marketing nav frosts on scroll because there's a hero behind it
 * worth seeing through; here, the surface behind the bar is just the
 * tool's own content, and frosting would be theatrical.
 *
 * Server Component: reads the session server-side so the avatar paints
 * immediately with real data (no skeleton flash). The dropdown and title
 * components are client islands.
 *
 * Per MASTER.md v1.2/v1.3: no Gambetta italic, no editorial decoration.
 * The bar is a thin reference strip. Restraint is the design.
 */
export async function AppTopBar() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  // If we render the top bar, the route group layout has already asserted
  // there's a session. But in case this ever renders without one (e.g. a
  // future public-but-in-app-chrome page), we render a safe fallback
  // instead of crashing.
  const user = session?.user;

  return (
    <header className="bg-background border-border/40 sticky top-0 z-20 h-14 border-b">
      <div className="flex h-full items-center justify-between px-6 md:px-10">
        <TopBarTitle />
        <div className="flex items-center gap-3">
          {user ? (
            <AccountMenu name={user.name ?? ""} email={user.email} image={user.image ?? null} />
          ) : null}
        </div>
      </div>
    </header>
  );
}
