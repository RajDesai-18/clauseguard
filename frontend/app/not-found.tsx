import Link from "next/link";
import { Logo } from "@/components/ui/logo";
import { BackButton } from "@/components/system/back-button";

/**
 * Global 404 page. Rendered for any URL Next.js can't match to a route,
 * regardless of auth state or route group. Chrome-less by design - when
 * a user is lost, the priority is "here's the way home," not navigation.
 *
 * The editorial gesture: the catalogue number IS the HTTP code. A 404
 * is just a missing folio in the archive.
 */
export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-[640px] text-center">
        <p className="text-caption text-muted-foreground font-mono tracking-[0.14em] uppercase">
          <span>No. 404</span>
          <span className="text-border mx-2">—</span>
          <span>Folio Not Found</span>
        </p>

        <h1
          aria-label="404 - page not found"
          className="font-editorial text-foreground mt-8 leading-[0.9] tracking-[-0.04em]"
          style={{ fontSize: "clamp(120px, 22vw, 240px)" }}
        >
          404
        </h1>

        <p className="font-display text-foreground mt-8 text-[20px] leading-[1.4] tracking-[-0.01em] md:text-[22px]">
          This folio isn&rsquo;t on the shelves.
        </p>
        <p className="text-body text-muted-foreground mt-3">
          It may have been moved to the archives, or it never existed.
        </p>

        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
          <Link
            href="/"
            className="bg-foreground font-display text-body-sm text-background inline-flex w-full items-center justify-center px-6 py-3 font-medium transition-transform duration-200 [transition-timing-function:var(--ease-out-strong)] hover:scale-[1.01] active:scale-[0.98] sm:w-auto"
          >
            Return home
          </Link>
          <BackButton />
        </div>

        <div className="border-border/40 mt-16 flex justify-center border-t pt-8">
          <Logo size="md" />
        </div>
      </div>
    </main>
  );
}
