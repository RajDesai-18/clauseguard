"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { authClient } from "@/lib/auth-client";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface AccountMenuProps {
  name: string;
  email: string;
  image: string | null;
}

export function AccountMenu({ name, email, image }: AccountMenuProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [isSigningOut, startSignOut] = useTransition();

  const initials = getInitials(name || email);

  const handleSignOut = () => {
    startSignOut(async () => {
      await authClient.signOut();
      router.push("/login");
      router.refresh();
    });
  };

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger
        aria-label={`Account menu for ${name || email}`}
        className="bg-muted text-foreground hover:bg-muted/80 focus-visible:ring-foreground focus-visible:ring-offset-background data-[state=open]:bg-muted/80 relative flex size-8 items-center justify-center overflow-hidden rounded-sm transition-colors duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] outline-none focus-visible:ring-2 focus-visible:ring-offset-2"
        style={{
          boxShadow: "inset 0 1px 0 0 rgb(0 0 0 / 0.04), inset 0 -1px 0 0 rgb(255 255 255 / 0.4)",
        }}
      >
        {image ? (
          // Using <img> rather than next/image: avatars are tiny (32px),
          // come from an external host (Google), and the overhead of the
          // next/image loader outweighs the benefit at this size.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={image} alt="" className="size-full object-cover" />
        ) : (
          <span className="text-caption font-mono uppercase">{initials}</span>
        )}
      </DropdownMenuTrigger>

      <DropdownMenuContent
        align="end"
        sideOffset={8}
        className="border-border/60 bg-background w-[240px] rounded-none border p-0 shadow-none ring-0"
      >
        <div className="px-4 pt-4 pb-3">
          <p className="text-caption text-muted-foreground font-mono uppercase">Signed in as</p>
          <p className="font-display text-body-sm text-foreground mt-1 font-medium">{name}</p>
          <p className="text-body-sm text-muted-foreground mt-0.5 truncate">{email}</p>
        </div>

        <DropdownMenuSeparator className="bg-border/60 mx-0 my-0 h-px" />

        <div className="p-1">
          <DropdownMenuItem asChild>
            <Link
              href="/settings"
              className="text-caption text-foreground/85 focus:bg-muted/60 focus:text-foreground cursor-pointer rounded-none px-3 py-2 font-mono tracking-[0.12em] uppercase transition-colors duration-150 ease-[cubic-bezier(0.23,1,0.32,1)]"
            >
              Settings
            </Link>
          </DropdownMenuItem>

          <DropdownMenuItem
            disabled={isSigningOut}
            onSelect={(e) => {
              // Prevent the menu from auto-closing so the user sees the
              // transition state. signOut() finishes + router.push() runs,
              // then the page navigates away naturally.
              e.preventDefault();
              handleSignOut();
            }}
            className="text-caption text-foreground/85 focus:bg-destructive/10 focus:text-destructive cursor-pointer rounded-none px-3 py-2 font-mono tracking-[0.12em] uppercase transition-colors duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] data-[disabled]:pointer-events-none data-[disabled]:opacity-60"
          >
            {isSigningOut ? "Signing out..." : "Sign out"}
          </DropdownMenuItem>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function getInitials(source: string): string {
  const trimmed = source.trim();
  if (!trimmed) return "?";

  // Full name: use first letter of first word + first letter of last word.
  const words = trimmed.split(/\s+/);
  if (words.length >= 2) {
    return (words[0][0] + words[words.length - 1][0]).toUpperCase();
  }

  // Email fallback: take first two letters of the local part.
  const localPart = trimmed.split("@")[0];
  return localPart.slice(0, 2).toUpperCase();
}
