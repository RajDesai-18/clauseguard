# ClauseGuard

AI-Powered Contract Review Platform for Startups & Freelancers.

Upload contracts (NDAs, MSAs, SOWs, freelance agreements) and get instant, plain-English risk analysis, clause-by-clause breakdowns, and AI-suggested redlines.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Celery, SQLAlchemy 2.0
- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS 4
- **Infrastructure**: PostgreSQL 16, Redis 7, RabbitMQ 3.13, MinIO
- **AI**: LiteLLM (GPT-4.1 + Claude Sonnet 4 fallback)

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12
- Node.js 20+

### Setup

1. Clone the repo:
```bash
   git clone https://github.com/RajDesai-18/clauseguard.git
   cd clauseguard
```

2. Create `.env` from the example:
```bash
   cp .env.example .env
```

3. Start all services:
```bash
   docker compose up -d
```

4. Run database migrations:
```bash
   cd backend
   python -m venv .venv
   .venv/Scripts/activate  # Windows
   # source .venv/bin/activate  # Mac/Linux
   pip install -e ".[dev]"
   alembic upgrade head
```

5. Start the frontend:
```bash
   cd frontend
   npm install
   npm run dev
```

### Service URLs

| Service      | URL                          |
|-------------|------------------------------|
| Frontend    | http://localhost:3000         |
| API         | http://localhost:8000         |
| API Health  | http://localhost:8000/api/v1/health |
| RabbitMQ UI | http://localhost:15672        |
| MinIO Console | http://localhost:9001       |
| Flower      | http://localhost:5555         |

## Development

### Backend
```bash
cd backend
.venv/Scripts/activate
pytest -v          # run tests
ruff check .       # lint
ruff format .      # format
```

### Frontend
```bash
cd frontend
npm run dev        # dev server
npm run build      # production build
npm run lint       # eslint
```

## License

MIT