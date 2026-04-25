import type { Metadata } from "next";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";

export const metadata: Metadata = {
  title: {
    default: "ClauseGuard",
    template: "%s · ClauseGuard",
  },
};

/**
 * Layout for the unauthenticated auth route group (/login, /signup).
 *
 * Inverse of the (app) gate: if a session exists, the user has no
 * business on the auth pages and gets bounced to /dashboard.
 *
 * No chrome - the AuthCard component owns the centered-card layout.
 * This layout only does the session check and renders children.
 */
export default async function AuthLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (session) {
    redirect("/dashboard");
  }

  return <>{children}</>;
}
