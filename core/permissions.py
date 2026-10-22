"""Sistema de permisos y confirmaciones de seguridad.

Las acciones de riesgo HIGH/CRITICAL requieren confirmación del usuario.
La UI puede registrar un callback para mostrar un diálogo; si no hay callback,
se usa la consola (input) como fallback.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Awaitable, Callable, Optional

from config.constants import RiskLevel
from config.settings import settings
from core.logger import log

# Firma del callback de confirmación. Recibe (mensaje, nivel_riesgo) y
# devuelve un booleano (puede ser una corrutina).
ConfirmationCallback = Callable[[str, RiskLevel], "bool | Awaitable[bool]"]


@dataclass
class PermissionRequest:
    """Registro de una solicitud de permiso."""

    description: str
    risk_level: RiskLevel
    granted: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


class PermissionManager:
    """Gestiona las confirmaciones de seguridad de YU."""

    def __init__(self) -> None:
        self._callback: Optional[ConfirmationCallback] = None
        self.history: list[PermissionRequest] = []
        # Permisos "recordados" por la sesión (auto-aprobados).
        self._session_grants: set[str] = set()

    # ------------------------------------------------------------------ #
    # Registro de callbacks de UI
    # ------------------------------------------------------------------ #
    def set_confirmation_callback(self, callback: ConfirmationCallback) -> None:
        """Registra un callback (por ejemplo, un diálogo de la UI)."""
        self._callback = callback
        log.debug("Callback de confirmación registrado.")

    def remember_for_session(self, action_key: str) -> None:
        """Aprueba automáticamente futuras acciones con esta clave."""
        self._session_grants.add(action_key)

    # ------------------------------------------------------------------ #
    # Lógica de confirmación
    # ------------------------------------------------------------------ #
    def requires_confirmation(self, risk: RiskLevel) -> bool:
        """Determina si un nivel de riesgo necesita confirmación."""
        if not settings.require_confirmation_high_risk:
            return False
        return risk >= RiskLevel.HIGH

    async def request(
        self,
        description: str,
        risk_level: RiskLevel,
        action_key: str | None = None,
    ) -> bool:
        """Solicita confirmación al usuario para una acción.

        Devuelve True si la acción puede continuar.
        """
        # Acciones de bajo riesgo se aprueban automáticamente.
        if not self.requires_confirmation(risk_level):
            self._record(description, risk_level, True)
            return True

        # Aprobación recordada en la sesión.
        if action_key and action_key in self._session_grants:
            log.info("Acción '{}' aprobada (recordada en sesión).", action_key)
            self._record(description, risk_level, True)
            return True

        granted = await self._ask(description, risk_level)
        self._record(description, risk_level, granted)
        log.info(
            "Confirmación [{}] '{}' -> {}",
            risk_level.value,
            description,
            "CONCEDIDA" if granted else "DENEGADA",
        )
        return granted

    async def _ask(self, description: str, risk_level: RiskLevel) -> bool:
        """Pregunta al usuario usando el callback o la consola."""
        if self._callback is not None:
            try:
                result = self._callback(description, risk_level)
                if asyncio.iscoroutine(result):
                    return bool(await result)
                return bool(result)
            except Exception as exc:  # noqa: BLE001
                log.error("Error en callback de confirmación: {}", exc)
                return False

        # Fallback a consola (no bloquea el event loop).
        prompt = (
            f"\n[YU][{risk_level.value.upper()}] {description}\n"
            "¿Confirmas esta acción? (s/n): "
        )

        def _blocking_input() -> bool:
            answer = input(prompt).strip().lower()
            return answer in {"s", "si", "sí", "y", "yes"}

        return await asyncio.to_thread(_blocking_input)

    def _record(self, description: str, risk: RiskLevel, granted: bool) -> None:
        self.history.append(
            PermissionRequest(description=description, risk_level=risk, granted=granted)
        )

    def last_decisions(self, n: int = 10) -> list[PermissionRequest]:
        """Devuelve las últimas n decisiones de permisos."""
        return self.history[-n:]


# Instancia compartida en toda la aplicación.
permission_manager = PermissionManager()
