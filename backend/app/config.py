from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    development = "development"
    staging = "staging"
    production = "production"
    testing = "testing"


class LLMProvider(StrEnum):
    openai = "openai"
    anthropic = "anthropic"


class StorageProvider(StrEnum):
    local = "local"
    s3 = "s3"
    minio = "minio"


class LogFormat(StrEnum):
    json = "json"
    console = "console"


class EmbedderType(StrEnum):
    openai = "openai"
    voyage = "voyage"
    bge = "bge"


class ChunkerType(StrEnum):
    recursive = "recursive"
    semantic = "semantic"
    hybrid = "hybrid"


class RetrieverType(StrEnum):
    dense = "dense"
    bm25 = "bm25"
    hybrid = "hybrid"


class VectorStoreType(StrEnum):
    pgvector = "pgvector"
    qdrant = "qdrant"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_env: Environment = Environment.development
    app_debug: bool = False
    secret_key: str = "change-this-in-production"
    allowed_origins: list[str] = ["http://localhost:5173"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            try:
                import json
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return [o.strip() for o in v.split(",")]
        return v

    @model_validator(mode="after")
    def enforce_production_security(self) -> Settings:
        if self.app_env == Environment.production:
            insecure_defaults = {
                "change-this-in-production",
                "change-this-to-a-long-random-string-in-production",
            }
            if self.secret_key in insecure_defaults:
                raise ValueError("SECRET_KEY must be changed from default in production")
            if self.jwt_secret_key in (
                "change-this-jwt-secret",
                "change-this-jwt-secret-in-production",
            ):
                raise ValueError("JWT_SECRET_KEY must be changed from default in production")
            if "*" in self.allowed_origins:
                raise ValueError("ALLOWED_ORIGINS must not contain wildcard (*) in production")
            if self.app_debug:
                raise ValueError("APP_DEBUG must be false in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.production

    @property
    def is_development(self) -> bool:
        return self.app_env == Environment.development

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://docna:docna@localhost:5432/docna"
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_pool_recycle: int = 3600
    database_echo: bool = False

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "")

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600

    # ── Celery ───────────────────────────────────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── JWT ───────────────────────────────────────────────────────────────────
    jwt_secret_key: str = "change-this-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30

    # ── Storage ───────────────────────────────────────────────────────────────
    storage_provider: StorageProvider = StorageProvider.minio
    aws_access_key_id: str = "minioadmin"
    aws_secret_access_key: str = "minioadmin"
    aws_default_region: str = "us-east-1"
    s3_bucket_name: str = "docna-documents"
    s3_endpoint_url: str | None = "http://localhost:9000"

    # ── LLM ───────────────────────────────────────────────────────────────────
    llm_provider: LLMProvider = LLMProvider.openai
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536
    openai_chat_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_chat_model: str = "claude-sonnet-4-6"

    # ── Billing ───────────────────────────────────────────────────────────────
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""
    stripe_enterprise_price_id: str = ""

    # ── Observability ─────────────────────────────────────────────────────────
    sentry_dsn: str = ""
    otel_exporter_otlp_endpoint: str = ""
    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.console
    metrics_auth_token: str = ""   # set to protect /metrics; leave empty to disable in prod

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    rate_limit_enabled: bool = True
    rate_limit_anonymous_rpm: int = 10
    rate_limit_free_rpm: int = 60
    rate_limit_pro_rpm: int = 300
    # Number of trusted reverse proxies in front of the app. X-Forwarded-For is
    # only honored when set > 0, and then the client IP is taken this many hops
    # from the right (the entries a trusted proxy appends can't be spoofed by the
    # client). 0 = ignore X-Forwarded-For entirely and use the direct peer.
    trusted_proxy_count: int = 0

    # ── Plans ─────────────────────────────────────────────────────────────────
    plan_free_documents: int = 10
    plan_free_queries_per_month: int = 100
    plan_free_storage_bytes: int = 52_428_800       # 50 MB
    plan_pro_documents: int = -1                     # -1 = unlimited
    plan_pro_queries_per_month: int = 2_000
    plan_pro_storage_bytes: int = 10_737_418_240     # 10 GB

    # ── RAG ── core ──────────────────────────────────────────────────────────
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 64
    rag_top_k: int = 6                               # final chunks returned
    rag_pre_rerank_top_k: int = 20                   # candidates before reranking
    rag_similarity_threshold: float = 0.35

    # ── RAG ── embedder ───────────────────────────────────────────────────────
    rag_embedder: EmbedderType = EmbedderType.openai
    rag_embedding_dimensions: int = 1536             # must match embedding model output
    voyage_api_key: str = ""
    voyage_embedding_model: str = "voyage-3"
    bge_model_name: str = "BAAI/bge-large-en-v1.5"
    bge_device: str = "cpu"

    # ── RAG ── chunker ────────────────────────────────────────────────────────
    rag_chunker: ChunkerType = ChunkerType.hybrid
    rag_semantic_threshold: float = 0.92

    # ── RAG ── retriever ──────────────────────────────────────────────────────
    rag_retriever: RetrieverType = RetrieverType.hybrid

    # ── RAG ── reranker ───────────────────────────────────────────────────────
    rag_rerank_enabled: bool = True
    rag_rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ── RAG ── vector store ───────────────────────────────────────────────────
    rag_vector_store: VectorStoreType = VectorStoreType.pgvector
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "docna_chunks"

    # ── Anonymous sessions ────────────────────────────────────────────────────
    anon_session_max_queries: int = 5
    anon_session_ttl_days: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
