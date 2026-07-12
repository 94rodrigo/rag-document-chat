<div align="center">

# Docna

**Ask questions about your documents. Get answers with citations, streamed token by token.**

A production-grade RAG (Retrieval-Augmented Generation) SaaS — hybrid retrieval, cross-encoder re-ranking,
asynchronous document ingestion, Stripe billing, and a React frontend in six languages.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_+_pgvector-4169E1?logo=postgresql&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-workers-37814A?logo=celery&logoColor=white)
![Stripe](https://img.shields.io/badge/Stripe-billing-635BFF?logo=stripe&logoColor=white)
![Tests](https://img.shields.io/badge/tests-74_passing-3FB950)
![License](https://img.shields.io/badge/license-MIT-blue)

</div>

---

## What this is

Upload a PDF, Word document, or EPUB. Docna parses it, splits it into semantically coherent chunks,
embeds them, and indexes them for both **vector** and **keyword** search. Ask a question and it retrieves
the passages that actually answer it, re-ranks them with a cross-encoder, and streams an answer that
cites the exact document and page it came from.

The interesting part is not that it does RAG — it's *how*. Most "chat with your PDF" projects call
`similarity_search()` and hope. Docna runs two retrievers in parallel, fuses their rankings with
Reciprocal Rank Fusion, and re-scores the survivors with a model that reads the query and the passage
*together*. Every component — chunker, embedder, retriever, vector store, re-ranker — sits behind a
`Protocol` and is swapped by config, not by editing code.

![System architecture](docs/assets/architecture.svg)

---

## Features

**Retrieval**
- Hybrid search: dense vectors **and** BM25 keyword matching, fused with Reciprocal Rank Fusion
- Cross-encoder re-ranking (`ms-marco-MiniLM-L-6-v2`) narrows 20 candidates to the best 6
- Three chunking strategies: recursive, semantic (embedding-similarity boundaries), and hybrid
- Pluggable embedders (OpenAI, Voyage, local BGE) and vector stores (pgvector, Qdrant)
- Citations resolved back to the source document and page number

**Documents**
- PDF, DOCX, DOC, EPUB, TXT, Markdown — up to 50 MB
- Asynchronous ingestion on Celery workers: upload returns immediately, indexing happens in the background
- In-browser PDF viewer with the cited passage highlighted on the page

**Product**
- JWT auth with refresh-token rotation, plus **anonymous trial sessions** (5 questions, no signup)
- Stripe subscriptions: checkout, customer portal, and webhook-driven plan changes
- Per-plan quotas on documents, storage, and monthly queries — enforced in the service layer
- Tiered rate limiting (anonymous 10 rpm · free 60 rpm · pro 300 rpm)
- Answers streamed over Server-Sent Events
- Six languages: English, Portuguese, Spanish, French, German, Arabic (with RTL)

---

## How the RAG pipeline works

![RAG pipeline](docs/assets/rag-pipeline.svg)

### Why two retrievers?

Dense vector search understands *meaning*: ask "how do I cancel?" and it finds a passage about
"terminating your subscription." But embeddings blur exactly the things that are often most important —
part numbers, error codes, surnames, `SKU-4417-B`. BM25 keyword search nails those and understands
nothing else.

Running both and merging their results gets you the strengths of each. The problem is that their scores
are not comparable: a cosine similarity of `0.82` and a BM25 score of `14.3` live in different universes,
and normalising them requires calibration that drifts the moment you change the embedding model.

### Reciprocal Rank Fusion

RRF sidesteps the problem entirely by throwing the scores away and fusing on **rank** alone:

```
score(chunk) = Σ  1 / (k + rank_i)          k = 60
             i ∈ retrievers that returned it
```

A chunk that both retrievers rank 2nd scores `1/62 + 1/62 = 0.0323`, beating a chunk that only one
retriever ranked 1st (`1/61 = 0.0164`). **Consensus beats a single confident opinion** — which is exactly
the behaviour you want, and it needs no calibration between the two systems. `k = 60` is the standard
constant; raising it flattens the difference between adjacent ranks.

Implementation: [`backend/app/domain/rag/retrievers/hybrid.py`](backend/app/domain/rag/retrievers/hybrid.py)

### Re-ranking

The bi-encoders used for retrieval embed the query and the passage *separately* — fast, because chunk
vectors are precomputed, but it means the model never actually compares the two. A cross-encoder scores
the `(query, passage)` pair **jointly**, which is far more accurate and far too slow to run over a whole
corpus.

So Docna uses each for what it's good at: cheap retrieval casts a wide net (20 candidates), and the
expensive model re-scores only those, returning the top 6 to the LLM.

---

## Tech stack

| Layer | Choices |
|---|---|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2 |
| **Workers** | Celery + Redis, Flower dashboard |
| **Data** | PostgreSQL 16 + pgvector, Redis, MinIO / S3 |
| **RAG** | tiktoken, sentence-transformers, OpenAI / Voyage / BGE embeddings |
| **LLM** | OpenAI (`gpt-4o-mini`) or Anthropic (`claude-sonnet-4-6`) |
| **Billing** | Stripe (checkout, portal, webhooks) |
| **Frontend** | React 18, TypeScript, Vite, Tailwind, Radix UI, TanStack Query, Zustand |
| **Frontend extras** | react-pdf, react-markdown, framer-motion, i18next, Zod + React Hook Form |
| **Quality** | pytest, ruff, mypy, ESLint |

---

## Quickstart

### With Docker (everything, one command)

```bash
git clone <your-repo-url> docna && cd docna/backend
cp .env.example .env          # add your OPENAI_API_KEY
docker compose up -d
docker compose exec api alembic upgrade head
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API + interactive docs | http://localhost:8000/docs |
| Flower (task monitor) | http://localhost:5555 |
| MinIO console | http://localhost:9001 |

The `api` image reloads on code changes automatically unless `APP_ENV=production`; the `worker`
container needs a restart (`docker compose restart worker`) to pick up code changes since Celery
doesn't autoreload. For faster frontend iteration without a rebuild on every save, run it outside
Docker instead:

```bash
cd ../frontend
npm install
npm run dev                   # http://localhost:5173, proxies /api to localhost:8000
```

> `.env.example` defaults to `STORAGE_PROVIDER=local`, which writes uploaded files inside the
> `api`/`worker` containers' own filesystem rather than a mounted volume — they won't survive
> `docker compose down`. The bundled MinIO service is already wired up (`S3_ENDPOINT_URL` points
> at it inside the compose network); set `STORAGE_PROVIDER=minio` in `.env` for storage that
> persists across restarts.

### Running the backend locally

Requires PostgreSQL 16 with the `pgvector` extension, and Redis.

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# in a second terminal — the ingestion worker
celery -A app.workers.celery_app worker --loglevel=info
```

> The API will start without a worker, but uploaded documents will sit in `processing` forever —
> parsing, chunking, embedding, and indexing all happen on the worker.

---

## Configuration

Everything is driven by environment variables (see [`backend/.env.example`](backend/.env.example)).
Sensible defaults exist for all of them; in `production` the settings validator **refuses to boot**
on default secrets, a wildcard CORS origin, or debug mode.

**Essentials**

| Variable | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | — | Required for the default embedder and LLM |
| `DATABASE_URL` | `postgresql+asyncpg://docna:docna@localhost:5432/docna` | Needs pgvector |
| `REDIS_URL` | `redis://localhost:6379/0` | Cache; Celery uses DBs 1 and 2 |
| `SECRET_KEY` / `JWT_SECRET_KEY` | insecure defaults | Must be changed in production |
| `STORAGE_PROVIDER` | `local` | `minio`, `s3`, or `local` — `.env.example` defaults to `local`; see the Docker quickstart note above |

**Tuning the RAG pipeline** — the fun part:

| Variable | Default | Options |
|---|---|---|
| `RAG_CHUNKER` | `hybrid` | `recursive`, `semantic`, `hybrid` |
| `RAG_EMBEDDER` | `openai` | `openai`, `voyage`, `bge` (local) |
| `RAG_RETRIEVER` | `hybrid` | `dense`, `bm25`, `hybrid` |
| `RAG_VECTOR_STORE` | `pgvector` | `pgvector`, `qdrant` |
| `RAG_RERANK_ENABLED` | `true` | Cross-encoder re-ranking |
| `RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP` | `512` / `64` | Tokens |
| `RAG_TOP_K` / `RAG_PRE_RERANK_TOP_K` | `6` / `20` | Final chunks / candidates |
| `RAG_SIMILARITY_THRESHOLD` | `0.35` | Floor for dense retrieval |

Switching from cloud embeddings to a local GPU-free model is a one-line change:
`RAG_EMBEDDER=bge`.

---

## API

All routes are under `/api/v1`. Interactive docs at `/docs`.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/auth/register` · `/auth/login` · `/auth/refresh` · `/auth/logout` | JWT auth |
| `POST` | `/auth/anonymous` | Trial session — 5 questions, no signup |
| `GET` | `/auth/me` | Current user |
| `POST` | `/documents` | Upload (enqueues ingestion) |
| `GET` | `/documents` · `/documents/{id}` | List / detail with processing status |
| `GET` | `/documents/search` | Semantic search across the corpus |
| `GET` | `/documents/{id}/file` · `/{id}/chunks` | Source file / indexed chunks |
| `DELETE` | `/documents/{id}` | Delete document and its vectors |
| `POST` | `/conversations` | Start a conversation |
| `POST` | `/conversations/{id}/messages` | **Ask a question — streams the answer over SSE** |
| `GET` | `/conversations` · `/conversations/{id}` | History |
| `GET` | `/billing/plans` · `/billing/subscription` · `/billing/usage` | Plan and usage state |
| `POST` | `/billing/checkout` · `/billing/portal` | Stripe checkout / customer portal |
| `POST` | `/billing/webhook` | Stripe events (signature-verified) |
| `GET`/`PATCH`/`DELETE` | `/users/me` | Profile, password, account deletion |

### Plans

| | Free | Pro ($29/mo) | Enterprise |
|---|---|---|---|
| Documents | 10 | Unlimited | Unlimited |
| Queries / month | 100 | 2,000 | Unlimited |
| Storage | 50 MB | 10 GB | Unlimited |
| Rate limit | 60 rpm | 300 rpm | Custom |

---

## Testing

```bash
cd backend
pytest                                    # 74 unit tests, ~0.2s, no DB or network required
pytest --cov=app --cov-report=term-missing
```

The suite covers the logic that is most expensive to get wrong: RRF fusion arithmetic, chunker
invariants, plan quota enforcement, and Stripe webhook handling. Repository doubles stand in for the
database, so the **service logic itself runs under test** rather than being mocked out.

Writing these tests caught two real bugs. `RecursiveChunker` documented a guarantee — *"every chunk is
within token limits"* — that it did not keep: it decided whether a split fit by summing the token counts
of splits measured *individually*, then emitted `" ".join(...)`, and joining re-tokenises the boundaries
into more tokens than the parts cost separately. Both that and an unchecked overlap carry-over are fixed,
and the guarantee is now enforced by a test.

---

## Project structure

```
backend/
├─ app/
│  ├─ api/v1/           # Route handlers — thin, no business logic
│  ├─ domain/           # One package per bounded context
│  │  ├─ auth/          #   models · schemas · repository · service
│  │  ├─ documents/
│  │  ├─ conversations/
│  │  ├─ billing/       #   quotas + Stripe
│  │  └─ rag/           #   the interesting one ↓
│  │     ├─ chunkers/   #   recursive · semantic · hybrid
│  │     ├─ embedders/  #   openai · voyage · bge
│  │     ├─ retrievers/ #   dense · bm25 · hybrid (RRF)
│  │     ├─ stores/     #   pgvector · qdrant
│  │     ├─ reranker.py #   cross-encoder
│  │     └─ pipeline.py #   assembles the above from config
│  ├─ infrastructure/   # DB, Redis, S3, LLM clients
│  ├─ middleware/       # Auth, rate limiting, structured logging
│  └─ workers/          # Celery tasks
├─ migrations/          # Alembic
└─ tests/

frontend/src/
├─ features/            # auth · chat · documents · billing · dashboard · settings · landing
│  └─ <feature>/        #   components · hooks · pages · stores · schemas
└─ shared/              # ui · lib · i18n · stores · types
```

Each domain package follows the same shape — `models` (SQLAlchemy) → `schemas` (Pydantic) →
`repository` (queries) → `service` (business rules) — so routes stay thin and the business rules stay
testable without a web server.

---

## Design decisions

**Ports over branches.** Every swappable piece of the RAG pipeline is a `Protocol`, and
`pipeline.py` assembles the concrete implementations from settings. Adding a new vector store means
writing one class, not touching the retrieval code.

**Ingestion is asynchronous, and that's a product decision.** Parsing a 300-page PDF, embedding a few
thousand chunks, and indexing them takes far longer than an HTTP request should. The upload endpoint
enqueues and returns; the client polls status. It also means a slow embedding provider can't take the
API down with it.

**Quotas live in the service layer, not the route.** `UsageLimitService.assert_can_upload()` and
`assert_can_query()` are called by the services that do the work, so a new entry point can't
accidentally bypass billing.

**Webhooks are the source of truth for subscriptions.** The client never tells the backend that a
payment succeeded — Stripe does, over a signature-verified webhook. A user who closes the browser mid-checkout
still gets the plan they paid for.

---

## Known gaps

Being honest about what a reader will notice:

- **No integration tests yet.** The unit suite is real, but nothing exercises the API end-to-end against
  a live Postgres + pgvector. That's the next piece of work.
- **The database engine is created at import time** (`infrastructure/database.py`), which couples every
  module import to a configured database. It should move behind a factory.
- **`_rrf_fuse` mutates the chunks it is handed** rather than returning copies — a sharp edge, currently
  pinned by a test.
- **`mypy --strict` does not pass.** It runs in CI as an advisory step rather than a gate, so the number
  is visible without pretending the codebase is clean.
- **CI doesn't build or run the Docker images.** [`ci.yml`](.github/workflows/ci.yml) lints and tests the
  source directly; a break in `docker-compose.yml` or either Dockerfile wouldn't be caught until someone
  actually runs `docker compose up`.

---

## Continuous integration

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push and pull request:

| Job | Steps |
|---|---|
| **Backend** | `ruff check` → `pytest --cov` → `mypy` *(advisory, non-blocking)* |
| **Frontend** | `eslint` → `tsc --noEmit` → `vite build` |

Both jobs gate on lint and pass today. Getting there meant fixing the frontend's tooling, which was
quietly broken: `npm run lint` had no ESLint config at all, and `npm run typecheck` failed on an invalid
`ignoreDeprecations` value in `tsconfig.json`. Neither script had ever run successfully.

---

## License

[MIT](LICENSE) © 2026 Rodrigo Costa

---

<div align="center">
<sub>Built by Rodrigo Costa</sub>
</div>
