#!/usr/bin/env bash
# Pull the latest code and redeploy the ClauseGuard stack on the VPS.
# Run from the repo root:  ./deploy/redeploy.sh
set -euo pipefail

BRANCH="${1:-feature/phase-8-deploy}"

echo "==> Pulling latest on ${BRANCH}"
git fetch origin
git checkout "${BRANCH}"
git pull origin "${BRANCH}"

echo "==> Rebuilding and restarting containers"
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d --build

echo "==> Running database migrations"
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml exec -T api alembic upgrade head

echo "==> Done. Current status:"
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml ps