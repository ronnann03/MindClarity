"""Gestor de contexto conversacional con resumen automático."""
from __future__ import annotations

from collections import deque
from typing import Any

from config.settings import settings
from core.logger import log
from models.openai_model import OpenAIModel, openai_model


def estimate_tokens(text: str) -> int:
    """Estimación aproximada de tokens (1 token ~ 4 caracteres)."""
    return max(1, len(text) // 4)


def _default_model() -> OpenAIModel:  # type: ignore[return]
    try:
        from models.model_router import model_router  # noqa: PLC0415
        return model_router  # type: ignore[return-value]
    except Exception:
        return openai_model


class ContextManager:
    """Mantiene la ventana de conversación y la resume si crece demasiado."""

    def __init__(self, model: OpenAIModel | None = None) -> None:
        self.model = model or _default_model()
        self.history: deque[dict[str, str]] = deque()
        self.summary: str = ""
        self.max_tokens = settings.max_context_tokens

    def add_turn(self, role: str, content: str) -> None:
        """Añade un turno de conversación al historial."""
        self.history.append({"role": role, "content": content})

    def _current_tokens(self) -> int:
        total = estimate_tokens(self.summary)
        for turn in self.history:
            total += estimate_tokens(turn["content"])
        return total

    async def maybe_summarize(self) -> None:
        """Si se supera el límite de tokens, resume los turnos antiguos."""
        if self._current_tokens() <= self.max_tokens:
            return
        if len(self.history) <= 4:
            return

        # Resume todo menos los 4 últimos turnos.
        to_summarize = []
        while len(self.history) > 4:
            to_summarize.append(self.history.popleft())

        convo = "\n".join(f"{t['role']}: {t['content']}" for t in to_summarize)
        prompt = (
            "Resume de forma concisa la siguiente parte de una conversación, "
            "conservando hechos, decisiones y preferencias importantes:\n\n" + convo
        )
        try:
            new_summary = await self.model.simple_chat(prompt)
            self.summary = (self.summary + "\n" + new_summary).strip()
            log.debug("Contexto resumido. Nuevo tamaño resumen: {} tokens.",
                      estimate_tokens(self.summary))
        except Exception as exc:  # noqa: BLE001
            log.error("Error al resumir contexto: {}", exc)

    def build_messages(self, relevant_memories: str = "") -> list[dict[str, str]]:
        """Construye la lista de mensajes para el LLM."""
        messages: list[dict[str, str]] = []
        if self.summary:
            messages.append({"role": "system", "content": f"Resumen previo:\n{self.summary}"})
        if relevant_memories:
            messages.append({
                "role": "system",
                "content": f"Memorias relevantes:\n{relevant_memories}",
            })
        messages.extend(list(self.history))
        return messages

    def context_text(self) -> str:
        """Devuelve el contexto actual como texto plano."""
        parts: list[str] = []
        if self.summary:
            parts.append(f"Resumen: {self.summary}")
        for turn in self.history:
            parts.append(f"{turn['role']}: {turn['content']}")
        return "\n".join(parts)

    def clear(self) -> None:
        self.history.clear()
        self.summary = ""
