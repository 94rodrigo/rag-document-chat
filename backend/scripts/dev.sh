#!/bin/bash
# Start the API server for local development.
# Prerequisites: run scripts/setup_local_services.sh once (needs sudo).
set -e
cd "$(dirname "$0")/.."

# ── Verify services are up ────────────────────────────────────────────────────
check_service() {
  local name="$1"
  if ! systemctl is-active --quiet "$name"; then
    echo "ERROR: $name is not running."
    echo "  Start it with: sudo systemctl start $name"
    exit 1
  fi
}
check_service postgresql
check_service redis-server

# ── Python env ────────────────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "==> Creating virtualenv..."
  python3 -m venv .venv
fi

echo "==> Activating virtualenv..."
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Installing dependencies..."
pip install -q -e ".[dev]"

# ── .env ──────────────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "==> Copying .env.example → .env"
  cp .env.example .env
  echo "    ⚠  Edit .env and set OPENAI_API_KEY before using the chat feature."
fi

# ── Migrations ────────────────────────────────────────────────────────────────
echo "==> Running migrations..."
alembic upgrade head

# ── MinIO (optional, for document storage) ────────────────────────────────────
# If you don't have MinIO, uploads will fail. Either:
#   a) Install MinIO: https://min.io/docs/minio/linux/index.html
#   b) Set STORAGE_PROVIDER=local in .env (add local storage support)
#   c) Use real S3 credentials in .env

# ── API server ────────────────────────────────────────────────────────────────
echo ""
echo "==> Starting Citenest API on http://localhost:8000"
echo "    Docs: http://localhost:8000/docs"
echo ""
# --no-proxy-headers: don't let uvicorn rewrite the client address from
# X-Forwarded-For. The app decides whether to trust that header via
# TRUSTED_PROXY_COUNT (default 0 = never), so rate-limit identities can't be
# spoofed by a client-supplied X-Forwarded-For.
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --no-proxy-headers \
  --reload \
  --reload-dir app
