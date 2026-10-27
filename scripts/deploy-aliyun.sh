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
  rmdir "$APP_DIR" 2>/dev/null || true
  git clone --depth 1 "$REPOSITORY" "$APP_DIR"
fi

if [ ! -f "$DATA_DIR/eventide_state.json" ] && [ "${ALLOW_EMPTY_EVENTIDE_DATA:-0}" != "1" ]; then
  cat >&2 <<EOF
No migrated Eventide state was found at:
  $DATA_DIR/eventide_state.json

Copy the Zeabur state file here before deploying. To intentionally create a
fresh state, rerun with ALLOW_EMPTY_EVENTIDE_DATA=1.
EOF
  exit 1
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
EVENTIDE_LEGACY_PUBLIC_HOST=eventidemcp.zeabur.app
EMOTION_BASE_URL=http://emotion:3000
OB_BASE_URL=http://ombre-brain:8000
OB_HOOK_TOKEN=
DATA_DIR=/data
PORT=8080
EOF
fi
chmod 600 "$ENV_FILE"

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

path = Path("/opt/mcp-stack/proxy/Caddyfile")
text = path.read_text(encoding="utf-8")
block = """eventide.xunzhou.space {
    reverse_proxy eventide:8080
}"""

managed = re.compile(
    r"(?ms)^# BEGIN EVENTIDE\n.*?^# END EVENTIDE\n?"
)
text = managed.sub("", text)

lines = text.splitlines()
kept = []
index = 0
start = re.compile(r"^eventide\.xunzhou\.space\s*\{")
while index < len(lines):
    if not start.match(lines[index]):
        kept.append(lines[index])
        index += 1
        continue

    depth = 0
    while index < len(lines):
        depth += lines[index].count("{")
        depth -= lines[index].count("}")
        index += 1
        if depth == 0:
            break

text = "\n".join(kept).rstrip()
text += "\n\n# BEGIN EVENTIDE\n" + block + "\n# END EVENTIDE\n"
path.write_text(text, encoding="utf-8")
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

if ! docker inspect -f '{{.State.Health.Status}}' eventide 2>/dev/null | grep -qx healthy; then
  docker compose ps >&2
  docker logs --tail 100 eventide >&2 || true
  exit 1
fi

curl -fsS --max-time 15 "https://$DOMAIN/health"
printf '\nEVENTIDE_DEPLOYED\n'
MCP_PATH_TOKEN=$(sed -n 's/^EVENTIDE_MCP_PATH_TOKEN=//p' "$ENV_FILE")
printf 'MCP URL: https://%s/%s/mcp\n' "$DOMAIN" "$MCP_PATH_TOKEN"
printf 'State file: %s/eventide_state.json\n' "$DATA_DIR"
printf 'Environment: %s\n' "$ENV_FILE"
printf 'Caddy backup: %s\n' "$CADDY_BACKUP"
