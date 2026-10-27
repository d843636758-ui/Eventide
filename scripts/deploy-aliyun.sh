#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/mcp-stack/apps/eventide
DATA_DIR=/opt/mcp-stack/data/eventide
SERVICE_DIR=/opt/mcp-stack/services/eventide
CADDYFILE=/opt/mcp-stack/proxy/Caddyfile
DOMAIN=eventide.xunzhou.space
REPOSITORY=https://github.com/d843636758-ui/Eventide.git

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this script as root (sudo)." >&2
  exit 1
fi

for command in docker git openssl python3; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Missing required command: $command" >&2
    exit 1
  }
done

docker network inspect mcp-edge >/dev/null 2>&1 || {
  echo "Docker network mcp-edge does not exist." >&2
  exit 1
}

mkdir -p "$(dirname "$APP_DIR")" "$DATA_DIR" "$SERVICE_DIR"
chmod 700 "$DATA_DIR" "$SERVICE_DIR"

if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  if [ -e "$APP_DIR" ] && [ "$(find "$APP_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]; then
    echo "$APP_DIR exists and is not an Eventide git checkout; refusing to overwrite it." >&2
    exit 1
  fi
  rm -d "$APP_DIR" 2>/dev/null || true
  git clone --depth 1 "$REPOSITORY" "$APP_DIR"
fi

ENV_FILE="$SERVICE_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  API_KEY=$(openssl rand -hex 32)
  MCP_PATH_TOKEN=$(openssl rand -hex 32)
  umask 077
  cat >"$ENV_FILE" <<EOF
EVENTIDE_API_KEY=$API_KEY
EVENTIDE_MCP_PATH_TOKEN=$MCP_PATH_TOKEN
EVENTIDE_PUBLIC_HOST=$DOMAIN
EMOTION_BASE_URL=https://emotion.xunzhou.space
OB_BASE_URL=https://ombre.xunzhou.space
OB_HOOK_TOKEN=
DATA_DIR=/data
PORT=8080
EOF
fi

cat >"$SERVICE_DIR/compose.yaml" <<EOF
services:
  eventide:
    build:
      context: $APP_DIR
    container_name: eventide
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - $DATA_DIR:/data
    networks:
      - mcp-edge
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"
      interval: 30s
      timeout: 5s
      retries: 3

networks:
  mcp-edge:
    external: true
EOF

if [ ! -f "$CADDYFILE" ]; then
  echo "Caddyfile not found at $CADDYFILE" >&2
  exit 1
fi

CADDY_BACKUP="$CADDYFILE.before-eventide-$(date -u +%Y%m%dT%H%M%SZ)"
cp "$CADDYFILE" "$CADDY_BACKUP"

python3 - <<'PY'
from pathlib import Path
import re

path = Path('/opt/mcp-stack/proxy/Caddyfile')
text = path.read_text()
domain = 'eventide.xunzhou.space'
block = '''eventide.xunzhou.space {
    reverse_proxy eventide:8080
}'''

pattern = re.compile(r'(?ms)^eventide\.xunzhou\.space\s*\{.*?^\}')
if pattern.search(text):
    text = pattern.sub(block, text, count=1)
else:
    text = text.rstrip() + '\n\n' + block + '\n'
path.write_text(text)
PY

cd "$SERVICE_DIR"
docker compose up -d --build

if ! docker exec caddy caddy validate --config /etc/caddy/Caddyfile; then
  cp "$CADDY_BACKUP" "$CADDYFILE"
  docker exec caddy caddy reload --config /etc/caddy/Caddyfile || true
  exit 1
fi

if ! docker exec caddy caddy reload --config /etc/caddy/Caddyfile; then
  cp "$CADDY_BACKUP" "$CADDYFILE"
  docker exec caddy caddy reload --config /etc/caddy/Caddyfile || true
  exit 1
fi

for _ in $(seq 1 20); do
  if docker inspect -f '{{.State.Health.Status}}' eventide 2>/dev/null | grep -qx healthy; then
    break
  fi
  sleep 2
done

docker compose ps
curl -fsS --max-time 15 "https://$DOMAIN/health"
printf '\nEVENTIDE_DEPLOYED\n'
printf 'State file: %s/eventide_state.json\n' "$DATA_DIR"
printf 'Environment: %s\n' "$ENV_FILE"
printf 'Caddy backup: %s\n' "$CADDY_BACKUP"
