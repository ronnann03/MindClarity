"""Fixtures compartidos para toda la suite de tests de YU."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


# --------------------------------------------------------------------------- #
# Configuración de asyncio para pytest-asyncio
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


# --------------------------------------------------------------------------- #
# Stub del modelo de IA (evita llamadas reales a OpenAI/Gemini en tests)
# --------------------------------------------------------------------------- #
class FakeModel:
    """Modelo falso con la misma interfaz que OpenAIModel/GeminiModel/ModelRouter."""

    def __init__(self, default_reply: str = "respuesta simulada") -> None:
        self.default_reply = default_reply
        # Rastrear llamadas
        self.calls: list[dict[str, Any]] = []

    async def chat_completion(self, messages, **kwargs) -> Any:
        self.calls.append({"method": "chat_completion", "messages": messages})
        return MagicMock(content=self.default_reply, tool_calls=None)

    async def simple_chat(self, prompt, system=None, **kwargs) -> str:
        self.calls.append({"method": "simple_chat", "prompt": prompt})
        return self.default_reply

    async def structured_output(self, messages, schema, temperature=None):
        self.calls.append({"method": "structured_output", "schema": schema.__name__})
        # Devuelve instancia con valores por defecto del schema
        return schema.model_construct()

    async def embeddings(self, text) -> list[list[float]]:
        inputs = [text] if isinstance(text, str) else text
        return [[0.1] * 10 for _ in inputs]  # vector corto para tests

    async def embedding(self, text) -> list[float]:
        return [0.1] * 10


@pytest.fixture
def fake_model() -> FakeModel:
    return FakeModel()


# --------------------------------------------------------------------------- #
# Directorio temporal para archivos de test
# --------------------------------------------------------------------------- #
@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Subdirectorio temporal limpio para cada test."""
    d = tmp_path / "yu_test"
    d.mkdir()
    return d


# --------------------------------------------------------------------------- #
# Stub de MemoryManager (sin Supabase)
# --------------------------------------------------------------------------- #
@pytest.fixture
def fake_memory():
    mem = MagicMock()
    mem.preferences = {}
    mem.context = MagicMock()
    mem.context.build_messages = MagicMock(return_value=[])
    mem.recall = AsyncMock(return_value=[])
    mem.save_interaction = AsyncMock()
    mem.initialize = AsyncMock()
    return mem
