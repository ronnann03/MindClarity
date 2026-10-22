"""Coordinador de memoria: short-term, long-term (Supabase) y semántica."""
from __future__ import annotations

import asyncio
from typing import Any

from config.settings import settings
from core.logger import log
from database.repositories.conversation_repo import (
    ConversationRepository,
    conversation_repo,
)
from database.supabase_client import supabase_client
from memory.context_manager import ContextManager
from memory.vector_memory import VectorMemory, vector_memory


class MemoryManager:
    """Orquesta los tres niveles de memoria de YU."""

    def __init__(
        self,
        context: ContextManager | None = None,
        vector: VectorMemory | None = None,
        conv_repo: ConversationRepository | None = None,
    ) -> None:
        self.context = context or ContextManager()
        self.vector = vector or vector_memory
        self.conv_repo = conv_repo or conversation_repo
        self.short_term: list[dict[str, Any]] = []
        self.conversation_id: str | None = None
        self.preferences: dict[str, Any] = {}

    async def initialize(self) -> None:
        """Crea una conversación nueva y carga preferencias."""
        try:
            row = await asyncio.to_thread(self.conv_repo.create_conversation)
            self.conversation_id = row.get("id")
            self.preferences = await asyncio.to_thread(supabase_client.get_preferences)
            log.info("Memoria inicializada (conversación={}).", self.conversation_id)
        except Exception as exc:  # noqa: BLE001
            log.error("Error inicializando memoria: {}", exc)

    # ------------------------------------------------------------------ #
    # Guardado de interacciones
    # ------------------------------------------------------------------ #
    async def save_interaction(
        self,
        user_input: str,
        assistant_response: str,
        intent_type: str = "conversation",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Guarda un intercambio en los tres niveles de memoria."""
        # Short-term en memoria.
        self.short_term.append({"user": user_input, "assistant": assistant_response})
        if len(self.short_term) > settings.short_term_size:
            self.short_term.pop(0)

        # Contexto conversacional.
        self.context.add_turn("user", user_input)
        self.context.add_turn("assistant", assistant_response)
        await self.context.maybe_summarize()

        # Long-term (Supabase) — no bloqueante ante fallos.
        if self.conversation_id:
            try:
                await asyncio.to_thread(
                    self.conv_repo.add_message,
                    self.conversation_id, "user", user_input, intent_type, metadata or {},
                )
                await asyncio.to_thread(
                    self.conv_repo.add_message,
                    self.conversation_id, "assistant", assistant_response, intent_type, metadata or {},
                )
            except Exception as exc:  # noqa: BLE001
                log.error("Error guardando mensajes en Supabase: {}", exc)

        # Memoria semántica para interacciones relevantes (no triviales).
        if settings.ai_provider != "ollama" and len(user_input) > 12:
            await self.vector.remember(
                content=f"Usuario: {user_input} | YU: {assistant_response}",
                kind="event",
                importance=0.5,
                metadata={"intent": intent_type},
            )

        # Sincronización automática con Obsidian (Cerebro de YU) para intenciones clave o notas
        if intent_type in ("obsidian", "reminder", "research"):
            try:
                from integrations.obsidian_controller import obsidian_controller
                await asyncio.to_thread(
                    obsidian_controller.append_to_daily_note,
                    f"**[{intent_type.upper()}]** User: {user_input} -> YU: {assistant_response}"
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("No se pudo registrar en Obsidian Daily Note: {}", exc)


    # ------------------------------------------------------------------ #
    # Recuperación
    # ------------------------------------------------------------------ #
    async def recall(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Recupera memorias semánticamente similares a la consulta."""
        if settings.ai_provider == "ollama":
            return []
        return await self.vector.search_similar(query, limit=limit)

    async def get_context(self, query: str = "") -> str:
        """Construye el contexto textual (resumen + memorias relevantes)."""
        parts: list[str] = []
        ctx = self.context.context_text()
        if ctx:
            parts.append(ctx)

        if query:
            memories = await self.recall(query, limit=3)
            if memories:
                mem_text = "\n".join(f"- {m.get('content', '')}" for m in memories)
                parts.append(f"Recuerdos relevantes:\n{mem_text}")

        if self.preferences:
            prefs = ", ".join(f"{k}={v}" for k, v in self.preferences.items())
            parts.append(f"Preferencias del usuario: {prefs}")

        return "\n\n".join(parts)

    # ------------------------------------------------------------------ #
    # Preferencias
    # ------------------------------------------------------------------ #
    async def update_preference(self, key: str, value: Any) -> None:
        """Guarda/actualiza una preferencia del usuario."""
        self.preferences[key] = value
        try:
            await asyncio.to_thread(supabase_client.set_preference, key, value)
            # Memoria semántica de la preferencia.
            if settings.ai_provider != "ollama":
                await self.vector.remember(
                    content=f"Preferencia del usuario: {key} = {value}",
                    kind="preference",
                    importance=0.8,
                )
            log.info("Preferencia actualizada: {} = {}", key, value)
        except Exception as exc:  # noqa: BLE001
            log.error("Error actualizando preferencia: {}", exc)


memory_manager = MemoryManager()
