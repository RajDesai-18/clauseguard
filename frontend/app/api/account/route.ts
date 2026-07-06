import { NextResponse } from "next/server";
import { APIError } from "better-auth/api";
import { auth } from "@/lib/auth";

/**
 * DELETE /api/account
 *
 * Permanently deletes the current user's account. This orchestrates two
 * systems in a fixed order:
 *
 *   1. Purge application data via FastAPI (contracts, clauses, and the
 *      contracts' MinIO objects), while the session is still valid.
 *   2. Delete the auth user via Better Auth, which cascades the user's
 *      sessions and account rows and clears the session cookie.
 *
 * The order is not interchangeable. FastAPI authenticates by reading the
 * `session` table, so deleting the auth user first would strand the app
 * data (the purge call could no longer authenticate). Purging first means
 * the worst-case partial failure is "data gone, account survives", which is
 * recoverable by retrying, rather than "account gone, files orphaned".
 *
 * Runs on the Node.js runtime because the auth instance uses the `pg`
 * driver, which is not Edge-compatible.
 */
export const runtime = "nodejs";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function DELETE(req: Request): Promise<NextResponse> {
  try {
    // Confirm the caller is authenticated before doing anything destructive.
    const session = await auth.api.getSession({ headers: req.headers });
    if (!session) {
      return NextResponse.json(
        { error: { code: "unauthorized", message: "You must be signed in to delete your account." } },
        { status: 401 }
      );
    }

    // Step 1: purge application data via FastAPI. Forward the incoming
    // cookies so FastAPI resolves the same user from the session table.
    // Node's fetch has no cookie jar, so we pass the header through explicitly.
    const cookie = req.headers.get("cookie") ?? "";
    const purgeRes = await fetch(`${API_URL}/api/v1/account/data`, {
      method: "DELETE",
      headers: { cookie },
      cache: "no-store",
    });

    if (!purgeRes.ok) {
      // Leave the auth user intact so nothing is half-deleted. The user's
      // data is unchanged (the purge aborts atomically on failure), so a
      // retry is safe.
      const body = (await purgeRes.json().catch(() => null)) as
        | { detail?: string; error?: { message?: string } }
        | null;
      const message =
        body?.error?.message ??
        body?.detail ??
        "Couldn't remove your data. Your account was not deleted. Please try again.";
      return NextResponse.json(
        { error: { code: "purge_failed", message } },
        { status: 502 }
      );
    }

    // Step 2: delete the auth user. With no sendDeleteAccountVerification
    // callback configured, this deletes immediately and cascades the user's
    // sessions and account rows, then clears the session cookie.
    await auth.api.deleteUser({ body: {}, headers: req.headers });

    return NextResponse.json({ ok: true }, { status: 200 });
  } catch (err) {
    // Better Auth surfaces its own failures as APIError. Forward its status
    // and message rather than masking them as a generic 500. Note: at this
    // point app data is already purged, so a deleteUser failure leaves the
    // benign "data gone, account survives" state the ordering guarantees.
    if (err instanceof APIError) {
      const status = typeof err.statusCode === "number" ? err.statusCode : 400;
      return NextResponse.json(
        { error: { code: "auth_error", message: err.message || "Account deletion failed." } },
        { status }
      );
    }

    console.error("[delete-account] unexpected error:", err);
    return NextResponse.json(
      { error: { code: "internal_error", message: "Something went wrong deleting your account." } },
      { status: 500 }
    );
  }
}