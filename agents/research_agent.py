"""Agente de investigación: busca en la web y resume con el LLM."""
from __future__ import annotations

from typing import Any

import httpx

from agents.base_agent import AgentResult, BaseAgent
from core.logger import log


class ResearchAgent(BaseAgent):
    """Realiza búsquedas web y sintetiza resultados."""

    name = "research_agent"

    DDG_API = "https://api.duckduckgo.com/"
    DDG_HTML = "https://html.duckduckgo.com/html/"

    async def _duckduckgo(self, query: str) -> list[str]:
        """Obtiene resultados de la API instantánea de DuckDuckGo."""
        snippets: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    self.DDG_API,
                    params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
                    headers={"User-Agent": "YU/1.0"},
                )
                data = resp.json()
            if data.get("AbstractText"):
                snippets.append(data["AbstractText"])
            for topic in data.get("RelatedTopics", [])[:6]:
                if isinstance(topic, dict) and topic.get("Text"):
                    snippets.append(topic["Text"])
        except Exception as exc:  # noqa: BLE001
            log.error("Error consultando DuckDuckGo: {}", exc)
        return snippets

    async def quick_search(self, query: str = "", **_: Any) -> str:
        """Búsqueda rápida que devuelve un resumen corto."""
        result = await self.execute(query=query, depth="quick")
        return result.message

    async def execute(  # type: ignore[override]
        self,
        query: str = "",
        topic: str = "",
        depth: str = "quick",
        **_: Any,
    ) -> AgentResult:
        """Acepta tanto llamadas con kwargs sueltos (del decision_engine) como dict."""
        query = query or topic
        if not query:
            return self._fail("No se especificó qué buscar.")

        log.info("[research_agent] Buscando: '{}'", query)
        snippets = await self._duckduckgo(query)

        if not snippets:
            # Sin resultados web: responde con conocimiento del modelo.
            answer = await self.ask_llm(
                f"Responde de forma breve y precisa: {query}",
                system="Eres un asistente de investigación conciso.",
            )
            return self._ok(output=answer, message=answer or "No encontré información.")

        instruction = (
            "Resume en 2-3 frases" if depth == "quick"
            else "Elabora un resumen detallado y estructurado"
        )
        prompt = (
            f"Pregunta: {query}\n\nResultados de búsqueda:\n"
            + "\n".join(f"- {s}" for s in snippets)
            + f"\n\n{instruction} en el idioma de la pregunta."
        )
        summary = await self.ask_llm(prompt, system="Eres un investigador experto.")
        return self._ok(output=snippets, message=summary or snippets[0])


research_agent = ResearchAgent()
