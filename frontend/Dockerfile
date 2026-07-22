# Production image for the ClauseGuard Next.js frontend.
#
# Multi-stage build:
#   1. deps   - install node_modules from the lockfile
#   2. builder - build the Next.js app (standalone output)
#   3. runner - minimal runtime image with only the standalone bundle
#
# IMPORTANT: NEXT_PUBLIC_* variables are inlined into the client bundle at
# BUILD time, not runtime. They are therefore passed as build args here and
# must be supplied when building (docker-compose.prod.yml does this). Server-
# only secrets (DATABASE_URL, GOOGLE_CLIENT_SECRET, ...) are read at RUNTIME
# from the container environment and must NOT be build args.

# ---- deps ----
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---- builder ----
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Public (build-time) configuration. These end up in the client bundle.
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_BETTER_AUTH_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_BETTER_AUTH_URL=${NEXT_PUBLIC_BETTER_AUTH_URL}

# Standalone output requires it to be enabled in next.config (see repo change).
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---- runner ----
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Run as a non-root user inside the container.
RUN addgroup --system --gid 1001 nodejs \
 && adduser --system --uid 1001 nextjs

# Copy the standalone server, static assets, and public files.
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# The standalone build emits server.js at the app root.
CMD ["node", "server.js"]