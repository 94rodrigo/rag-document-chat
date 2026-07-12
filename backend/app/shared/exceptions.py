from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application exception."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: str | None = None,
        *,
        detail: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.detail = detail
        self.headers = headers
        super().__init__(self.message)


# ── 400 Bad Request ───────────────────────────────────────────────────────────

class ValidationError(AppError):
    status_code = 400
    error_code = "VALIDATION_ERROR"
    message = "Invalid input"


class FileTooLargeError(AppError):
    status_code = 400
    error_code = "FILE_TOO_LARGE"
    message = "File exceeds the allowed size limit"


class UnsupportedFileTypeError(AppError):
    status_code = 400
    error_code = "UNSUPPORTED_FILE_TYPE"
    message = "File type is not supported"


# ── 401 Unauthorized ──────────────────────────────────────────────────────────

class AuthenticationError(AppError):
    status_code = 401
    error_code = "AUTHENTICATION_ERROR"
    message = "Authentication required"


class InvalidTokenError(AppError):
    status_code = 401
    error_code = "INVALID_TOKEN"
    message = "Token is invalid or expired"


class InvalidCredentialsError(AppError):
    status_code = 401
    error_code = "INVALID_CREDENTIALS"
    message = "Invalid email or password"


# ── 403 Forbidden ─────────────────────────────────────────────────────────────

class PermissionDeniedError(AppError):
    status_code = 403
    error_code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action"


# ── 404 Not Found ─────────────────────────────────────────────────────────────

class NotFoundError(AppError):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"


class DocumentNotFoundError(NotFoundError):
    error_code = "DOCUMENT_NOT_FOUND"
    message = "Document not found"


class ConversationNotFoundError(NotFoundError):
    error_code = "CONVERSATION_NOT_FOUND"
    message = "Conversation not found"


# ── 409 Conflict ──────────────────────────────────────────────────────────────

class ConflictError(AppError):
    status_code = 409
    error_code = "CONFLICT"
    message = "Resource already exists"


class EmailAlreadyRegisteredError(ConflictError):
    error_code = "EMAIL_REGISTERED"
    message = "An account with this email already exists"


# ── 422 Unprocessable ─────────────────────────────────────────────────────────

class DocumentProcessingError(AppError):
    status_code = 422
    error_code = "DOCUMENT_PROCESSING_ERROR"
    message = "Document could not be processed"


# ── 429 Rate Limited ──────────────────────────────────────────────────────────

class RateLimitExceededError(AppError):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests. Please slow down."


class UsageLimitExceededError(AppError):
    status_code = 429
    error_code = "USAGE_LIMIT_EXCEEDED"
    message = "You have reached your plan's usage limit"


class DocumentLimitExceededError(UsageLimitExceededError):
    error_code = "DOCUMENT_LIMIT_EXCEEDED"
    message = "Document limit reached. Upgrade to add more."


class QueryLimitExceededError(UsageLimitExceededError):
    error_code = "QUERY_LIMIT_EXCEEDED"
    message = "Monthly query limit reached. Upgrade for more."


class StorageLimitExceededError(UsageLimitExceededError):
    error_code = "STORAGE_LIMIT_EXCEEDED"
    message = "Storage limit reached. Delete documents or upgrade."


# ── 503 Service Unavailable ───────────────────────────────────────────────────

class LLMUnavailableError(AppError):
    status_code = 503
    error_code = "LLM_UNAVAILABLE"
    message = "AI service is temporarily unavailable"


class StorageUnavailableError(AppError):
    status_code = 503
    error_code = "STORAGE_UNAVAILABLE"
    message = "Storage service is temporarily unavailable"
