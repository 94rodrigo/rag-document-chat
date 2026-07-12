"""
Local filesystem storage backend — development only.
Set STORAGE_PROVIDER=local in .env to use this instead of S3/MinIO.
Files are stored under LOCAL_STORAGE_PATH (default: ./storage/).
"""
from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import BinaryIO

import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()


class LocalStorageService:
    def __init__(self, root: str | None = None) -> None:
        self._root = Path(root or os.getenv("LOCAL_STORAGE_PATH", "./storage")).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        log.info("local_storage.init", root=str(self._root))

    def _path(self, key: str) -> Path:
        # Prevent path traversal
        safe = Path(key).parts
        return self._root.joinpath(*safe)

    async def ensure_bucket(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)

    async def upload(
        self,
        key: str,
        data: BinaryIO | bytes,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            dest.write_bytes(data)
        else:
            dest.write_bytes(data.read())
        log.info("local_storage.upload_ok", key=key)
        return key

    async def download(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            from app.shared.exceptions import StorageUnavailableError
            raise StorageUnavailableError(f"File not found: {key}")
        return path.read_bytes()

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()
            # Clean up empty parent directories
            with contextlib.suppress(OSError):
                path.parent.rmdir()
        log.info("local_storage.delete_ok", key=key)

    async def generate_presigned_url(self, key: str, expiry_seconds: int = 3600) -> str:
        # Serve via the API's file download endpoint instead
        return f"/api/v1/documents/{key}/file"

    async def get_object_size(self, key: str) -> int:
        path = self._path(key)
        return path.stat().st_size if path.exists() else 0
