"""Clase base abstracta para los agentes de YU."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from core.logger import log
from models.openai_model import OpenAIModel, openai_model  # conservado para inyección directa

# ModelRouter se importa con lazy import para evitar ciclos en tests parciales.
def _default_model() -> OpenAIModel:  # type: ignore[return]
    try:
        from models.model_router import model_router  # noqa: PLC0415
        return model_router  # type: ignore[return-value]
    except Exception:
        return openai_model


@dataclass
class AgentResult:
    """Resultado estándar devuelto por cualquier agente."""

    success: bool
    output: Any = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:  # Útil para que el orquestador lo narre.
        return self.message or str(self.output or "")


class BaseAgent(abc.ABC):
    """Agente base con utilidades de LLM, logging y manejo de errores."""

    name: str = "base_agent"

    def __init__(self, model: OpenAIModel | None = None) -> None:
        self.model = model or _default_model()

    @abc.abstractmethod
    async def execute(self, **kwargs: Any) -> AgentResult:  # type: ignore[override]
        """Ejecuta la tarea del agente. Debe implementarse en subclases.

        Los subclases reciben los parámetros como kwargs sueltos, igual
        que los envía el decision_engine (func(**step.params)).
        """
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # Helpers comunes
    # ------------------------------------------------------------------ #
    async def ask_llm(self, prompt: str, system: str | None = None) -> str:
        """Consulta sencilla al modelo de lenguaje."""
        try:
            return await self.model.simple_chat(prompt, system=system)
        except Exception as exc:  # noqa: BLE001
            log.error("[{}] Error consultando LLM: {}", self.name, exc)
            return ""

    def _ok(self, output: Any = None, message: str = "", **meta: Any) -> AgentResult:
        log.info("[{}] OK: {}", self.name, message or output)
        return AgentResult(success=True, output=output, message=message, metadata=meta)

    def _fail(self, message: str, **meta: Any) -> AgentResult:
        log.warning("[{}] Fallo: {}", self.name, message)
        return AgentResult(success=False, message=message, metadata=meta)

    async def safe_execute(self, **kwargs: Any) -> AgentResult:
        """Envuelve execute() con manejo de errores."""
        try:
            return await self.execute(**kwargs)
        except Exception as exc:  # noqa: BLE001
            log.error("[{}] Excepción no controlada: {}", self.name, exc)
            return self._fail(f"Error en el agente {self.name}: {exc}")
