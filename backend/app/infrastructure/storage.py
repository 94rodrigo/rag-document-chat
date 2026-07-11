from __future__ import annotations

import mimetypes
from typing import BinaryIO

import aioboto3
import structlog
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import get_settings
from app.shared.exceptions import StorageUnavailableError

log = structlog.get_logger(__name__)
settings = get_settings()


class StorageService:
    """Async S3/MinIO storage abstraction."""

    def __init__(self) -> None:
        self._session = aioboto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_default_region,
        )
        self._endpoint = settings.s3_endpoint_url
        self._bucket = settings.s3_bucket_name
        self._config = Config(signature_version="s3v4")

    def _client(self):
        kwargs: dict = {"config": self._config}
        if self._endpoint:
            kwargs["endpoint_url"] = self._endpoint
        return self._session.client("s3", **kwargs)

    async def ensure_bucket(self) -> None:
        async with self._client() as s3:
            try:
                await s3.head_bucket(Bucket=self._bucket)
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    await s3.create_bucket(Bucket=self._bucket)
                    log.info("storage.bucket_created", bucket=self._bucket)
                else:
                    raise StorageUnavailableError(str(e)) from e

    async def upload(
        self,
        key: str,
        data: BinaryIO | bytes,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str:
        if content_type is None:
            content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
        extra: dict = {"ContentType": content_type}
        if metadata:
            extra["Metadata"] = metadata

        try:
            async with self._client() as s3:
                if isinstance(data, bytes):
                    import io
                    data = io.BytesIO(data)
                await s3.upload_fileobj(data, self._bucket, key, ExtraArgs=extra)
            log.info("storage.upload_ok", key=key)
            return key
        except ClientError as e:
            log.exception("storage.upload_failed", key=key)
            raise StorageUnavailableError(str(e)) from e

    async def download(self, key: str) -> bytes:
        import io
        buf = io.BytesIO()
        try:
            async with self._client() as s3:
                await s3.download_fileobj(self._bucket, key, buf)
            buf.seek(0)
            return buf.read()
        except ClientError as e:
            log.exception("storage.download_failed", key=key)
            raise StorageUnavailableError(str(e)) from e

    async def delete(self, key: str) -> None:
        try:
            async with self._client() as s3:
                await s3.delete_object(Bucket=self._bucket, Key=key)
            log.info("storage.delete_ok", key=key)
        except ClientError as e:
            log.exception("storage.delete_failed", key=key)
            raise StorageUnavailableError(str(e)) from e

    async def generate_presigned_url(
        self,
        key: str,
        expiry_seconds: int = 3600,
    ) -> str:
        try:
            async with self._client() as s3:
                url = await s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self._bucket, "Key": key},
                    ExpiresIn=expiry_seconds,
                )
            return url
        except ClientError as e:
            raise StorageUnavailableError(str(e)) from e

    async def get_object_size(self, key: str) -> int:
        try:
            async with self._client() as s3:
                resp = await s3.head_object(Bucket=self._bucket, Key=key)
            return resp["ContentLength"]
        except ClientError as e:
            raise StorageUnavailableError(str(e)) from e


_storage: StorageService | None = None


def get_storage() -> StorageService:
    global _storage
    if _storage is None:
        from app.config import StorageProvider
        if settings.storage_provider == StorageProvider.local:
            from app.infrastructure.storage_local import LocalStorageService
            _storage = LocalStorageService()  # type: ignore[assignment]
        else:
            _storage = StorageService()
    return _storage
