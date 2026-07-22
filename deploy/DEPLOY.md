# ClauseGuard Deployment Runbook

Single-box deployment: the entire stack (Next.js frontend, FastAPI backend,
Celery worker, Postgres, Redis, RabbitMQ, MinIO, Jaeger) runs on one VPS
behind Caddy, which terminates TLS and routes:

- `clauseguard.dev` -> frontend
- `www.clauseguard.dev` -> redirect to apex
- `api.clauseguard.dev` -> backend

Only Caddy (ports 80/443) is exposed to the internet; every datastore is
internal to the Docker network.

## Prerequisites

- A VPS running Ubuntu 24.04 (Hetzner CX33 or similar, 8 GB RAM recommended).
- Your SSH public key added to the box.
- DNS control for `clauseguard.dev` (records point at the VPS IP).
- Real secrets ready: `APP_SECRET_KEY`, datastore passwords, LLM API keys,
  Google OAuth client ID/secret.

## First-time deploy

1. **Provision the box** (as root on a fresh server):
   ```bash
   NEW_USER=raj bash provision.sh
   passwd raj            # set a strong password
   ```
   Log back in as `raj`.

2. **Clone the repo**:
   ```bash
   cd ~
   git clone https://github.com/RajDesai-18/clauseguard.git
   cd clauseguard
   git checkout feature/phase-8-deploy
   ```

3. **Create the production env file**:
   ```bash
   cp deploy/.env.prod.example .env
   nano .env     # fill in every secret; generate APP_SECRET_KEY with: openssl rand -hex 32
   ```

4. **Point DNS at the box** (in your DNS provider):
   - `A  clauseguard.dev      -> <VPS_IP>`
   - `A  www.clauseguard.dev  -> <VPS_IP>`
   - `A  api.clauseguard.dev  -> <VPS_IP>`
   Wait for propagation (verify with `dig clauseguard.dev +short`).

5. **Register the Google OAuth redirect URI** in Google Cloud Console:
   - `https://clauseguard.dev/api/auth/callback/google`

6. **Build and start the stack**:
   ```bash
   docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d --build
   ```
   Caddy will obtain TLS certificates automatically once DNS resolves.

7. **Run database migrations**:
   ```bash
   docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml exec api alembic upgrade head
   ```

8. **Verify**:
   - `https://api.clauseguard.dev/api/v1/health` returns healthy.
   - `https://clauseguard.dev` loads; sign up, sign in, upload a contract,
     watch the pipeline complete.

## Redeploying a change

```bash
cd ~/clauseguard
./deploy/redeploy.sh
```
(pulls latest, rebuilds, restarts, runs migrations).

## Re-hosting on a new box (after destroying the old one)

1. Provision a new box (steps 1-2 above).
2. Restore data from backup (see Backups) if you want prior data.
3. Recreate `.env` (step 3).
4. Update DNS A records to the new IP (step 4).
5. Build and start (step 6) and migrate (step 7).

## Backups (to Cloudflare R2)

A backup captures Postgres and the MinIO bucket, then uploads them to R2 so
data survives box destruction. Run before tearing down:

```bash
# Postgres dump
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml \
  exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup-db.sql

# MinIO data (from the named volume)
docker run --rm -v clauseguard_minio_data:/data -v "$PWD":/backup alpine \
  tar czf /backup/backup-minio.tar.gz -C /data .

# Upload backup-db.sql and backup-minio.tar.gz to R2 (rclone or aws-cli).
```
Restore reverses this: `psql < backup-db.sql` and untar into the MinIO volume
before first start.

## Notes

- Internal dashboards (Jaeger :16686, Flower :5555, RabbitMQ :15672) are not
  publicly exposed. Reach them with an SSH tunnel, e.g.:
  ```bash
  ssh -L 16686:localhost:16686 raj@<VPS_IP>
  ```
  (requires temporarily publishing the port in compose, or use docker exec).
- The API refuses to boot if `APP_SECRET_KEY` is default/short in production.
- `.env` is gitignored and must never be committed.