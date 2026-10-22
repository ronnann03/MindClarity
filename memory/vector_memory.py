"""Memoria vectorial: guarda y recupera recuerdos por similitud semántica."""
from __future__ import annotations

import asyncio
from typing import Any

from config.settings import settings
from core.logger import log
from database.repositories.memory_repo import MemoryRepository, memory_repo
from memory.embeddings import EmbeddingService, embedding_service


class VectorMemory:
    """Capa de memoria semántica sobre pgvector en Supabase."""

    def __init__(
        self,
        repo: MemoryRepository | None = None,
        embedder: EmbeddingService | None = None,
    ) -> None:
        self.repo = repo or memory_repo
        self.embedder = embedder or embedding_service

    async def remember(
        self,
        content: str,
        kind: str = "fact",
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Almacena un recuerdo generando su embedding."""
        embedding = await self.embedder.embed(content)
        if not embedding:
            log.warning("No se pudo generar embedding; recuerdo no guardado.")
            return
        await asyncio.to_thread(
            self.repo.save_memory, content, embedding, kind, importance, metadata
        )

    async def search_similar(
        self,
        query: str,
        limit: int = 5,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Busca recuerdos similares a una consulta de texto."""
        query_embedding = await self.embedder.embed(query)
        if not query_embedding:
            return []
        return await asyncio.to_thread(
            self.repo.search_similar,
            query_embedding,
            limit,
            threshold if threshold is not None else settings.memory_similarity_threshold,
        )

    async def search_by_embedding(
        self,
        query_embedding: list[float],
        limit: int = 5,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Busca recuerdos a partir de un embedding ya calculado."""
        return await asyncio.to_thread(
            self.repo.search_similar, query_embedding, limit, threshold
        )


vector_memory = VectorMemory()
