#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  echo "Missing .env. Copy .env.example to .env and fill required values."
  exit 1
fi

set -a
source .env
set +a

DOMAIN="${DOMAIN:-api.aurorablog.me}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"

if [ -z "$CERTBOT_EMAIL" ]; then
  echo "CERTBOT_EMAIL is required in .env"
  exit 1
fi

mkdir -p nginx/certbot nginx/letsencrypt logs

CERT_PATH="nginx/letsencrypt/live/${DOMAIN}/fullchain.pem"
if [ ! -f "$CERT_PATH" ]; then
  echo "No cert found for ${DOMAIN}. Issuing first certificate..."
  docker compose stop nginx || true
  docker run --rm -p 80:80 \
    -v "$ROOT_DIR/nginx/letsencrypt:/etc/letsencrypt" \
    -v "$ROOT_DIR/nginx/certbot:/var/www/certbot" \
    certbot/certbot certonly --standalone \
      -d "$DOMAIN" --email "$CERTBOT_EMAIL" --agree-tos --no-eff-email
fi

docker compose up -d db

docker compose run --rm backend alembic upgrade head

docker compose up -d --build backend nginx

# Start renewal loop in background (host)
if [ ! -f .renew.pid ] || ! kill -0 "$(cat .renew.pid)" 2>/dev/null; then
  nohup bash -c "while :; do docker compose run --rm certbot renew --webroot -w /var/www/certbot --deploy-hook 'docker compose exec -T nginx nginx -s reload'; sleep 12h; done" \
    > logs/renew.log 2>&1 &
  echo $! > .renew.pid
fi

cat <<EOM
Startup complete.
Verify:
  curl https://${DOMAIN}/
  curl https://${DOMAIN}/api/system/routes
EOM
