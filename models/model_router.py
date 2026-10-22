"""Router de modelo: Ollama local por defecto, OpenAI/Gemini en modo auto.

Expone exactamente la misma interfaz que OpenAIModel y GeminiModel, por lo que
puede reemplazarlos como dependencia en cualquier lugar del proyecto.
"""
from __future__ import annotations

from typing import Any, AsyncIterator, Optional, Type, TypeVar

from pydantic import BaseModel

from config.settings import settings
from core.logger import log
from models.gemini_model import GeminiModel, gemini_model
from models.openai_model import OpenAIModel, openai_model
from models.ollama_model import ollama_model

T = TypeVar("T", bound=BaseModel)


class ModelRouter:
    """Enruta peticiones a Ollama o a proveedores externos según AI_PROVIDER.

    Lógica de selección:
    En modo ollama no se llama a proveedores externos ni se generan embeddings
    para Supabase. Se conserva el contexto conversacional en memoria.
    En modo auto:
    1. Si OpenAI API key no está configurada (pero sí la de Gemini), usa Gemini
       desde el inicio.
    2. Si OpenAI falla en tiempo de ejecución (error de red, cuota, etc.) cae a
       Gemini.
    3. Los embeddings usan siempre OpenAI, sin fallback: la tabla `memories` de
       Supabase tiene una columna `vector(1536)` fija (dimensión de
       `text-embedding-3-small`) y los embeddings de Gemini no son compatibles
       con ese índice.
    """

    def __init__(
        self,
        primary: OpenAIModel | None = None,
        fallback: GeminiModel | None = None,
    ) -> None:
        self._primary = primary or openai_model
        self._fallback = fallback or gemini_model
        self._local = ollama_model if settings.ai_provider == "ollama" and primary is None and fallback is None else None
        self._prefer_fallback = not bool(settings.openai_api_key) and bool(settings.gemini_api_key)
        if self._local:
            log.info("IA local: Ollama ({})", settings.ollama_model)
        elif not settings.openai_api_key and not settings.gemini_api_key:
            log.warning("Ni OPENAI_API_KEY ni GEMINI_API_KEY configuradas — las funciones de IA fallarán.")
        elif self._prefer_fallback:
            log.warning("OPENAI_API_KEY no configurada — usando Gemini como modelo principal.")

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
        if self._local:
            return await self._local.chat_completion(messages, tools, response_format, temperature, max_tokens)
        if self._prefer_fallback:
            return await self._fallback.chat_completion(
                messages, temperature=temperature, max_tokens=max_tokens
            )
        try:
            return await self._primary.chat_completion(
                messages,
                tools=tools,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("OpenAI falló ({}), usando Gemini como fallback.", type(exc).__name__)
            return await self._fallback.chat_completion(
                messages, temperature=temperature, max_tokens=max_tokens
            )

    async def simple_chat(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
    ) -> str:
        if self._local:
            return await self._local.simple_chat(prompt, system, temperature)
        if self._prefer_fallback:
            return await self._fallback.simple_chat(prompt, system=system, temperature=temperature)
        try:
            return await self._primary.simple_chat(prompt, system=system, temperature=temperature)
        except Exception as exc:  # noqa: BLE001
            log.warning("OpenAI simple_chat falló ({}), usando Gemini.", type(exc).__name__)
            return await self._fallback.simple_chat(prompt, system=system, temperature=temperature)

    # ------------------------------------------------------------------ #
    # Structured outputs (Pydantic)
    # ------------------------------------------------------------------ #
    async def structured_output(
        self,
        messages: list[dict[str, Any]],
        schema: Type[T],
        temperature: float | None = None,
    ) -> T:
        if self._local:
            return await self._local.structured_output(messages, schema, temperature)
        if self._prefer_fallback:
            return await self._fallback.structured_output(messages, schema, temperature)
        try:
            return await self._primary.structured_output(messages, schema, temperature)
        except Exception as exc:  # noqa: BLE001
            log.warning("OpenAI structured_output falló ({}), usando Gemini.", type(exc).__name__)
            return await self._fallback.structured_output(messages, schema, temperature)

    # ------------------------------------------------------------------ #
    # Embeddings (solo OpenAI, sin fallback — ver docstring de la clase)
    # ------------------------------------------------------------------ #
    async def embeddings(self, text: str | list[str]) -> list[list[float]]:
        if self._local:
            # No mezclar espacios vectoriales con la tabla OpenAI vector(1536).
            # La memoria semántica queda desactivada; el historial de sesión sigue activo.
            return [[] for _ in ([text] if isinstance(text, str) else text)]
        return await self._primary.embeddings(text)

    async def embedding(self, text: str) -> list[float]:
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
        if self._local:
            async for token in self._local.stream_chat(messages, temperature):
                yield token
            return
        if self._prefer_fallback:
            async for token in self._fallback.stream_chat(messages, temperature):
                yield token
            return
        try:
            async for token in self._primary.stream_chat(messages, temperature):
                yield token
        except Exception as exc:  # noqa: BLE001
            log.warning("OpenAI stream_chat falló ({}), usando Gemini como fallback.", type(exc).__name__)
            async for token in self._fallback.stream_chat(messages, temperature):
                yield token


# Instancia reutilizable (sustituye a openai_model en la mayor parte del proyecto).
model_router = ModelRouter()
