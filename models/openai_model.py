"""Wrapper asíncrono completo sobre la API de OpenAI.

Expone chat, structured outputs, embeddings y streaming con manejo de errores.
"""
from __future__ import annotations

from typing import Any, AsyncIterator, Optional, Type, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from config.settings import settings
from core.logger import log

T = TypeVar("T", bound=BaseModel)


class OpenAIModel:
    """Cliente de alto nivel para los modelos de OpenAI."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.model = model or settings.model_name
        self.embedding_model = settings.embedding_model
        self._api_key = api_key or settings.openai_api_key
        self.__client: AsyncOpenAI | None = None

    @property
    def _client(self) -> AsyncOpenAI:
        if self.__client is None:
            if not self._api_key:
                raise RuntimeError("OPENAI_API_KEY no configurada")
            self.__client = AsyncOpenAI(api_key=self._api_key)
        return self.__client

    # ------------------------------------------------------------------ #
    # Chat estándar
    # ------------------------------------------------------------------ #
    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        response_format: Optional[dict[str, Any]] = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        """Realiza una llamada de chat. Devuelve el `message` de la respuesta.

        Si se pasan `tools`, el mensaje puede contener `tool_calls`.
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.temperature,
            "max_tokens": max_tokens or settings.max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = await self._client.chat.completions.create(**kwargs)
            return response.choices[0].message
        except Exception as exc:  # noqa: BLE001
            log.error("Error en chat_completion de OpenAI: {}", exc)
            raise

    async def simple_chat(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """Atajo: envía un prompt simple y devuelve el texto de respuesta."""
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        message = await self.chat_completion(messages, temperature=temperature)
        return message.content or ""

    # ------------------------------------------------------------------ #
    # Structured outputs (Pydantic)
    # ------------------------------------------------------------------ #
    async def structured_output(
        self,
        messages: list[dict[str, Any]],
        schema: Type[T],
        temperature: float | None = None,
    ) -> T:
        """Devuelve una instancia validada del modelo Pydantic `schema`.

        Usa la API `parse` de structured outputs de OpenAI.
        """
        try:
            response = await self._client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=schema,
                temperature=temperature if temperature is not None else 0.2,
            )
            parsed = response.choices[0].message.parsed
            if parsed is None:
                raise ValueError("La respuesta estructurada vino vacía.")
            return parsed
        except Exception as exc:  # noqa: BLE001
            log.error("Error en structured_output: {}", exc)
            raise

    # ------------------------------------------------------------------ #
    # Embeddings
    # ------------------------------------------------------------------ #
    async def embeddings(self, text: str | list[str]) -> list[list[float]]:
        """Genera embeddings para uno o varios textos."""
        inputs = [text] if isinstance(text, str) else text
        try:
            response = await self._client.embeddings.create(
                model=self.embedding_model,
                input=inputs,
            )
            return [item.embedding for item in response.data]
        except Exception as exc:  # noqa: BLE001
            log.error("Error generando embeddings: {}", exc)
            raise

    async def embedding(self, text: str) -> list[float]:
        """Genera un único embedding."""
        result = await self.embeddings(text)
        return result[0]

    # ------------------------------------------------------------------ #
    # Streaming
    # ------------------------------------------------------------------ #
    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """Genera la respuesta token a token (async generator)."""
        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else settings.temperature,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except Exception as exc:  # noqa: BLE001
            log.error("Error en stream_chat: {}", exc)
            raise


# Instancia reutilizable.
openai_model = OpenAIModel()
