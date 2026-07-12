from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import LLMProvider, get_settings
from app.shared.exceptions import LLMUnavailableError

log = structlog.get_logger(__name__)
settings = get_settings()


# ── Abstract interfaces ───────────────────────────────────────────────────────

class EmbedderProtocol(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class ChatProtocol(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str: ...

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]: ...


# ── OpenAI implementations ────────────────────────────────────────────────────

class OpenAIEmbedder(EmbedderProtocol):
    def __init__(self) -> None:
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_embedding_model
        self._dims = settings.openai_embedding_dimensions

    async def embed(self, text: str) -> list[float]:
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(min=1, max=8),
                retry=retry_if_exception_type(Exception),
            ):
                with attempt:
                    resp = await self._client.embeddings.create(
                        model=self._model,
                        input=texts,
                        dimensions=self._dims,
                    )
                    return [d.embedding for d in resp.data]
        except Exception as e:
            log.exception("openai.embed_failed")
            raise LLMUnavailableError(str(e)) from e
        return []  # unreachable


class OpenAIChat(ChatProtocol):
    def __init__(self) -> None:
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_chat_model

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            log.exception("openai.complete_failed")
            raise LLMUnavailableError(str(e)) from e

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        try:
            async with await self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            ) as stream:
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
        except Exception as e:
            log.exception("openai.stream_failed")
            raise LLMUnavailableError(str(e)) from e


# ── Anthropic implementations ─────────────────────────────────────────────────

class AnthropicChat(ChatProtocol):
    def __init__(self) -> None:
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_chat_model

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        system, msgs = self._split_messages(messages)
        try:
            resp = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=msgs,
            )
            return resp.content[0].text  # type: ignore[union-attr]
        except Exception as e:
            raise LLMUnavailableError(str(e)) from e

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        system, msgs = self._split_messages(messages)
        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=msgs,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise LLMUnavailableError(str(e)) from e

    @staticmethod
    def _split_messages(
        messages: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, str]]]:
        system = ""
        rest: list[dict[str, str]] = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                rest.append(m)
        return system, rest


# ── Factory ───────────────────────────────────────────────────────────────────

_embedder: EmbedderProtocol | None = None
_chat: ChatProtocol | None = None


def get_embedder() -> EmbedderProtocol:
    global _embedder
    if _embedder is None:
        _embedder = OpenAIEmbedder()
    return _embedder


def get_chat() -> ChatProtocol:
    global _chat
    if _chat is None:
        _chat = (
            AnthropicChat()
            if settings.llm_provider == LLMProvider.anthropic
            else OpenAIChat()
        )
    return _chat
