"""Motor de decisión: evalúa riesgo, pide confirmación y ejecuta los planes.

Mantiene un historial de decisiones y enruta cada paso a su módulo de ejecución.
"""
from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from config.constants import ActionStatus, ExecutionStatus
from core.logger import log
from core.permissions import PermissionManager, permission_manager
from core.planner import ActionStep, Plan


@dataclass
class ExecutionResult:
    """Resultado de ejecutar un plan completo."""

    status: ExecutionStatus
    outputs: list[Any] = field(default_factory=list)
    message: str = ""
    steps: list[ActionStep] = field(default_factory=list)


@dataclass
class Decision:
    """Entrada del historial de decisiones."""

    plan_description: str
    status: ExecutionStatus
    timestamp: datetime = field(default_factory=datetime.utcnow)


class DecisionEngine:
    """Decide si ejecutar un plan y lo enruta a los módulos correctos."""

    def __init__(self, permissions: PermissionManager | None = None) -> None:
        self.permissions = permissions or permission_manager
        # Registro de módulos ejecutables: nombre -> objeto con métodos.
        self._registry: dict[str, Any] = {}
        self.history: list[Decision] = []

    # ------------------------------------------------------------------ #
    # Registro de módulos de ejecución
    # ------------------------------------------------------------------ #
    def register(self, name: str, module: Any) -> None:
        """Registra un módulo/objeto bajo un nombre para enrutar pasos."""
        self._registry[name] = module
        log.debug("Módulo de ejecución registrado: {}", name)

    def register_many(self, modules: dict[str, Any]) -> None:
        for name, module in modules.items():
            self.register(name, module)

    # ------------------------------------------------------------------ #
    # Ejecución de planes
    # ------------------------------------------------------------------ #
    async def execute_plan(self, plan: Plan) -> ExecutionResult:
        """Evalúa, confirma y ejecuta cada paso del plan en orden."""
        if plan.is_empty:
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                message="Sin acciones que ejecutar.",
            )

        log.info("Evaluando plan '{}' | riesgo máx={}", plan.description, plan.max_risk.value)
        outputs: list[Any] = []
        any_failed = False
        any_success = False

        for step in plan.steps:
            # Confirmación de seguridad por paso según su riesgo.
            granted = await self.permissions.request(
                description=(step.description or f"{step.module}.{step.function}") +
                    (". Detalles: " + json.dumps(step.params, ensure_ascii=False, default=str) if step.params else ""),
                risk_level=step.risk_level,
                action_key=f"{step.module}.{step.function}",
            )
            if not granted:
                step.status = ActionStatus.CANCELLED
                log.warning("Paso cancelado por el usuario: {}", step.description)
                continue

            step.status = ActionStatus.RUNNING
            try:
                result = await self._run_step(step)
                step.result = result
                failed_text = isinstance(result, str) and result.lower().startswith(('no pude', 'no encuentro', 'no encontré', 'error ', 'no se pudo', 'no hay'))
                if getattr(result, "success", True) is False or result is False or failed_text:
                    step.status = ActionStatus.FAILED
                    any_failed = True
                    outputs.append(result)
                    continue
                step.status = ActionStatus.SUCCESS
                any_success = True
                outputs.append(result)
            except Exception as exc:  # noqa: BLE001
                step.status = ActionStatus.FAILED
                step.result = str(exc)
                any_failed = True
                log.error("Error ejecutando paso {}.{}: {}", step.module, step.function, exc)

        status = self._aggregate_status(any_success, any_failed, plan)
        self.history.append(Decision(plan.description, status))
        return ExecutionResult(
            status=status,
            outputs=outputs,
            steps=plan.steps,
            message=self._summarize(outputs),
        )

    async def _run_step(self, step: ActionStep) -> Any:
        """Resuelve módulo+función y la invoca (soporta sync y async)."""
        module = self._registry.get(step.module)
        if module is None:
            raise RuntimeError(f"Módulo no registrado: '{step.module}'")

        func: Callable[..., Any] | None = getattr(module, step.function, None)
        if func is None or not callable(func):
            raise RuntimeError(f"Función no encontrada: {step.module}.{step.function}")

        log.info("Ejecutando {}.{}({})", step.module, step.function, step.params)
        if inspect.iscoroutinefunction(func):
            return await func(**step.params)
        return func(**step.params)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _aggregate_status(any_success: bool, any_failed: bool, plan: Plan) -> ExecutionStatus:
        cancelled = all(s.status == ActionStatus.CANCELLED for s in plan.steps)
        if cancelled:
            return ExecutionStatus.CANCELLED
        if any_failed and any_success:
            return ExecutionStatus.PARTIAL
        if any_failed:
            return ExecutionStatus.FAILED
        return ExecutionStatus.COMPLETED

    @staticmethod
    def _summarize(outputs: list[Any]) -> str:
        if not outputs:
            return ""
        parts = [str(o) for o in outputs if o is not None]
        return " | ".join(parts)

    def recent_decisions(self, n: int = 10) -> list[Decision]:
        return self.history[-n:]


decision_engine = DecisionEngine()
