import { betterAuth } from "better-auth";
import { Pool } from "pg";

/**
 * Better Auth server-side configuration.
 *
 * Authoritative source for: providers, session policy, database
 * connection, and environment-gated cookie/origin behavior. The Next.js
 * API route at `/api/auth/[...all]/route.ts` delegates everything to this
 * instance, and the client at `lib/auth-client.ts` infers its types from
 * this config via `typeof auth.$Infer.Session`.
 *
 * Deployment topology (production):
 *   - Frontend (this Next.js app, where Better Auth runs): clauseguard.dev
 *   - Backend (FastAPI): api.clauseguard.dev
 *   - Session cookie scoped to the parent `.clauseguard.dev` so both the
 *     apex frontend and the api subdomain read it as a first-party cookie.
 *
 * Because both hosts are subdomains of one parent, cookies stay
 * `SameSite=Lax` (browser-friendly, no third-party-cookie blocking). We do
 * NOT use `SameSite=None`; that path is only needed for genuinely different
 * domains and is unreliable on public-suffix platform URLs.
 *
 * Database note: Better Auth manages its own four tables (`user`,
 * `session`, `account`, `verification`), created by the Alembic baseline.
 * Better Auth writes them; FastAPI reads `session` and `user` to
 * authenticate API requests. Schema mirror lives in
 * `backend/app/models/auth.py`.
 *
 * Column name note: Better Auth's internal field names are camelCase but
 * our Postgres schema is snake_case. The `fields` maps below translate
 * between the two, keeping the backend idiomatic on both sides.
 */

// Production is detected via NODE_ENV, which Vercel sets automatically on
// deployed builds. Nothing to configure at deploy time for this switch.
const isProd = process.env.NODE_ENV === "production";

// The project's public root domain. Not a secret; stable for the life of
// the deployment, so it lives here as a constant rather than an env var.
const ROOT_DOMAIN = "clauseguard.dev";

// The frontend origin where Better Auth runs. Localhost in dev, the apex in
// production. Used as baseURL and is implicitly trusted as an origin.
const FRONTEND_URL = isProd ? `https://${ROOT_DOMAIN}` : "http://localhost:3000";

export const auth = betterAuth({
  database: new Pool({
    connectionString: process.env.DATABASE_URL,
  }),

  // The canonical origin of this auth instance. Better Auth uses it for
  // building callback URLs and implicitly trusts it as an origin.
  baseURL: FRONTEND_URL,

  // Origins allowed to make authenticated requests. In production, both the
  // apex and www (www redirects to apex, but the browser may send it as the
  // origin on the first hit before the redirect resolves). Localhost is
  // deliberately excluded from the production list, per Better Auth security
  // guidance never to trust localhost on a production auth instance.
  trustedOrigins: isProd
    ? [`https://${ROOT_DOMAIN}`, `https://www.${ROOT_DOMAIN}`]
    : ["http://localhost:3000"],

  // Email + password is the primary credential.
  emailAndPassword: {
    enabled: true,
    // Allow sign-in immediately; email verification is not gated yet.
    requireEmailVerification: false,
    minPasswordLength: 8,
    maxPasswordLength: 128,
  },

  // Google OAuth as a secondary path. Same account model: a Google sign-in
  // links a row in the `account` table to the user.
  socialProviders: {
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID as string,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET as string,
    },
  },

  // Map Better Auth's camelCase field names to our snake_case columns.
  user: {
    fields: {
      emailVerified: "email_verified",
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
    // Hard-delete a user and cascade their auth rows (sessions, accounts).
    // No `sendDeleteAccountVerification` callback is configured, so deletion
    // happens immediately in the `auth.api.deleteUser` call rather than via a
    // two-step email flow. That is deliberate: SMTP is not wired yet, and the
    // destructive intent is confirmed in the UI (typed "DELETE") instead. The
    // Next.js orchestrator route purges app data (contracts, clauses, MinIO
    // objects) via FastAPI *before* calling deleteUser, while the session is
    // still valid.
    deleteUser: {
      enabled: true,
    },
  },
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // refresh expiry every 24h of activity
    // Disable the fresh-session gate on sensitive operations. Better Auth
    // otherwise requires a session created within `freshAge` (default 1 day)
    // for deleteUser / unlinkAccount, which would intermittently reject an
    // OAuth user whose last sign-in was more than a day ago. We rely on
    // per-operation guards instead: current-password for change-password, the
    // lock-out guard for disconnect, and a typed confirmation for delete.
    freshAge: 0,
    fields: {
      userId: "user_id",
      expiresAt: "expires_at",
      ipAddress: "ip_address",
      userAgent: "user_agent",
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
  },
  account: {
    fields: {
      userId: "user_id",
      accountId: "account_id",
      providerId: "provider_id",
      accessToken: "access_token",
      refreshToken: "refresh_token",
      accessTokenExpiresAt: "access_token_expires_at",
      refreshTokenExpiresAt: "refresh_token_expires_at",
      idToken: "id_token",
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
  },
  verification: {
    fields: {
      expiresAt: "expires_at",
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
  },

  advanced: {
    // Force the Secure cookie flag in production. `.dev` is HTTPS-only
    // anyway, but making it explicit is correct and self-documenting.
    useSecureCookies: isProd,

    // Share the session cookie across the apex and api subdomain by scoping
    // it to the parent domain. In dev this is disabled entirely: localhost
    // does not need it and cross-subdomain cookies misbehave there.
    crossSubDomainCookies: isProd
      ? { enabled: true, domain: `.${ROOT_DOMAIN}` }
      : { enabled: false },
  },
});

// Export the inferred session type for use in client and server code.
export type Session = typeof auth.$Infer.Session;
