# Running Citenest locally

## Prerequisites

- Python 3.12+
- Node.js 18+
- Ubuntu 24.04 (the setup script targets this distro)

---

## 1. One-time system setup

Installs PostgreSQL 16 + pgvector + Redis via apt and creates the `citenest` database:

```bash
cd backend
sudo bash scripts/setup_local_services.sh
```

---

## 2. Configure environment

```bash
cd backend
cp .env.example .env
```

Open `.env` and set at minimum:

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Required if `LLM_PROVIDER=openai` |
| `ANTHROPIC_API_KEY` | Required if `LLM_PROVIDER=anthropic` |
| `LLM_PROVIDER` | `openai` or `anthropic` |
| `STORAGE_PROVIDER` | Keep as `local` to skip MinIO |

Everything else works as-is for local development.

---

## 3. Start the backend API

Creates the virtualenv, installs dependencies, runs migrations, and starts uvicorn with hot-reload:

```bash
cd backend
bash scripts/dev.sh
```

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

---

## 4. Start the Celery worker (optional)

Required only for document processing (upload + embedding pipeline):

```bash
cd backend
source .venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info -Q documents
```

---

## 5. Start the frontend

```bash
cd frontend
npm install   # first time only
npm run dev
```

- Frontend: http://localhost:5173

---

## Creating an admin user

```bash
cd backend
.venv/bin/python scripts/create_admin.py \
  --email you@example.com \
  --name "Your Name" \
  --password "YourPass1"
```

The script grants the user an enterprise plan with unlimited documents, queries, and storage.

---

## Connecting to the database (DBeaver or any Postgres client)

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `citenest` |
| Username | `citenest` |
| Password | `citenest` |

---

## Stopping the application

| Component | How to stop |
|---|---|
| API (uvicorn) | `pkill -f "uvicorn app.main"` |
| Celery worker | `Ctrl+C` in its terminal |
| Frontend (Vite) | `Ctrl+C` in its terminal |
| Postgres + Redis | `sudo systemctl stop postgresql redis-server` |
