import { createAuthClient } from "better-auth/react";
import { inferAdditionalFields } from "better-auth/client/plugins";
import type { auth } from "@/lib/auth";

/**
 * Better Auth client for the browser.
 *
 * Provides `signIn`, `signUp`, `signOut`, `useSession`, and friends.
 * Type inference is wired through to the server config via the
 * `inferAdditionalFields` plugin so every method gets full autocomplete
 * and type safety based on the providers and fields we enabled in
 * `lib/auth.ts`.
 *
 * Usage:
 *   import { authClient } from "@/lib/auth-client";
 *   const { data: session } = authClient.useSession();
 *   await authClient.signIn.email({ email, password });
 *   await authClient.signIn.social({ provider: "google" });
 *   await authClient.signOut();
 *
 * The baseURL is resolved from NEXT_PUBLIC_BETTER_AUTH_URL at build
 * time. In dev it falls back to the current origin, which works
 * because the auth routes live on the same Next.js app.
 */
export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_BETTER_AUTH_URL,
  plugins: [inferAdditionalFields<typeof auth>()],
});

// Convenience re-exports for the most common hooks/methods.
// Lets components do `import { useSession } from "@/lib/auth-client"`
// instead of destructuring every time.
export const { signIn, signUp, signOut, useSession } = authClient;
