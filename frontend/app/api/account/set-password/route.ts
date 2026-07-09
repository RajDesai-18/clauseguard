import { NextResponse } from "next/server";
import { z } from "zod";
import { APIError } from "better-auth/api";
import { auth } from "@/lib/auth";

/**
 * POST /api/account/set-password
 *
 * Lets an OAuth-only user (e.g. signed in via Google, no credential
 * account) add an email/password credential to their account.
 *
 * Why this exists as a server route: Better Auth's `setPassword` is
 * server-only by design and is not exposed as a client-callable HTTP
 * endpoint, which is why a client-side call to `/api/auth/set-password`
 * returns 404. We wrap `auth.api.setPassword` behind our own route so
 * the browser can reach it while the call itself stays server-side.
 *
 * Security:
 *   - Requires a valid session (401 otherwise).
 *   - Refuses if the user already has a credential account (409). This
 *     prevents a logged-in session from silently overwriting an existing
 *     password without knowing the current one, which would bypass the
 *     `currentPassword` requirement enforced by change-password.
 *
 * Runs on the Node.js runtime because the auth instance uses the `pg`
 * driver, which is not Edge-compatible.
 */
export const runtime = "nodejs";

const BodySchema = z.object({
  newPassword: z
    .string()
    .min(8, "Password must be at least 8 characters.")
    .max(128, "Password must be at most 128 characters."),
});

export async function POST(req: Request): Promise<NextResponse> {
  // Parse and validate the body before touching auth.
  let raw: unknown;
  try {
    raw = await req.json();
  } catch {
    return NextResponse.json(
      { error: { code: "invalid_request", message: "Request body must be valid JSON." } },
      { status: 400 }
    );
  }

  const parsed = BodySchema.safeParse(raw);
  if (!parsed.success) {
    const message = parsed.error.issues[0]?.message ?? "Invalid request.";
    return NextResponse.json({ error: { code: "invalid_request", message } }, { status: 400 });
  }

  try {
    // Identify the caller from their session cookie.
    const session = await auth.api.getSession({ headers: req.headers });
    if (!session) {
      return NextResponse.json(
        { error: { code: "unauthorized", message: "You must be signed in to set a password." } },
        { status: 401 }
      );
    }

    // Guard: only OAuth-only users may set a password here. If a
    // credential account already exists, they should use change-password.
    const accounts = await auth.api.listUserAccounts({ headers: req.headers });
    const hasCredential = accounts.some((account) => account.providerId === "credential");
    if (hasCredential) {
      return NextResponse.json(
        {
          error: {
            code: "password_already_set",
            message: "You already have a password. Use change password instead.",
          },
        },
        { status: 409 }
      );
    }

    // Link a credential account with the chosen password.
    await auth.api.setPassword({
      body: { newPassword: parsed.data.newPassword },
      headers: req.headers,
    });

    return NextResponse.json({ ok: true }, { status: 200 });
  } catch (err) {
    // Better Auth surfaces its own failures as APIError. Forward its
    // status and message rather than masking them as a generic 500.
    if (err instanceof APIError) {
      const status = typeof err.statusCode === "number" ? err.statusCode : 400;
      return NextResponse.json(
        { error: { code: "auth_error", message: err.message || "Auth request failed." } },
        { status }
      );
    }

    console.error("[set-password] unexpected error:", err);
    return NextResponse.json(
      { error: { code: "internal_error", message: "Something went wrong setting your password." } },
      { status: 500 }
    );
  }
}
