"""Generación de embeddings con caché LRU y procesamiento por lotes."""
from __future__ import annotations

import hashlib
from collections import OrderedDict

from core.logger import log
from models.openai_model import OpenAIModel, openai_model


def _default_model() -> OpenAIModel:  # type: ignore[return]
    """Devuelve model_router si está disponible; si no, openai_model."""
    try:
        from models.model_router import model_router  # noqa: PLC0415
        return model_router  # type: ignore[return-value]
    except Exception:
        return openai_model


class EmbeddingService:
    """Genera embeddings con caché en memoria (LRU)."""

    def __init__(self, model: OpenAIModel | None = None, cache_size: int = 512) -> None:
        self.model = model or _default_model()
        self._cache: "OrderedDict[str, list[float]]" = OrderedDict()
        self._cache_size = cache_size

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _cache_get(self, text: str) -> list[float] | None:
        key = self._key(text)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def _cache_put(self, text: str, vector: list[float]) -> None:
        key = self._key(text)
        self._cache[key] = vector
        self._cache.move_to_end(key)
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

    async def embed(self, text: str) -> list[float]:
        """Genera (o recupera de caché) el embedding de un texto."""
        cached = self._cache_get(text)
        if cached is not None:
            return cached
        try:
            vector = await self.model.embedding(text)
            self._cache_put(text, vector)
            return vector
        except Exception as exc:  # noqa: BLE001
            log.error("Error generando embedding: {}", exc)
            return []

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Genera embeddings para una lista de textos, usando caché."""
        results: list[list[float] | None] = [None] * len(texts)
        pending: list[tuple[int, str]] = []

        for i, text in enumerate(texts):
            cached = self._cache_get(text)
            if cached is not None:
                results[i] = cached
            else:
                pending.append((i, text))

        if pending:
            try:
                vectors = await self.model.embeddings([t for _, t in pending])
                for (idx, text), vector in zip(pending, vectors):
                    self._cache_put(text, vector)
                    results[idx] = vector
            except Exception as exc:  # noqa: BLE001
                log.error("Error en embed_batch: {}", exc)
                for idx, _ in pending:
                    results[idx] = []

        return [r if r is not None else [] for r in results]


embedding_service = EmbeddingService()
