"""Sistema de auditoría y registro de acciones de YU.

Registra todas las acciones ejecutadas, permisos concedidos/denegados,
y errores para análisis y seguridad.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from config.settings import settings
from core.logger import log


class AuditLevel(str, Enum):
    """Niveles de auditoría."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    PERMISSION = "permission"


@dataclass
class AuditEvent:
    """Evento auditado."""
    timestamp: str
    level: AuditLevel
    action: str
    agent: str
    user: str
    status: str
    details: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convierte a diccionario."""
        data = asdict(self)
        data["level"] = self.level.value
        return data


class AuditManager:
    """Gestor de auditoría centralizado."""

    def __init__(self) -> None:
        self.audit_dir = settings.log_dir / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.audit_file = self.audit_dir / "audit.jsonl"
        self.current_user = "default"

    def set_current_user(self, user: str) -> None:
        """Establece el usuario actual para auditoría."""
        self.current_user = user

    def log_action(
        self,
        action: str,
        agent: str,
        status: str = "success",
        details: dict[str, Any] | None = None,
        error: str = "",
    ) -> None:
        """Registra una acción."""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            level=AuditLevel.ERROR if error else AuditLevel.INFO,
            action=action,
            agent=agent,
            user=self.current_user,
            status=status,
            details=details or {},
            error=error,
        )

        # Escribir en archivo JSONL
        with open(self.audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

        log.debug("[audit] {} | {}: {}", action, agent, status)

    def log_permission(
        self,
        action: str,
        granted: bool,
        reason: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Registra una decisión de permiso."""
        status = "granted" if granted else "denied"
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            level=AuditLevel.PERMISSION,
            action=f"permission:{action}",
            agent="permission_manager",
            user=self.current_user,
            status=status,
            details={"reason": reason, **(details or {})},
        )

        with open(self.audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

        log.info("[audit] Permiso {}: {} ({})", status, action, reason)

    def log_error(
        self,
        action: str,
        agent: str,
        error: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Registra un error."""
        self.log_action(action, agent, "error", details, error)

    def get_events(
        self,
        user: str | None = None,
        agent: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Obtiene eventos de auditoría filtrados."""
        events = []

        try:
            with open(self.audit_file, "r", encoding="utf-8") as f:
                for line in f.readlines()[-limit:]:
                    event = json.loads(line)
                    # Filtrar
                    if user and event.get("user") != user:
                        continue
                    if agent and event.get("agent") != agent:
                        continue
                    events.append(event)
        except FileNotFoundError:
            pass

        return events

    def get_stats(self) -> dict[str, Any]:
        """Obtiene estadísticas de auditoría."""
        events = self.get_events(limit=10000)

        stats = {
            "total_events": len(events),
            "by_level": {},
            "by_agent": {},
            "by_user": {},
            "errors": [],
        }

        for event in events:
            # Por nivel
            level = event.get("level", "unknown")
            stats["by_level"][level] = stats["by_level"].get(level, 0) + 1

            # Por agente
            agent = event.get("agent", "unknown")
            stats["by_agent"][agent] = stats["by_agent"].get(agent, 0) + 1

            # Por usuario
            user = event.get("user", "unknown")
            stats["by_user"][user] = stats["by_user"].get(user, 0) + 1

            # Errores
            if event.get("error"):
                stats["errors"].append({
                    "timestamp": event.get("timestamp"),
                    "agent": agent,
                    "error": event.get("error"),
                })

        return stats


audit_manager = AuditManager()
