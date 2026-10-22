"""Repositorio para memorias semánticas y búsqueda vectorial."""
from __future__ import annotations

from typing import Any

from config.constants import TABLE_MEMORIES
from config.settings import settings
from core.logger import log
from database.supabase_client import SupabaseClient, supabase_client


class MemoryRepository:
    """Operaciones de persistencia y búsqueda vectorial de memorias."""

    def __init__(self, client: SupabaseClient | None = None) -> None:
        self.db = client or supabase_client

    def save_memory(
        self,
        content: str,
        embedding: list[float],
        kind: str = "fact",
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Guarda una memoria con su embedding."""
        data = {
            "content": content,
            "embedding": embedding,
            "kind": kind,
            "importance": importance,
            "metadata": metadata or {},
        }
        row = self.db.insert(TABLE_MEMORIES, data)
        log.debug("Memoria guardada ({}): {}", kind, content[:60])
        return row

    def search_similar(
        self,
        query_embedding: list[float],
        limit: int = 5,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Busca memorias similares mediante la función RPC `match_memories`."""
        threshold = threshold if threshold is not None else settings.memory_similarity_threshold
        results = self.db.rpc(
            "match_memories",
            {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": limit,
            },
        )
        log.debug("Búsqueda vectorial: {} resultados (umbral={}).", len(results), threshold)
        return results

    def list_memories(self, kind: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        filters = {"kind": kind} if kind else None
        return self.db.select(
            TABLE_MEMORIES, filters, limit=limit, order_by="created_at", descending=True
        )

    def delete_memory(self, memory_id: str) -> bool:
        return self.db.delete(TABLE_MEMORIES, memory_id)


memory_repo = MemoryRepository()
