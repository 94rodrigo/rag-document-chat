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

COPY pyproject.toml .
RUN pip install -e ".[dev]"

COPY . .

RUN alembic upgrade head 2>/dev/null || true

EXPOSE 8000

# --no-proxy-headers: uvicorn must not derive the client IP from X-Forwarded-For.
# The app trusts that header only when TRUSTED_PROXY_COUNT > 0 (see config), so
# behind a reverse proxy set TRUSTED_PROXY_COUNT to the number of trusted hops and
# have the proxy overwrite (not append) X-Forwarded-For.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--no-proxy-headers"]
