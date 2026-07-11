from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_from_ts(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=UTC)


def generate_id() -> str:
    """Generate a URL-safe UUID4 string."""
    return str(uuid.uuid4())


def generate_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Hash a token for secure storage using HMAC-SHA256 with the app secret key."""
    from app.config import get_settings
    secret = get_settings().secret_key.encode()
    return hmac.new(secret, token.encode(), hashlib.sha256).hexdigest()


def build_s3_key(user_id: str, document_id: str, filename: str) -> str:
    """Build a deterministic S3 object key."""
    return f"users/{user_id}/documents/{document_id}/{filename}"


def safe_filename(name: str) -> str:
    """Sanitize a filename — strips control chars, limits path traversal."""
    import re
    # Strip control chars (including \r\n that enable header injection)
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    # Only allow word chars, hyphens, dots, and spaces
    name = re.sub(r"[^\w\s\-.]", "", name)
    # Prevent double-dot path traversal
    name = re.sub(r"\.{2,}", ".", name)
    return name.strip()[:200] or "document"


def chunk_list(lst: list[Any], size: int) -> list[list[Any]]:
    """Split a list into chunks of the given size."""
    return [lst[i : i + size] for i in range(0, len(lst), size)]
