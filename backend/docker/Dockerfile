# syntax=docker/dockerfile:1

# ── base: system deps + the package, shared by the api and worker images ──────
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system app && useradd --system --gid app --create-home app

# sentence-transformers pulls in torch, and the default PyPI wheel bundles a
# full CUDA/cuDNN/NCCL stack (~3GB) that this slim, GPU-less image can never
# use. Install the CPU-only build first so the -e . install below is already
# satisfied by it instead of pulling the GPU wheel. Scoped to this image only —
# bare-metal dev installs (`pip install -e .`) are untouched and can still get
# a GPU build if the machine has one.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch

# Dependency layer cached separately from the source copy below so editing
# app code doesn't bust the pip install cache.
COPY pyproject.toml .
RUN pip install -e .

COPY . .
# storage/ is excluded by .dockerignore (runtime data, not source), so it doesn't exist
# yet here. Created explicitly, owned by app, so that when compose mounts a fresh named
# volume over it, Docker seeds the volume from this dir instead of a root-owned empty
# one — otherwise the app user can't write to it (PermissionError) at runtime.
RUN mkdir -p storage && chown -R app:app /app
USER app

# ── api ─────────────────────────────────────────────────────────────────────
FROM base AS api

EXPOSE 8000

# 127.0.0.1, not localhost: avoids depending on IPv4/IPv6 resolution order,
# which varies across Docker environments (see the frontend Dockerfile for a
# case where it actually broke the healthcheck).
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

# --no-proxy-headers: uvicorn must not derive the client IP from X-Forwarded-For.
# The app trusts that header only when TRUSTED_PROXY_COUNT > 0 (see config), so
# behind a reverse proxy set TRUSTED_PROXY_COUNT to the number of trusted hops
# and have the proxy overwrite (not append) X-Forwarded-For.
#
# APP_ENV=production runs 4 worker processes with no autoreload. Any other
# value (the .env.example default is "development") runs a single reloading
# process, so the docker-compose bind mount of ./app actually picks up code
# changes live instead of silently doing nothing.
CMD if [ "$APP_ENV" = "production" ]; then \
      exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --no-proxy-headers; \
    else \
      exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --no-proxy-headers; \
    fi

# ── worker ──────────────────────────────────────────────────────────────────
FROM base AS worker

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD celery -A app.workers.celery_app:celery inspect ping -d celery@$HOSTNAME || exit 1

CMD ["celery", "-A", "app.workers.celery_app:celery", "worker", \
     "--loglevel=info", "--concurrency=4", "-Q", "default,documents,emails"]
