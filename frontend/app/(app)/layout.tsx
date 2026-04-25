import type { Metadata } from "next";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { AppRail } from "@/components/shell/rail";
import { AppTopBar } from "@/components/shell/top-bar";
import { auth } from "@/lib/auth";

export const metadata: Metadata = {
  title: {
    default: "ClauseGuard",
    template: "%s · ClauseGuard",
  },
};

/**
 * Layout for authenticated app routes.
 *
 * Composes the persistent shell: left rail (or bottom bar on mobile)
 * and the top bar. Content area uses tighter padding than marketing
 * pages since there's no editorial scroll rhythm to preserve.
 *
 * The bond paper texture and html/body wrapper come from the root
 * layout - this layout only adds the rail/top-bar/main composition.
 *
 * Auth gate: the layout is async and reads the session server-side.
 * If there is no session, we redirect to /login with a callbackUrl so
 * the user lands back here after signing in. Children below are only
 * rendered when a session exists, so every route under (app) is
 * implicitly protected without per-page checks.
 *
 * Note: top-bar reads the session independently for the avatar dropdown.
 * Better Auth caches the lookup within a request, so the second read is
 * effectively free; not worth coupling layout and top-bar via props.
 */
export default async function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) {
    // We can't read the current pathname server-side here (layouts don't
    // receive it as a prop). The login page lands users on /dashboard by
    // default when no callbackUrl is provided, which is the right
    // fallback for the common case of "I tried to look at the app while
    // logged out."
    redirect("/login?callbackUrl=/dashboard");
  }

  return (
    <div className="flex min-h-screen">
      <AppRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppTopBar />
        <main className="flex-1 px-6 pt-8 pb-20 md:px-10 md:pt-10 md:pb-16">
          <div className="mx-auto w-full max-w-[1280px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
