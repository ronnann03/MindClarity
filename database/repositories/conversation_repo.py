"""Repositorio para conversaciones y mensajes."""
from __future__ import annotations

from typing import Any

from config.constants import TABLE_CONVERSATIONS, TABLE_MESSAGES
from core.logger import log
from database.supabase_client import SupabaseClient, supabase_client


class ConversationRepository:
    """Operaciones de persistencia para conversaciones y mensajes."""

    def __init__(self, client: SupabaseClient | None = None) -> None:
        self.db = client or supabase_client

    # ------------------------------------------------------------------ #
    # Conversaciones
    # ------------------------------------------------------------------ #
    def create_conversation(self, title: str | None = None) -> dict[str, Any]:
        """Crea una conversación nueva y devuelve su registro."""
        data = {"title": title or "Conversación con YU"}
        row = self.db.insert(TABLE_CONVERSATIONS, data)
        log.debug("Conversación creada: {}", row.get("id"))
        return row

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        rows = self.db.select(TABLE_CONVERSATIONS, {"id": conversation_id}, limit=1)
        return rows[0] if rows else None

    def update_summary(self, conversation_id: str, summary: str) -> dict[str, Any]:
        return self.db.update(TABLE_CONVERSATIONS, conversation_id, {"summary": summary})

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.db.select(
            TABLE_CONVERSATIONS, limit=limit, order_by="updated_at", descending=True
        )

    # ------------------------------------------------------------------ #
    # Mensajes
    # ------------------------------------------------------------------ #
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        intent_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Inserta un mensaje en una conversación."""
        data = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "intent_type": intent_type,
            "metadata": metadata or {},
        }
        return self.db.insert(TABLE_MESSAGES, data)

    def get_messages(self, conversation_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return self.db.select(
            TABLE_MESSAGES,
            {"conversation_id": conversation_id},
            limit=limit,
            order_by="created_at",
            descending=False,
        )


conversation_repo = ConversationRepository()
