"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

/**
 * Marketing site top navigation (a.k.a. "the top rail").
 *
 * At rest: solid bg-background, matches the footer cleanly.
 * On scroll: translucent bg + backdrop-blur so content reads through
 * as you move past it. The blur is earned — there's something behind
 * the nav worth seeing through.
 *
 * - Mobile: hamburger reveals full-screen drawer
 * - Tablet+: inline nav
 * - Scroll: background frosts + bottom border strengthens
 */
export function SiteNav() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (menuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  return (
    <>
      <header
        className={`sticky top-0 z-40 border-b transition-[background-color,backdrop-filter,border-color] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] ${
          scrolled ? "border-foreground/30 bg-background/30 backdrop-blur-md" : "border-border/40"
        }`}
      >
        <div className="mx-auto flex w-full max-w-[1400px] items-center justify-between px-6 py-4 pl-14 md:px-10 md:pl-24 xl:pl-28">
          <Link href="/" className="group flex items-center gap-2.5" aria-label="ClauseGuard home">
            <span
              aria-hidden
              className="border-foreground group-hover:bg-foreground inline-flex size-[18px] items-center justify-center border transition-colors duration-200 ease-[cubic-bezier(0.23,1,0.32,1)]"
            >
              <span className="bg-foreground group-hover:bg-background size-[5px] transition-colors duration-200 ease-[cubic-bezier(0.23,1,0.32,1)]" />
            </span>
            <span className="font-display text-[15px] font-medium tracking-tight">ClauseGuard</span>
          </Link>

          <nav className="hidden items-center gap-7 md:flex">
            <NavLink href="#product">Product</NavLink>
            <NavLink href="#process">How it works</NavLink>
            <NavLink href="/docs">Docs</NavLink>
            <Link
              href="/login"
              className="border-foreground/50 text-caption text-foreground hover:border-foreground hover:bg-foreground hover:text-background rounded-[3px] border px-3.5 py-1.5 font-mono font-medium uppercase transition-all duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] active:scale-[0.98]"
            >
              Sign in
            </Link>
          </nav>

          <button
            type="button"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((o) => !o)}
            className="flex size-9 items-center justify-center md:hidden"
          >
            <span className="relative block h-4 w-5">
              <span
                className={`bg-foreground absolute right-0 left-0 block h-px transition-all duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] ${
                  menuOpen ? "top-1/2 rotate-45" : "top-0"
                }`}
              />
              <span
                className={`bg-foreground absolute right-0 left-0 block h-px transition-all duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] ${
                  menuOpen ? "top-1/2 -rotate-45" : "top-[calc(50%-0.5px)]"
                }`}
              />
              <span
                className={`bg-foreground absolute right-0 left-0 block h-px transition-all duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] ${
                  menuOpen ? "top-1/2 opacity-0" : "bottom-0"
                }`}
              />
            </span>
          </button>
        </div>
      </header>

      <div
        className={`bg-background fixed inset-0 z-30 flex flex-col pt-[73px] transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)] md:hidden ${
          menuOpen
            ? "pointer-events-auto translate-y-0 opacity-100"
            : "pointer-events-none -translate-y-4 opacity-0"
        }`}
        aria-hidden={!menuOpen}
      >
        <nav className="flex flex-col gap-1 px-6 py-10 pl-14">
          <MobileLink onClick={() => setMenuOpen(false)} href="#product" index="001">
            Product
          </MobileLink>
          <MobileLink onClick={() => setMenuOpen(false)} href="#process" index="002">
            How it works
          </MobileLink>
          <MobileLink onClick={() => setMenuOpen(false)} href="/docs" index="003">
            Docs
          </MobileLink>
          <MobileLink onClick={() => setMenuOpen(false)} href="/login" index="004" emphasis>
            Sign in
          </MobileLink>
        </nav>
      </div>
    </>
  );
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="group text-caption text-muted-foreground hover:text-foreground relative font-mono uppercase transition-colors duration-200 ease-[cubic-bezier(0.23,1,0.32,1)]"
    >
      <span>{children}</span>
      <span
        aria-hidden
        className="bg-foreground absolute inset-x-0 -bottom-1.5 h-px origin-left scale-x-0 transition-transform duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] group-hover:scale-x-100"
      />
    </Link>
  );
}

function MobileLink({
  href,
  children,
  index,
  emphasis = false,
  onClick,
}: {
  href: string;
  children: React.ReactNode;
  index: string;
  emphasis?: boolean;
  onClick?: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className={`group border-border/50 flex items-baseline gap-5 border-b py-5 transition-colors duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] ${emphasis ? "" : "hover:bg-muted/30"}`}
    >
      <span className="text-caption text-muted-foreground font-mono uppercase">No. {index}</span>
      <span
        className={`font-display tracking-[-0.02em] ${emphasis ? "text-[28px]" : "text-[32px]"} font-medium`}
      >
        {children}
      </span>
      <span
        aria-hidden
        className="text-muted-foreground ml-auto font-mono text-lg transition-transform duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] group-hover:translate-x-1"
      >
        &rarr;
      </span>
    </Link>
  );
}
