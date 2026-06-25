"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  LayoutDashboard,
  Upload,
  Search,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { LogoMark } from "@/components/ui/logo";

/**
 * Left navigation rail for the authenticated app shell.
 *
 * Tablet+ (md): collapsible. Expanded (224px) shows icon + full label in
 * a left-aligned row; collapsed (72px) shows centered icons only. The
 * collapsed state persists in the `rail_collapsed` cookie, which the
 * server layout reads so first paint matches (no width flicker). The
 * width animates with the house ease curve, the one place a resize
 * genuinely reads better animated than snapped.
 *
 * Mobile: a fixed bottom bar, unaffected by collapse.
 *
 * Active state: a foreground vertical rule bleeds to the rail's right
 * edge, like a magazine bookmark tab. No pulse, no scale, no translate.
 */
export function AppRail({ defaultCollapsed = false }: { defaultCollapsed?: boolean }) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    // Persist as a plain UI preference. Not sensitive, so document.cookie
    // is fine; the server layout reads it for flicker-free first paint.
    // 1 year, lax, site-wide.
    document.cookie = `rail_collapsed=${next ? "1" : "0"}; path=/; max-age=31536000; samesite=lax`;
  };

  return (
    <>
      <aside
        aria-label="Primary"
        data-collapsed={collapsed}
        className={`bg-sidebar border-sidebar-border sticky top-0 z-30 hidden h-screen shrink-0 flex-col border-r transition-[width] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] md:flex ${
          collapsed ? "w-[72px]" : "w-[224px]"
        }`}
      >
        <Link
          href="/dashboard"
          aria-label="ClauseGuard home"
          className={`group border-sidebar-border flex h-14 items-center border-b transition-[padding] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] ${
            collapsed ? "justify-center px-0" : "gap-2.5 px-5"
          }`}
        >
          <LogoMark size="md" />
          {!collapsed && (
            <span className="font-display text-foreground text-[15px] font-medium tracking-[-0.01em] whitespace-nowrap">
              ClauseGuard
            </span>
          )}
        </Link>

        <nav className="flex flex-1 flex-col items-stretch gap-0.5 py-3">
          {NAV_ITEMS.map((item) => (
            <RailLink key={item.href} {...item} collapsed={collapsed} />
          ))}
        </nav>

        <div className="border-sidebar-border border-t p-2">
          <button
            type="button"
            onClick={toggle}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-pressed={collapsed}
            className={`text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-ring flex h-9 w-full items-center rounded-sm transition-colors duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] focus-visible:ring-2 focus-visible:outline-none ${
              collapsed ? "justify-center" : "gap-3 px-3"
            }`}
          >
            {collapsed ? (
              <PanelLeftOpen className="size-4.5 shrink-0" strokeWidth={1.5} aria-hidden />
            ) : (
              <PanelLeftClose className="size-4.5 shrink-0" strokeWidth={1.5} aria-hidden />
            )}
            {!collapsed && (
              <span className="text-caption font-mono whitespace-nowrap uppercase">Collapse</span>
            )}
          </button>
        </div>
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
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/search", label: "Search", icon: Search },
  { href: "/settings", label: "Settings", icon: Settings },
];

function RailLink({ href, label, icon: Icon, collapsed }: NavItem & { collapsed: boolean }) {
  const pathname = usePathname();
  const isActive = pathname === href || pathname.startsWith(`${href}/`);

  return (
    <Link
      href={href}
      aria-current={isActive ? "page" : undefined}
      title={collapsed ? label : undefined}
      className={`group relative flex items-center transition-colors duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] ${
        collapsed ? "h-11 justify-center" : "h-11 gap-3 px-5"
      } ${
        isActive
          ? "text-foreground"
          : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
      }`}
    >
      {isActive && <span aria-hidden className="bg-foreground absolute inset-y-0 right-0 w-0.75" />}
      <Icon className="size-4.5 shrink-0" strokeWidth={isActive ? 1.75 : 1.25} aria-hidden />
      {!collapsed && (
        <span className="text-body-sm font-mono tracking-[0.06em] whitespace-nowrap uppercase">
          {label}
        </span>
      )}
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
      <Icon className="size-4.5" strokeWidth={1.25} aria-hidden />
      <span className="text-caption font-mono uppercase">{label}</span>
    </Link>
  );
}
