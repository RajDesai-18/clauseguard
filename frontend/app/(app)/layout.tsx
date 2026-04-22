import type { Metadata } from "next";
import { AppRail } from "@/components/shell/rail";
import { AppTopBar } from "@/components/shell/top-bar";

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
 * layout — this layout only adds the rail/top-bar/main composition.
 *
 * NOTE: No auth gate yet. Phase 4C adds session protection here.
 */
export default function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
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
