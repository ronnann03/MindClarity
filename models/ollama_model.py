"""Proveedor local de YU: chat, JSON validado y streaming sin claves de API."""
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, AsyncIterator, TypeVar

import httpx
from pydantic import BaseModel

from config.settings import settings

T = TypeVar("T", bound=BaseModel)


class OllamaModel:
    def __init__(self, base_url: str | None = None, model: str | None = None,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.transport = transport

    def _client(self) -> httpx.AsyncClient:
        # Un cliente por petición evita compartir conexiones entre los loops de voz y web.
        return httpx.AsyncClient(base_url=self.base_url, timeout=settings.ollama_timeout,
                                 transport=self.transport, trust_env=False)

    def _payload(self, messages: list[dict[str, Any]], temperature: float | None,
                 max_tokens: int | None = None) -> dict[str, Any]:
        return {"model": self.model, "messages": messages, "stream": False,
                "keep_alive": "30m", "options": {
                    "temperature": settings.temperature if temperature is None else temperature,
                    "num_predict": max_tokens or settings.max_tokens, "num_ctx": 8192}}

    async def chat_completion(self, messages: list[dict[str, Any]], tools=None,
                              response_format=None, temperature=None, max_tokens=None) -> Any:
        payload = self._payload(messages, temperature, max_tokens)
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["format"] = (response_format["json_schema"]["schema"]
                                 if response_format.get("type") == "json_schema" else "json")
        async with self._client() as client:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            message = response.json()["message"]
        return SimpleNamespace(content=message.get("content", ""),
                               tool_calls=message.get("tool_calls"))

    async def simple_chat(self, prompt: str, system: str | None = None,
                          temperature: float | None = None) -> str:
        messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": prompt})
        return (await self.chat_completion(messages, temperature=temperature)).content

    async def structured_output(self, messages: list[dict[str, Any]], schema: type[T],
                                 temperature: float | None = None) -> T:
        json_schema = schema.model_json_schema()
        grounded = [*messages, {"role": "system", "content":
                    "Devuelve solo JSON conforme a este esquema: " + json.dumps(json_schema)}]
        message = await self.chat_completion(
            grounded, response_format={"type": "json_schema", "json_schema": {"schema": json_schema}},
            temperature=0 if temperature is None else temperature)
        return schema.model_validate_json(message.content)

    async def stream_chat(self, messages: list[dict[str, Any]],
                          temperature: float | None = None) -> AsyncIterator[str]:
        payload = self._payload(messages, temperature)
        payload["stream"] = True
        async with self._client() as client:
            async with client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    if chunk.get("error"):
                        raise RuntimeError(chunk["error"])
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content


ollama_model = OllamaModel()
