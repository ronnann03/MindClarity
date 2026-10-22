"""Agente executor de Obsidian para YU.

Expone las capacidades del Vault de Obsidian como herramientas ejecutables.
"""
from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from core.logger import log
from integrations.obsidian_controller import obsidian_controller


class ObsidianAgent(BaseAgent):
    """Módulo ejecutable para manipular notas en Obsidian."""

    name = "obsidian_agent"

    def __init__(self, model: Any | None = None) -> None:
        super().__init__(model=model)


    async def execute(self, action: str, **kwargs: Any) -> Any:
        """Punto de entrada único del orquestador."""
        log.info("[obsidian_agent] Acción '{}' con parámetros: {}", action, kwargs)
        handler = getattr(self, action, None)
        if handler is None:
            return self._fail(f"Acción '{action}' no soportada por obsidian_agent.")
        return await handler(**kwargs)

    async def create_note(
        self,
        title: str,
        content: str,
        folder: str = "YU Brain",
        **_kwargs: Any,
    ) -> str:
        """Crea una nota en Obsidian."""
        res = obsidian_controller.create_note(title=title, content=content, folder=folder)
        return self._ok(res)

    async def append_daily_note(self, content: str, **_kwargs: Any) -> str:
        """Agrega un pensamiento o diario a Obsidian."""
        res = obsidian_controller.append_to_daily_note(content=content)
        return self._ok(res)

    async def search_notes(self, query: str, **_kwargs: Any) -> str:
        """Busca notas en el Vault de Obsidian."""
        results = obsidian_controller.search_notes(query=query)
        if not results:
            return self._ok(f"No encontré notas relacionadas con '{query}' en tu Obsidian.")
        summary = "\n".join(
            f"- **{r['title']}** ({r['path']}): {r['snippet']}..." for r in results
        )
        return self._ok(f"Encontré estas notas en tu Obsidian:\n{summary}")

    async def read_note(self, title: str, **_kwargs: Any) -> str:
        """Lee el contenido de una nota de Obsidian."""
        res = obsidian_controller.read_note(title=title)
        return self._ok(res)


obsidian_agent = ObsidianAgent()
