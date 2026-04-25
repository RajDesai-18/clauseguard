import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

/**
 * Better Auth API catch-all route.
 *
 * Handles every Better Auth endpoint, including:
 *   POST /api/auth/sign-in/email
 *   POST /api/auth/sign-up/email
 *   POST /api/auth/sign-out
 *   GET  /api/auth/sign-in/social/google   (initiates OAuth)
 *   GET  /api/auth/callback/google          (OAuth return)
 *   GET  /api/auth/get-session              (current session lookup)
 *   ... and others.
 *
 * The handler is generated from the auth config — there's nothing to
 * configure here. All policy lives in `lib/auth.ts`.
 */
export const { POST, GET } = toNextJsHandler(auth);
