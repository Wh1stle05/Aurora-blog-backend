# Backend Startup Guide

This guide explains how to use `scripts/start.sh` on the production branch.

## What The Script Does

`scripts/start.sh` is the one-command startup entry for this backend. It will:

- load variables from `.env`
- ask Certbot whether a certificate lineage already exists for `DOMAIN`
- request the first certificate with Certbot if no certificate is present
- start PostgreSQL
- run Alembic migrations
- build and start the backend and Nginx containers
- start a background renewal loop for TLS certificates

## Requirements

Before running the script, make sure the server has:

- Docker installed
- Docker Compose available as `docker compose`
- ports `80` and `443` open to the internet
- DNS already pointed at the server for `api.aurorablog.me`

This branch assumes you are deploying from the backend repository root.

## Required Files

You need these files before startup:

- `.env`
- `docker-compose.yml`
- `scripts/start.sh`

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

## Required `.env` Values

At minimum, fill in the production values in `.env`:

```env
ENV=prod
DATABASE_URL=postgresql+psycopg://blog:blogpass@db:5432/blogdb
JWT_SECRET=replace-with-a-long-random-secret
ADMIN_EMAILS=your-admin-email@example.com
CORS_ORIGINS=https://aurorablog.me,https://www.aurorablog.me,https://admin.aurorablog.me
RESEND_API_KEY=...
RESEND_FROM=Aurora Blog <no-reply@aurorablog.me>
TURNSTILE_SECRET_KEY=...
R2_ENDPOINT=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET=...
R2_PUBLIC_BASE_URL=https://cdn.aurorablog.me
REFRESH_TOKEN_EXPIRES_DAYS=30
REFRESH_TOKEN_PEPPER=replace-with-a-random-secret
DOMAIN=api.aurorablog.me
CERTBOT_EMAIL=your-email@example.com
```

Notes:

- `CERTBOT_EMAIL` is mandatory. The script will stop immediately if it is missing.
- `DOMAIN` defaults to `api.aurorablog.me` if omitted, but it is better to set it explicitly.
- R2 variables are required in this backend because file storage is R2-only in production.

## First Startup

Run from the repository root:

```bash
bash scripts/start.sh
```

On first run, the script does this in order:

1. loads `.env`
2. creates `nginx/certbot`, `nginx/letsencrypt`, and `logs`
3. checks Certbot's stored certificate lineage for `$DOMAIN`
4. if no certificate exists, requests one with Certbot using standalone mode on port `80`
5. starts the database container
6. runs `alembic upgrade head`
7. starts or rebuilds `backend` and `nginx`
8. starts a background certificate renewal loop if one is not already running

If everything completes, the script prints:

```text
Startup complete.
Verify:
  curl https://<DOMAIN>/
  curl https://<DOMAIN>/api/system/routes
```

## Repeat Startup

For later deployments, run the same command again:

```bash
bash scripts/start.sh
```

If the certificate already exists, the script skips initial certificate issuance and continues with:

- `docker compose up -d db`
- `docker compose run --rm backend alembic upgrade head`
- `docker compose up -d --build backend nginx`

This means you can use the same command after code updates.
The certificate check is non-interactive, so rerunning after `git pull` will not stop on a Certbot prompt for an existing matching certificate.

## Certificate Renewal

The script starts a background renewal loop on the host machine:

- it writes the process id to `.renew.pid`
- it logs renewal output to `logs/renew.log`
- it runs every 12 hours
- after renewal, it reloads Nginx inside the container

The loop is only started if `.renew.pid` is missing or the recorded process is no longer running.

## Useful Commands

Check container status:

```bash
docker compose ps
```

Check backend logs:

```bash
docker compose logs -f backend
```

Check Nginx logs:

```bash
docker compose logs -f nginx
```

Check renewal logs:

```bash
tail -f logs/renew.log
```

Stop the stack:

```bash
docker compose down
```

Stop only the renewal loop:

```bash
kill "$(cat .renew.pid)"
rm -f .renew.pid
```

## Common Failures

### `.env` missing

Error:

```text
Missing .env. Copy .env.example to .env and fill required values.
```

Fix:

- create `.env`
- fill the required variables
- run the script again

### `CERTBOT_EMAIL` missing

Error:

```text
CERTBOT_EMAIL is required in .env
```

Fix:

- add `CERTBOT_EMAIL` to `.env`
- rerun the script

### Certificate request fails

Typical causes:

- `DOMAIN` does not point to the server yet
- port `80` is blocked by firewall or cloud security rules
- another process is already using port `80`

Fix:

- verify DNS for `api.aurorablog.me`
- verify port `80` is reachable from the internet
- stop any service already bound to port `80`

### Migration fails

If `docker compose run --rm backend alembic upgrade head` fails:

- inspect backend output from the script
- verify database settings in `.env`
- retry after fixing the schema or connection issue

## Recommended Deployment Flow

For a fresh server:

```bash
git checkout releasev1.0.4
cp .env.example .env
bash scripts/start.sh
```

For later updates:

```bash
git pull
bash scripts/start.sh
```
