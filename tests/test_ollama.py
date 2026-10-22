"""Pruebas sin red: contrato de Ollama y aislamiento de proveedores pagos."""
import json
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import BaseModel, ValidationError

from config.settings import settings
from models.ollama_model import OllamaModel
from models.model_router import ModelRouter


class Payload(BaseModel):
    action: str
    entities: dict


@pytest.mark.asyncio
async def test_structured_output_accepts_open_entities_and_validates():
    def handler(request):
        body = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert body["format"]["properties"]["entities"]["type"] == "object"
        assert body["options"]["temperature"] == 0
        return httpx.Response(200, json={"message": {
            "content": '{"action":"set_volume","entities":{"level":30}}'}})
    model = OllamaModel(transport=httpx.MockTransport(handler))
    result = await model.structured_output([{"role": "user", "content": "Volumen 30"}], Payload)
    assert result.entities == {"level": 30}


@pytest.mark.asyncio
async def test_invalid_structured_output_is_rejected():
    transport = httpx.MockTransport(lambda _: httpx.Response(
        200, json={"message": {"content": '{"entities":{}}'}}))
    with pytest.raises(ValidationError):
        await OllamaModel(transport=transport).structured_output([], Payload)


@pytest.mark.asyncio
async def test_stream_preserves_chunks():
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=(
        '{"message":{"content":"Hola "},"done":false}\n'
        '{"message":{"content":"señor"},"done":false}\n'
        '{"message":{"content":""},"done":true}\n').encode()))
    chunks = [part async for part in OllamaModel(transport=transport).stream_chat([])]
    assert chunks == ["Hola ", "señor"]


@pytest.mark.asyncio
async def test_local_failure_never_calls_cloud(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "ollama")
    router = ModelRouter()
    local = AsyncMock()
    local.chat_completion.side_effect = httpx.ConnectError("offline")
    router._local = local
    router._primary = AsyncMock()
    router._fallback = AsyncMock()
    with pytest.raises(httpx.ConnectError):
        await router.chat_completion([])
    router._primary.chat_completion.assert_not_called()
    router._fallback.chat_completion.assert_not_called()
    assert await router.embeddings(["uno", "dos"]) == [[], []]
    router._primary.embeddings.assert_not_called()


@pytest.mark.asyncio
async def test_missing_model_http_error_is_propagated():
    transport = httpx.MockTransport(lambda _: httpx.Response(404, json={"error": "model not found"}))
    with pytest.raises(httpx.HTTPStatusError):
        await OllamaModel(transport=transport).simple_chat("Hola")


@pytest.mark.asyncio
async def test_local_memory_keeps_history_without_requesting_embeddings(monkeypatch):
    from memory.memory_manager import MemoryManager

    monkeypatch.setattr(settings, "ai_provider", "ollama")
    vector = AsyncMock()
    memory = MemoryManager(vector=vector)
    await memory.save_interaction("Mi color favorito es azul", "Lo recordaré en esta sesión")
    assert await memory.recall("¿Qué color me gusta?") == []
    assert memory.context.build_messages()[-2]["content"] == "Mi color favorito es azul"
    vector.remember.assert_not_called()
    vector.search_similar.assert_not_called()
