# ClauseGuard

[![Live](https://img.shields.io/badge/live-clauseguard.dev-2ea043)](https://clauseguard.dev)
[![CI](https://github.com/RajDesai-18/clauseguard/actions/workflows/ci.yml/badge.svg)](https://github.com/RajDesai-18/clauseguard/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

AI-powered contract review for people who aren't lawyers. Upload a contract (NDA, MSA, SOW, freelance agreement) and ClauseGuard returns a clause-by-clause risk analysis, plain-English explanations, market-standard comparisons, and AI-suggested redlines. Think "Grammarly for contracts."

**Live at [clauseguard.dev](https://clauseguard.dev)** &nbsp;·&nbsp; sign up (email or Google), upload an NDA, and watch the pipeline run in real time. API at [api.clauseguard.dev](https://api.clauseguard.dev).

This is a solo-built portfolio project demonstrating a production distributed system: a Celery saga pipeline, circuit-breaking LLM calls, fan-out parallelism, semantic caching with pgvector, and live progress streaming over SSE. It is deployed and running, not a localhost demo.

## Engineering highlights

- **Saga pipeline** &mdash; a five-stage Celery task chain (parse, classify, score, redline, finalize) where each step persists its own results, so a worker can crash and restart mid-pipeline without losing progress. Saga state lives in Postgres, not in task arguments, to keep broker messages small.
- **Fan-out parallelism** &mdash; per-clause classification is dispatched as a Celery `group()`, so an N-clause contract becomes N parallel LLM calls instead of a serial loop.
- **Circuit-breaking LLM layer** &mdash; all model calls go through LiteLLM wrapped in a `pybreaker` circuit breaker, with automatic fallback from GPT-5.1 to Gemini 2.5 Flash when the primary provider degrades.
- **Three-layer cost control** &mdash; before any LLM call, a clause is checked against a Redis exact-hash cache, then a pgvector semantic-similarity search (0.92 threshold), and only then falls through to the model.
- **Live progress over SSE** &mdash; Celery tasks publish to Redis Pub/Sub; the browser holds an `EventSource` to the API's stream endpoint that subscribes and forwards Server-Sent Events, driving an animated step tracker from Queued to Complete.
- **Idempotent uploads** &mdash; files are SHA-256 hashed; re-uploading the same contract returns the existing analysis instead of re-running the pipeline.
- **Distributed tracing** &mdash; OpenTelemetry propagates a trace ID from FastAPI through the Celery workers, exported to Jaeger, so a single upload is traceable across process boundaries.

## Architecture

Caddy is the only public entry point. The frontend and backend are co-located on one host so Better Auth and FastAPI can share the same Postgres without exposing a database to the internet.

```mermaid
flowchart TB
    Browser(["Browser"])

    subgraph Edge["Caddy (public entry, TLS)"]
        Caddy["Caddy reverse proxy"]
    end

    subgraph FE["Next.js 16 BFF"]
        Next["Server Components, Better Auth, EventSource"]
    end

    subgraph BE["FastAPI"]
        API["Auth-gated REST and SSE"]
    end

    subgraph Work["Celery workers"]
        Saga["Saga: parse, classify, score, redline, finalize"]
    end

    subgraph Stateful["Stateful services (internal only)"]
        PG[("PostgreSQL + pgvector")]
        Redis[("Redis: cache + pub/sub")]
        MQ[["RabbitMQ"]]
        MinIO[("MinIO: files")]
    end

    Browser -->|HTTPS| Caddy
    Caddy --> Next
    Caddy --> API
    Next -->|forwards session cookie| API
    API -->|publish task| MQ
    API --> PG
    API --> MinIO
    MQ --> Saga
    Saga --> PG
    Saga --> MinIO
    Saga -->|publish progress| Redis
    API -->|subscribe progress| Redis
    API -.->|SSE stream| Browser
```

### Upload pipeline (the saga in motion)

A single upload triggers a five-stage saga across FastAPI, RabbitMQ, and the Celery workers, with progress streamed back to the browser at every step.

```mermaid
sequenceDiagram
    actor U as Browser
    participant API as FastAPI
    participant Store as MinIO
    participant DB as Postgres
    participant MQ as RabbitMQ
    participant W as Celery worker
    participant R as Redis

    U->>API: POST /contracts/upload (PDF or DOCX)
    API->>Store: store file
    API->>DB: create contract (status queued)
    API->>MQ: publish parse task
    API-->>U: 202 contract_id

    U->>API: open EventSource /contracts/{id}/stream
    API->>R: subscribe contract:progress:{id}

    MQ->>W: parse
    W->>DB: save raw text, contract type
    W->>R: publish parsed
    R-->>API: progress event
    API-->>U: SSE parsed

    W->>W: classify (fan-out group, N clauses)
    W->>R: publish classified n of N
    API-->>U: SSE classified

    W->>DB: score risk vs pgvector templates
    W->>R: publish scored
    API-->>U: SSE scored

    W->>DB: save redlines (risky clauses only)
    W->>R: publish redlines ready
    API-->>U: SSE redlines

    W->>DB: status complete
    W->>R: publish complete
    API-->>U: SSE complete
    U->>API: GET /contracts/{id} (re-fetch)
    API-->>U: full analysis
```

The contract detail view re-fetches on terminal status and renders the Annotated Brief. See `clauseguard-project-spec.md` for the full architecture and phased build plan.

### Key design decisions

- **Single-box topology, not frontend-on-Vercel.** Better Auth (in Next.js) and FastAPI both need to read the same Postgres auth tables (`user`, `session`, `account`, `verification`). Co-locating them keeps Postgres private with no published host port, so no database is ever exposed to the internet. The trade-off is losing Vercel's edge CDN for the frontend, which is acceptable for a single-region app.
- **Saga state in the database, not task arguments.** Each stage reads and writes its own rows, so RabbitMQ messages stay tiny and a worker can be restarted mid-pipeline without losing or corrupting in-flight state.
- **Cross-user access returns 404, not 403.** A 403 would confirm a contract ID exists; 404 leaks nothing about which IDs are real.
- **Cookie scoped to the parent domain.** The auth cookie is set on `.clauseguard.dev` (`SameSite=Lax`, secure), so the apex frontend and the `api` subdomain both read it as first-party without CORS credential gymnastics.
- **A fresh Redis client for SSE, not the shared singleton.** The app's pooled Redis client binds to the first event loop; long-lived SSE subscriptions instead open a dedicated connection per stream and close it in `finally`, so a dropped browser tab can't leak connections.

## Distributed systems patterns

| Pattern | Implementation |
|---|---|
| Saga | Celery task chain: parse, classify, score, redline, finalize, each step persisting independently. |
| Circuit breaker | `pybreaker` wrapping all LLM calls, with fallback to a secondary provider. |
| Fan-out parallelism | `group()` for per-clause classification: N clauses become N parallel tasks. |
| Pub/Sub + SSE | Celery publishes to Redis; the API streams Server-Sent Events to the browser. |
| Idempotency | SHA-256 content hash; re-uploading a file returns the cached analysis. |
| Multi-layer caching | Redis exact-hash, then pgvector semantic similarity, then LLM. |
| Graceful degradation | If the LLM is unavailable, parsed results are returned without AI analysis. |
| Distributed tracing | OpenTelemetry trace ID propagated from FastAPI through Celery, exported to Jaeger. |

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Celery, SQLAlchemy 2.0 (async), asyncpg, pgvector
- **Frontend**: Next.js 16 (App Router, Turbopack), React 19, TypeScript, Tailwind CSS 4, shadcn/ui
- **Auth**: Better Auth 1.6.7 (email/password + Google OAuth)
- **Infrastructure**: PostgreSQL 16, Redis 7, RabbitMQ 3.13, MinIO, Caddy
- **AI**: LiteLLM with GPT-5.1 (primary) + Gemini 2.5 Flash (fallback)
- **Observability**: OpenTelemetry + Jaeger, Flower
- **Document generation**: python-docx with Aptos typography

## Deployment

ClauseGuard runs on a single Hetzner CX33 VPS (Ubuntu 24.04, Helsinki), with the entire stack orchestrated by Docker Compose and fronted by Caddy for automatic TLS.

- `clauseguard.dev` &rarr; Next.js frontend (standalone build), served by Caddy
- `api.clauseguard.dev` &rarr; FastAPI backend, served by Caddy
- `www.clauseguard.dev` &rarr; 301 redirect to apex
- Postgres, Redis, RabbitMQ, MinIO, Jaeger, and Flower have no published host ports.

Caddy disables response buffering on the SSE stream path so progress events flush immediately. Deploy configuration lives under `deploy/` (`docker-compose.prod.yml`, `Caddyfile`, `DEPLOY.md` runbook, `provision.sh`, `redeploy.sh`). All production compose commands layer the override on the base file:

```bash
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml <cmd>
```

### Backups and recovery

State (Postgres rows and the MinIO files they reference) is backed up together to Cloudflare R2 via `rclone`:

- `deploy/backup.sh` &mdash; `pg_dump` plus a tar of the MinIO volume into a single timestamped folder in R2, with automatic pruning of backups older than 14 days. Runs nightly via cron while the box is up, and on demand before any teardown.
- `deploy/restore.sh` &mdash; restores both halves from a chosen backup, with a destructive-action confirmation.

Because contract rows reference MinIO objects, restore is always "both or neither." The full loop (backup, total wipe, restore) has been tested end to end against real data.

## Quick Start (local)

### Prerequisites

- Docker and Docker Compose
- Python 3.12
- Node.js 20+
- A Google OAuth app (for sign-in via Google). See [Google OAuth setup](#google-oauth-setup) below.

### Setup

1. Clone the repo:
```bash
   git clone https://github.com/RajDesai-18/clauseguard.git
   cd clauseguard
```

2. Create the root `.env` from the example:
```bash
   cp .env.example .env
```

3. Create `frontend/.env.local` with your auth secrets (this file is git-ignored):
```env
   BETTER_AUTH_SECRET=<generate with: openssl rand -hex 32>
   BETTER_AUTH_URL=http://localhost:3000
   DATABASE_URL=postgresql://clauseguard:secret@localhost:5432/clauseguard
   GOOGLE_CLIENT_ID=<from Google Cloud Console>
   GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
   NEXT_PUBLIC_BETTER_AUTH_URL=http://localhost:3000
   NEXT_PUBLIC_API_URL=http://localhost:8000
```

4. Start the infrastructure (Postgres, Redis, RabbitMQ, MinIO, API, Worker, Flower):
```bash
   docker compose up -d
```

5. Run database migrations:
```bash
   docker compose exec api alembic upgrade head
```

6. Start the frontend (runs locally for fast hot reload, not in Docker):
```bash
   cd frontend
   npm install
   npm run dev
```

7. Open http://localhost:3000 and create an account at `/signup`.

### Service URLs

| Service        | URL                                  |
|----------------|--------------------------------------|
| Frontend       | http://localhost:3000                |
| API            | http://localhost:8000                |
| API Health     | http://localhost:8000/api/v1/health  |
| Auth endpoint  | http://localhost:3000/api/auth       |
| RabbitMQ UI    | http://localhost:15672               |
| MinIO Console  | http://localhost:9001                |
| Flower         | http://localhost:5555                |

### Google OAuth setup

1. Visit https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID (Application type: Web application)
3. Add authorized redirect URI: `http://localhost:3000/api/auth/callback/google`
4. Copy the Client ID and Client Secret into `frontend/.env.local`
5. While in development, add yourself as a test user under **OAuth consent screen** to bypass the unverified-app warning.

## Development

### Backend
```bash
cd backend
python -m venv .venv
.venv/Scripts/activate    # Windows
# source .venv/bin/activate  # Mac/Linux
pip install -e ".[dev]"

pytest -v                 # run tests
ruff check .              # lint
ruff format .             # format
tools pre                 # format + lint (Windows shortcut)
```

Backend tests run against the live Docker stack. The `db`-marked tests skip automatically when Postgres isn't reachable on `localhost:5432`.

### Frontend
```bash
cd frontend
npm install
npm run dev               # dev server (Turbopack, hot reload)
npm run build             # production build
npm run lint              # eslint
npx tsc --noEmit          # type check
```

The frontend runs locally rather than inside Docker for faster iteration. The Docker `api` service exposes port 8000, which the frontend reaches via `NEXT_PUBLIC_API_URL`.

### Database

Resetting the database during development:

```bash
docker compose down -v                                    # drop all volumes
docker compose up -d                                      # bring services back up
docker compose exec api alembic upgrade head              # apply baseline migration
```

Truncating just the user data (faster, keeps schema):

```bash
docker compose exec postgres psql -U clauseguard -d clauseguard \
  -c 'TRUNCATE "user", session, account, verification, contracts, clauses RESTART IDENTITY CASCADE;'
```

After either reset, clear cookies for `localhost:3000` in your browser (DevTools then Application then Cookies) so stale session tokens don't confuse the next sign-in.

## Contract Review Pipeline

When you upload a contract:

1. **Validate and store**: File type and size checked, SHA-256 hashed for idempotency, uploaded to MinIO, contract row created with status `queued`.
2. **Parse** (Celery): LlamaParse for PDFs, mammoth for DOCX. Raw text extracted; contract type detected.
3. **Classify** (fan-out): Each clause analysed in parallel by GPT-5.1 (via LiteLLM with a circuit breaker). Three-layer caching cuts LLM cost: Redis exact-hash lookup, pgvector semantic similarity (0.92 threshold), then LLM fallback.
4. **Score risk**: Each clause compared against market-standard templates via pgvector similarity. Overall risk computed: any red goes high, 3+ yellow goes high, any yellow goes medium, all green goes low.
5. **Generate redlines**: For yellow and red clauses only, GPT-5.1 generates a suggested revision.
6. **Finalize**: Contract status updated to `complete`, progress published to Redis (and through to the browser via SSE).

## Authentication

Authentication uses Better Auth with two methods:
- **Email + password** (8-char minimum)
- **Google OAuth**

The Better Auth session cookie is issued by the frontend. When the frontend's Server Components fetch from the FastAPI backend, the API client forwards the cookie because Node's `fetch` has no cookie jar. In production the cookie is scoped to `.clauseguard.dev`, so both the apex frontend and the `api` subdomain read it as first-party. The backend reads the cookie in a FastAPI dependency, validates the session row in Postgres, and attaches the User to every authenticated request.

All contract endpoints are auth-gated. Cross-user access returns 404 (not 403) to avoid leaking which contract IDs exist.

## Project Structure

```
clauseguard/
├── backend/
│   ├── alembic/versions/                # rebaselined migration as of Phase 4C
│   ├── app/
│   │   ├── api/                         # routes (contracts, health), auth deps
│   │   ├── core/                        # config, database, redis, storage, tracing
│   │   ├── middleware/                  # request_id, rate limiter
│   │   ├── models/                      # SQLAlchemy: user, auth, contract, clause, clause_template
│   │   ├── schemas/                     # Pydantic request/response
│   │   ├── services/                    # llm, parser, scorer, redline, progress, review_exporter
│   │   └── tasks/                       # Celery saga: parse, classify, score, redline, finalize
│   └── tests/
├── deploy/
│   ├── docker-compose.prod.yml          # production override (frontend + Caddy, no exposed datastore ports)
│   ├── Caddyfile                        # TLS, subdomain routing, SSE buffering off
│   ├── backup.sh / restore.sh           # Postgres + MinIO backup to Cloudflare R2
│   ├── provision.sh / redeploy.sh       # server setup and one-command redeploy
│   └── DEPLOY.md                        # full production runbook
└── frontend/
    ├── app/
    │   ├── (app)/                       # authenticated routes (server-side gated)
    │   │   ├── dashboard/               # contract library with delete
    │   │   ├── upload/                  # drag-and-drop, SSE-driven progress
    │   │   └── contract/[id]/           # analysis view
    │   ├── (auth)/                      # /login, /signup (inverse-gated)
    │   ├── api/
    │   │   ├── auth/[...all]/           # Better Auth route handler
    │   │   └── contracts/[id]/          # export (DOCX download) proxy
    │   ├── error.tsx                    # route-level error boundary
    │   ├── global-error.tsx             # last-resort error boundary
    │   └── not-found.tsx                # custom 404
    ├── components/
    │   ├── auth/                        # AuthCard, AuthInput, GoogleButton, forms
    │   ├── contract/                    # clause-card, clause-list (Annotated Brief)
    │   ├── dashboard/                   # dossier (table + stats + delete dialog)
    │   ├── features/                    # contract-detail-view, progress-tracker
    │   ├── shell/                       # rail, top-bar, account-menu
    │   ├── site/                        # marketing nav
    │   ├── system/                      # back-button and other system primitives
    │   └── ui/                          # shadcn primitives, risk-pill, status-badge
    ├── design-system/
    │   └── MASTER.md                    # design tokens, patterns, anti-patterns
    └── lib/
        ├── auth.ts                      # Better Auth server config
        ├── auth-client.ts               # Better Auth browser client
        ├── api/api-client.ts            # typed fetch with cookie forwarding
        └── hooks/use-contract-stream.ts # SSE consumer
```

## Roadmap

- **Email verification** &mdash; wired for Resend with DKIM on the live domain, gated behind a `sendVerificationEmail` callback. Deferred past v1.0.0 so it could be built and tested against real DNS rather than stubbed locally.
- **Public marketing page while authenticated** &mdash; let signed-in users still reach the landing page (currently they're routed straight to the dashboard).
- **Batch upload** &mdash; the pipeline is already fan-out parallel per clause; extending it to fan out across multiple contracts is a natural next step.
- **Rate-limit tuning under load** &mdash; the token-bucket middleware exists; production thresholds want real traffic to calibrate.

## License

MIT