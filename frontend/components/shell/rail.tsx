"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Upload, FileText, Settings } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { LogoMark } from "@/components/ui/logo";

/**
 * Left navigation rail for the authenticated app shell.
 *
 * Tablet+ (md): 72px wide, sticky, full viewport height, vertical icon
 * stack. Mobile: collapses to a fixed bottom bar with horizontal layout.
 *
 * Active state borrows from the marketing site's section-numbering voice
 * sparingly: a foreground vertical rule bleeds outside the rail's padding
 * box, like a magazine bookmark tab. No pulse, no scale, no translate.
 *
 * The rail surface is bg-sidebar (palette-matched but slightly distinct
 * from bg-background) so the bond paper texture passes through but the
 * boundary between chrome and content is legible.
 *
 * Per MASTER.md v1.2: no risk colors anywhere here, no Gambetta italic,
 * no labels next to icons (rail is too narrow), no collapse animation.
 */
export function AppRail() {
  return (
    <>
      <aside
        aria-label="Primary"
        className="bg-sidebar border-sidebar-border sticky top-0 z-30 hidden h-screen w-[72px] shrink-0 flex-col border-r md:flex"
      >
        <Link
          href="/dashboard"
          aria-label="ClauseGuard home"
          className="group border-sidebar-border flex h-14 items-center justify-center border-b"
        >
          <LogoMark size="md" />
        </Link>

        <nav className="flex flex-1 flex-col items-stretch gap-0.5 py-3">
          {NAV_ITEMS.map((item) => (
            <RailLink key={item.href} {...item} />
          ))}
        </nav>
      </aside>

      <nav
        aria-label="Primary"
        className="bg-sidebar border-sidebar-border fixed inset-x-0 bottom-0 z-30 flex h-16 items-stretch justify-around border-t md:hidden"
      >
        {NAV_ITEMS.map((item, index) => (
          <BottomBarLink key={item.href} {...item} index={index + 1} />
        ))}
      </nav>
    </>
  );
}

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dash", icon: LayoutDashboard },
  { href: "/upload", label: "Up", icon: Upload },
  { href: "/contracts", label: "Files", icon: FileText },
  { href: "/settings", label: "Set", icon: Settings },
];

function RailLink({ href, label, icon: Icon }: NavItem) {
  const pathname = usePathname();
  const isActive = pathname === href || pathname.startsWith(`${href}/`);

  return (
    <Link
      href={href}
      aria-current={isActive ? "page" : undefined}
      className={`group relative flex flex-col items-center justify-center gap-1.5 py-3.5 transition-colors duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] ${
        isActive
          ? "text-foreground"
          : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
      }`}
    >
      {isActive && <span aria-hidden className="bg-foreground absolute inset-y-0 right-0 w-0.75" />}
      <Icon className="size-4.5" strokeWidth={isActive ? 1.75 : 1.25} />
      <span className="text-caption font-mono uppercase">{label}</span>
    </Link>
  );
}

function BottomBarLink({ href, label, icon: Icon, index }: NavItem & { index: number }) {
  const pathname = usePathname();
  const isActive = pathname === href || pathname.startsWith(`${href}/`);
  const indexStr = String(index).padStart(3, "0");

  return (
    <Link
      href={href}
      aria-current={isActive ? "page" : undefined}
      className={`group relative flex flex-1 flex-col items-center justify-center gap-1 transition-colors duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] ${
        isActive ? "text-foreground" : "text-muted-foreground"
      }`}
    >
      {isActive && <span aria-hidden className="bg-foreground absolute inset-x-6 top-0 h-px" />}
      <span className="text-muted-foreground/70 font-mono text-[9px] tracking-[0.18em] uppercase">
        {indexStr}
      </span>
      <Icon className="size-4.5" strokeWidth={1.25} />
      <span className="text-caption font-mono uppercase">{label}</span>
    </Link>
  );
}
