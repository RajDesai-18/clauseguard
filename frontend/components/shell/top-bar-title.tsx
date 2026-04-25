"use client";

import { usePathname } from "next/navigation";

export function TopBarTitle() {
  const pathname = usePathname();
  const title = titleFromPath(pathname);

  return (
    <h1 className="text-heading-md font-display text-foreground font-medium tracking-[-0.01em]">
      {title}
    </h1>
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
