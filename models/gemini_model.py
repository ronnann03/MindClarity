"""Wrapper asíncrono sobre la API de Google Gemini.

Expone exactamente la misma interfaz pública que `OpenAIModel`
(`models/openai_model.py`), por lo que `ModelRouter` puede usarlo como
fallback sin tocar el resto del proyecto.

Nota sobre embeddings: la tabla `memories` de Supabase usa `vector(1536)`
(dimensión fija de `text-embedding-3-small`, ver `database/schemas/schema.sql`).
Los modelos de embeddings de Gemini devuelven otra dimensión, así que
`ModelRouter` NO usa este `embeddings()` como fallback de OpenAI — se deja
implementado aquí solo por paridad de interfaz, para quien quiera usarlo
directamente fuera del router.
"""
from __future__ import annotations

from typing import Any, AsyncIterator, Optional, Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from config.settings import settings
from core.logger import log

T = TypeVar("T", bound=BaseModel)

# Gemini usa "model" en vez de "assistant" para el rol del propio modelo.
_ROLE_MAP = {"assistant": "model", "user": "user"}


def _split_system(messages: list[dict[str, Any]]) -> tuple[str | None, list[dict[str, Any]]]:
    """Separa los mensajes `system` (Gemini los pasa aparte) del resto."""
    system_parts: list[str] = []
    rest: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("role") == "system":
            system_parts.append(str(msg.get("content", "")))
        else:
            rest.append(msg)
    system_instruction = "\n".join(system_parts) if system_parts else None
    return system_instruction, rest


def _to_contents(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "role": _ROLE_MAP.get(msg.get("role", "user"), "user"),
            "parts": [{"text": str(msg.get("content", ""))}],
        }
        for msg in messages
    ]


class GeminiModel:
    """Cliente de alto nivel para los modelos de Google Gemini."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.model = model or settings.gemini_model_name
        self._api_key = api_key or settings.gemini_api_key
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        """Crea el cliente de forma perezosa (falla recién al usarlo, no al importar
        el módulo, para no romper el arranque si GEMINI_API_KEY aún no está configurada).
        """
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

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
        """Realiza una llamada de chat. Devuelve un objeto con atributo `content`."""
        system_instruction, rest = _split_system(messages)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature if temperature is not None else settings.temperature,
            max_output_tokens=max_tokens or settings.max_tokens,
        )
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=_to_contents(rest),
                config=config,
            )
            return type("Message", (), {"content": response.text or "", "tool_calls": None})()
        except Exception as exc:  # noqa: BLE001
            log.error("Error en chat_completion de Gemini: {}", exc)
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
        """Devuelve una instancia validada del modelo Pydantic `schema`."""
        system_instruction, rest = _split_system(messages)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature if temperature is not None else 0.2,
            response_mime_type="application/json",
            response_schema=schema,
        )
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=_to_contents(rest),
                config=config,
            )
            if not response.text:
                raise ValueError("La respuesta estructurada de Gemini vino vacía.")
            return schema.model_validate_json(response.text)
        except Exception as exc:  # noqa: BLE001
            log.error("Error en structured_output de Gemini: {}", exc)
            raise

    # ------------------------------------------------------------------ #
    # Embeddings (no usado por ModelRouter, ver docstring del módulo)
    # ------------------------------------------------------------------ #
    async def embeddings(self, text: str | list[str]) -> list[list[float]]:
        inputs = [text] if isinstance(text, str) else text
        try:
            response = await self.client.aio.models.embed_content(
                model="gemini-embedding-001",
                contents=inputs,
            )
            return [item.values for item in response.embeddings]
        except Exception as exc:  # noqa: BLE001
            log.error("Error generando embeddings de Gemini: {}", exc)
            raise

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
        """Genera la respuesta token a token (async generator)."""
        system_instruction, rest = _split_system(messages)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature if temperature is not None else settings.temperature,
        )
        try:
            stream = await self.client.aio.models.generate_content_stream(
                model=self.model,
                contents=_to_contents(rest),
                config=config,
            )
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:  # noqa: BLE001
            log.error("Error en stream_chat de Gemini: {}", exc)
            raise


# Instancia reutilizable.
gemini_model = GeminiModel()
