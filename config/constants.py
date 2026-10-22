"""Enumeraciones y constantes compartidas por todo YU."""
from __future__ import annotations

from enum import Enum


class IntentType(str, Enum):
    """Tipos de intención que YU puede detectar en una petición."""

    CONVERSATION = "conversation"
    SYSTEM_CONTROL = "system_control"
    FILE_OPERATION = "file_operation"
    MEDIA_CONTROL = "media_control"
    SEARCH = "search"
    EMAIL = "email"
    REMINDER = "reminder"
    AUTOMATION = "automation"
    RESEARCH = "research"
    WEATHER = "weather"
    CALENDAR = "calendar"
    OBSIDIAN = "obsidian"
    WEB = "web"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    """Nivel de riesgo asociado a una acción.

    Se usa para decidir si se requiere confirmación del usuario.
    """

    LOW = "low"          # Sin efectos secundarios destructivos.
    MEDIUM = "medium"    # Modifica estado del sistema de forma reversible.
    HIGH = "high"        # Operaciones potencialmente destructivas.
    CRITICAL = "critical"  # Irreversible o de impacto severo.

    @property
    def weight(self) -> int:
        """Peso numérico para comparar niveles de riesgo."""
        return {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }[self]

    def __ge__(self, other: object) -> bool:  # type: ignore[override]
        if isinstance(other, RiskLevel):
            return self.weight >= other.weight
        return NotImplemented

    def __gt__(self, other: object) -> bool:  # type: ignore[override]
        if isinstance(other, RiskLevel):
            return self.weight > other.weight
        return NotImplemented


class ActionStatus(str, Enum):
    """Estado de un paso de acción individual."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    AWAITING_CONFIRMATION = "awaiting_confirmation"


class ExecutionStatus(str, Enum):
    """Estado global de la ejecución de un plan."""

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VoiceState(str, Enum):
    """Estados de la máquina del pipeline de voz."""

    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


# Mapeo por defecto de tipos de intención a su nivel de riesgo base.
DEFAULT_RISK_BY_INTENT: dict[IntentType, RiskLevel] = {
    IntentType.CONVERSATION: RiskLevel.LOW,
    IntentType.SEARCH: RiskLevel.LOW,
    IntentType.WEATHER: RiskLevel.LOW,
    IntentType.RESEARCH: RiskLevel.LOW,
    IntentType.MEDIA_CONTROL: RiskLevel.LOW,
    IntentType.REMINDER: RiskLevel.LOW,
    IntentType.SYSTEM_CONTROL: RiskLevel.MEDIUM,
    IntentType.AUTOMATION: RiskLevel.MEDIUM,
    IntentType.EMAIL: RiskLevel.MEDIUM,
    IntentType.FILE_OPERATION: RiskLevel.HIGH,
    IntentType.CALENDAR: RiskLevel.LOW,
    IntentType.OBSIDIAN: RiskLevel.LOW,
    IntentType.UNKNOWN: RiskLevel.LOW,
}

# Nombres de tablas en Supabase.
TABLE_CONVERSATIONS = "conversations"
TABLE_MESSAGES = "messages"
TABLE_MEMORIES = "memories"
TABLE_TASKS = "tasks"
TABLE_PREFERENCES = "preferences"
TABLE_LOGS = "system_logs"

# Dimensión de los embeddings de text-embedding-3-small.
EMBEDDING_DIM = 1536
