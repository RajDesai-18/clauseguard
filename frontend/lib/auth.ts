import { betterAuth } from "better-auth";
import { Pool } from "pg";

/**
 * Better Auth server-side configuration.
 *
 * Authoritative source for: providers, session policy, database
 * connection. The Next.js API route at `/api/auth/[...all]/route.ts`
 * delegates everything to this instance, and the client at
 * `lib/auth-client.ts` infers its types from this config via
 * `typeof auth.$Infer.Session`.
 *
 * Database note: Better Auth manages its own four tables (`user`,
 * `session`, `account`, `verification`) which were created by the
 * Alembic baseline migration. Better Auth writes to those tables;
 * FastAPI reads from `session` and `user` to authenticate API
 * requests. Schema in `backend/app/models/auth.py` mirrors what
 * Better Auth expects.
 *
 * Column name note: Better Auth's internal field names are camelCase
 * (emailVerified, createdAt, userId) but our Postgres schema uses
 * snake_case (email_verified, created_at, user_id) per Python/SQL
 * conventions. The `fields` maps below tell Better Auth how to
 * translate between the two. This keeps the backend idiomatic on
 * both sides of the language boundary.
 */
export const auth = betterAuth({
  database: new Pool({
    connectionString: process.env.DATABASE_URL,
  }),

  // Email + password is the primary credential.
  emailAndPassword: {
    enabled: true,
    // Allow sign-in immediately; we don't gate on email verification yet.
    // Phase 7 (or whenever we wire up SMTP) can flip this to true.
    requireEmailVerification: false,
    minPasswordLength: 8,
    maxPasswordLength: 128,
  },

  // Google OAuth as a secondary path. Same account model: a sign-in
  // through Google links a row in the `account` table to the user.
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
  },
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // refresh expiry every 24h of activity
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

  // Trust the local dev origin. For production, this becomes the
  // deployed URL. Phase 6 (deployment) will revisit.
  trustedOrigins: ["http://localhost:3000"],
});

// Export the inferred session type for use in client and server code.
export type Session = typeof auth.$Infer.Session;
