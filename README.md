# ClauseGuard

AI-powered contract review platform for startups and freelancers.

Upload a contract (NDA, MSA, SOW, freelance agreement) and ClauseGuard returns a clause-by-clause risk analysis, plain-English explanations, market-standard comparisons, and AI-suggested redlines. Export the review as a Word document, or delete it when you're done.

## Features

- **Upload**: Drag and drop PDFs or DOCX files; idempotent via content hash.
- **Live progress**: SSE streams pipeline status (parsing, classifying, scoring, generating redlines) directly to the browser.
- **Annotated review**: Silent on safe clauses, flagged on risky ones. Each concern explains why it matters, how it compares to market standards, and what to ask for instead.
- **Word export**: Download a typeset DOCX review with Aptos typography, ready to send to a client or counter-party.
- **Library management**: Dashboard summarises risk across all your contracts; delete with full purge (DB row + clauses + MinIO file).
- **Auth-gated, privacy-aware**: Cross-user access returns 404, not 403, so contract IDs aren't leakable.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Celery, SQLAlchemy 2.0 (async), asyncpg, pgvector
- **Frontend**: Next.js 16 (App Router, Turbopack), React 19, TypeScript, Tailwind CSS 4, shadcn/ui
- **Auth**: Better Auth 1.6.7 (email/password + Google OAuth)
- **Infrastructure**: PostgreSQL 16, Redis 7, RabbitMQ 3.13, MinIO
- **AI**: LiteLLM with GPT-5.1 (primary) + Gemini 2.5 Flash (fallback)
- **Document generation**: python-docx with Aptos typography

## Quick Start

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

The frontend runs locally rather than inside Docker for faster iteration. The Docker `api` service exposes port 8000, which the frontend reaches via `NEXT_PUBLIC_API_URL`. The frontend also exposes server-side proxy routes (`/api/contracts/[id]/stream` for SSE, `/api/contracts/[id]/export` for DOCX downloads) that forward Better Auth session cookies to FastAPI.

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

## Architecture

```
Next.js 16 frontend (BFF)         FastAPI backend            Celery saga
  - Better Auth                     - Auth-gated endpoints     - Parse (LlamaParse / mammoth)
  - Server Component session gate   - Forwards cookies         - Classify (fan-out via group)
  - Client-side session via hook    - Cross-user 404 not 403   - Score risk (vs market templates)
  - SSE proxy for live progress     - DOCX export endpoint     - Generate redlines
  - DOCX download proxy             - Delete with cascade      - Finalize
        |                                |                          |
        +--------- HTTP (REST + SSE) ----+                          |
                                         |                          |
                  Postgres (pgvector) <--+--> RabbitMQ <------------+
                  Redis (cache + pub/sub for SSE)
                  MinIO (file storage)
```

The Celery pipeline publishes progress to Redis Pub/Sub; the Next.js SSE proxy route subscribes and streams events to the browser, where the contract detail view re-fetches data on terminal status.

See `clauseguard-project-spec.md` for the full architecture and phased build plan.

## Authentication

Authentication uses Better Auth with two methods:
- **Email + password** (8-char minimum, no email verification in dev)
- **Google OAuth**

The Better Auth session cookie is set on `localhost:3000` (the frontend). When the frontend's Server Components fetch from the FastAPI backend on `localhost:8000`, the API client manually forwards the cookie because Node's `fetch` doesn't have a cookie jar. The backend reads the cookie in a FastAPI dependency, validates the session row in Postgres, and attaches the User to every authenticated request.

All contract endpoints are auth-gated. Cross-user access returns 404 (not 403) to avoid leaking which contract IDs exist.

## Contract Review Pipeline

When you upload a contract:

1. **Validate and store**: File type and size checked, SHA-256 hashed for idempotency, uploaded to MinIO, contract row created with status `queued`.
2. **Parse** (Celery): LlamaParse for PDFs, mammoth for DOCX. Raw text extracted; contract type detected.
3. **Classify** (fan-out): Each clause analysed in parallel by GPT-5.1 (via LiteLLM with a circuit breaker). Three-layer caching cuts LLM cost: Redis exact-hash lookup, pgvector semantic similarity (0.92 threshold), then LLM fallback.
4. **Score risk**: Each clause compared against market-standard templates via pgvector similarity. Overall risk computed: any red goes high, 3+ yellow goes high, any yellow goes medium, all green goes low.
5. **Generate redlines**: For yellow and red clauses only, GPT-5.1 generates a suggested revision.
6. **Finalize**: Contract status updated to `complete`, progress published to Redis (and through to the browser via SSE).

Throughout, the frontend's SSE hook drives a live progress tracker; on completion, the page re-fetches the contract and renders the Annotated Brief view.

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
└── frontend/
    ├── app/
    │   ├── (app)/                       # authenticated routes (server-side gated)
    │   │   ├── dashboard/               # contract library with delete
    │   │   ├── upload/                  # drag-and-drop, SSE-driven progress
    │   │   └── contract/[id]/           # analysis view
    │   ├── (auth)/                      # /login, /signup (inverse-gated)
    │   ├── api/
    │   │   ├── auth/[...all]/           # Better Auth route handler
    │   │   └── contracts/[id]/
    │   │       ├── stream/              # SSE proxy with auth check
    │   │       └── export/              # DOCX download proxy
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

## License

MIT