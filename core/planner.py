"""Planificador: convierte un Intent en un Plan ejecutable de pasos.

Cada paso (`ActionStep`) referencia un módulo y una función con sus parámetros.
"""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from config.constants import ActionStatus, IntentType, RiskLevel
from core.intent_detector import Intent
from core.logger import log


class ActionStep(BaseModel):
    """Un paso individual dentro de un plan."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    module: str = Field(description="Módulo que ejecuta el paso, p.ej. 'app_launcher'.")
    function: str = Field(description="Función a invocar, p.ej. 'open_app'.")
    params: dict = Field(default_factory=dict, description="Argumentos de la función.")
    description: str = Field(default="", description="Descripción legible del paso.")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    status: ActionStatus = Field(default=ActionStatus.PENDING)
    result: object | None = Field(default=None)


class Plan(BaseModel):
    """Conjunto ordenado de pasos derivados de un Intent."""

    intent_type: IntentType
    steps: list[ActionStep] = Field(default_factory=list)
    description: str = Field(default="")

    @property
    def max_risk(self) -> RiskLevel:
        """Riesgo máximo entre todos los pasos del plan."""
        risk = RiskLevel.LOW
        for step in self.steps:
            if step.risk_level > risk:
                risk = step.risk_level
        return risk

    @property
    def is_empty(self) -> bool:
        return len(self.steps) == 0


class Planner:
    """Construye un Plan a partir de un Intent.

    El mapeo intención->módulo/función se basa en reglas. Para conversación
    pura no se generan pasos (la respuesta la genera el orquestador con el LLM).
    """

    def build(self, intent: Intent) -> Plan:
        """Crea el plan correspondiente al intent."""
        plan = Plan(intent_type=intent.type, description=intent.action or intent.type.value)
        ent = intent.entities
        params = {**intent.parameters, **ent}

        builder = getattr(self, f"_plan_{intent.type.value}", None)
        if builder is not None:
            builder(plan, intent, params)
        else:
            log.debug("Sin builder para {}, plan vacío.", intent.type.value)

        log.info("Plan generado con {} paso(s) | riesgo={}", len(plan.steps), plan.max_risk.value)
        return plan

    # ------------------------------------------------------------------ #
    # Builders por tipo de intención
    # ------------------------------------------------------------------ #
    def _add(self, plan: Plan, module: str, function: str, params: dict,
             description: str, risk: RiskLevel) -> None:
        plan.steps.append(
            ActionStep(
                module=module,
                function=function,
                params=params,
                description=description,
                risk_level=risk,
            )
        )

    def _plan_conversation(self, plan: Plan, intent: Intent, params: dict) -> None:
        # La conversación la maneja directamente el orquestador (sin pasos).
        return

    def _plan_system_control(self, plan: Plan, intent: Intent, params: dict) -> None:
        action = (intent.action or "").lower()
        mapping: dict[str, tuple[str, str, RiskLevel]] = {
            # ---- Volumen ------------------------------------------------ #
            "set_volume":        ("pc_controller",  "set_volume",        RiskLevel.LOW),
            "get_volume":        ("pc_controller",  "get_volume",        RiskLevel.LOW),
            # ---- Brillo ------------------------------------------------- #
            "set_brightness":    ("pc_controller",  "set_brightness",    RiskLevel.LOW),
            # ---- Capturas / bloqueo ------------------------------------- #
            "take_screenshot":   ("pc_controller",  "take_screenshot",   RiskLevel.LOW),
            "lock_screen":       ("pc_controller",  "lock_screen",       RiskLevel.HIGH),
            # ---- Teclado / ratón ---------------------------------------- #
            "type_text":         ("pc_controller",  "type_text",         RiskLevel.MEDIUM),
            "press_key":         ("pc_controller",  "press_key",         RiskLevel.MEDIUM),
            "control_mouse":     ("pc_controller",  "control_mouse",     RiskLevel.LOW),
            # ---- Aplicaciones ------------------------------------------ #
            "open_app":          ("app_launcher",   "open_app",          RiskLevel.LOW),
            "close_app":         ("app_launcher",   "close_app",         RiskLevel.MEDIUM),
            "list_running_apps": ("app_launcher",   "list_running_apps", RiskLevel.LOW),
            # ---- Ventanas ----------------------------------------------- #
            "minimize":          ("window_manager", "minimize",          RiskLevel.LOW),
            "minimize_window":   ("window_manager", "minimize",          RiskLevel.LOW),
            "maximize":          ("window_manager", "maximize",          RiskLevel.LOW),
            "maximize_window":   ("window_manager", "maximize",          RiskLevel.LOW),
            "restore":           ("window_manager", "restore",           RiskLevel.LOW),
            "restore_window":    ("window_manager", "restore",           RiskLevel.LOW),
            "focus":             ("window_manager", "focus",             RiskLevel.LOW),
            "focus_window":      ("window_manager", "focus",             RiskLevel.LOW),
            "close_window":      ("window_manager", "close",             RiskLevel.MEDIUM),
            "move_window":       ("window_manager", "move",              RiskLevel.LOW),
            "resize_window":     ("window_manager", "resize",            RiskLevel.LOW),
            "get_windows_list":  ("window_manager", "get_windows_list",  RiskLevel.LOW),
        }
        # Una acción desconocida no debe convertirse en una apertura de app.
        if action not in mapping:
            return
        module, func, risk = mapping[action]
        self._add(plan, module, func, params, intent.action or func, risk)

    def _plan_file_operation(self, plan: Plan, intent: Intent, params: dict) -> None:
        action = (intent.action or "").lower()
        risk_map = {
            "create_file": RiskLevel.MEDIUM,
            "create_folder": RiskLevel.MEDIUM,
            "delete_file": RiskLevel.HIGH,
            "delete_folder": RiskLevel.CRITICAL,
            "move_file": RiskLevel.HIGH,
            "copy_file": RiskLevel.MEDIUM,
            "list_directory": RiskLevel.LOW,
            "search_files": RiskLevel.LOW,
        }
        func = action or "list_directory"
        self._add(plan, "file_manager", func, params, intent.action or func,
                  risk_map.get(func, RiskLevel.HIGH))

    def _plan_media_control(self, plan: Plan, intent: Intent, params: dict) -> None:
        action = (intent.action or "").lower()
        if "music" in action or params.get("type") == "music":
            self._add(plan, "youtube_controller", "play_music", params,
                      "Reproducir música en YouTube", RiskLevel.LOW)
        elif "video" in action or params.get("query"):
            self._add(plan, "youtube_controller", "play_video", params,
                      "Reproducir vídeo en YouTube", RiskLevel.LOW)
        else:
            self._add(plan, "youtube_controller", "open_youtube", {},
                      "Abrir YouTube", RiskLevel.LOW)

    def _plan_search(self, plan: Plan, intent: Intent, params: dict) -> None:
        self._add(plan, "research_agent", "quick_search", params,
                  "Búsqueda web rápida", RiskLevel.LOW)

    def _plan_research(self, plan: Plan, intent: Intent, params: dict) -> None:
        self._add(plan, "research_agent", "execute", params,
                  "Investigación profunda", RiskLevel.LOW)

    def _plan_weather(self, plan: Plan, intent: Intent, params: dict) -> None:
        self._add(plan, "weather_service", "get_weather", params,
                  "Consultar el clima", RiskLevel.LOW)

    def _plan_email(self, plan: Plan, intent: Intent, params: dict) -> None:
        # Inyecta 'action' para que email_agent sepa si leer o enviar.
        params_with_action = {"action": intent.action or "read_email", **params}
        risk = RiskLevel.HIGH if "send" in (intent.action or "") else RiskLevel.MEDIUM
        self._add(plan, "email_agent", "execute", params_with_action,
                  "Operación de correo", risk)

    def _plan_reminder(self, plan: Plan, intent: Intent, params: dict) -> None:
        # Inyecta 'action' para que productivity_agent sepa qué hacer.
        params_with_action = {"action": intent.action or "create_task", **params}
        self._add(plan, "productivity_agent", "execute", params_with_action,
                  "Gestión de productividad", RiskLevel.LOW)

    def _plan_automation(self, plan: Plan, intent: Intent, params: dict) -> None:
        # Inyecta 'action' para que system_agent pueda enrutar la automatización.
        params_with_action = {"action": intent.action, **params}
        self._add(plan, "system_agent", "execute", params_with_action,
                  "Automatización del sistema", RiskLevel.MEDIUM)

    def _plan_calendar(self, plan: Plan, intent: Intent, params: dict) -> None:
        """Enruta las operaciones de Google Calendar al calendar_agent."""
        action = intent.action or "list_events"
        params_with_action = {"action": action, **params}
        risk = (
            RiskLevel.HIGH if action in {"delete_event", "eliminar", "borrar", "eliminar_evento"}
            else RiskLevel.LOW
        )
        self._add(plan, "calendar_agent", "execute", params_with_action,
                  "Gestión de Google Calendar", risk)

    def _plan_obsidian(self, plan: Plan, intent: Intent, params: dict) -> None:
        """Enruta operaciones de Obsidian (cerebro de notas) al obsidian_agent."""
        action = intent.action or "append_daily_note"
        params_with_action = {"action": action, **params}
        self._add(plan, "obsidian_agent", "execute", params_with_action,
                  f"Operación Obsidian ({action})", RiskLevel.LOW)

    def _plan_web(self, plan: Plan, intent: Intent, params: dict) -> None:
        allowed = {'open_url', 'search', 'open_youtube', 'open_maps', 'open_gmail'}
        if intent.action in allowed:
            self._add(plan, 'web_agent', 'execute', {'action':intent.action, **params},
                      'Abrir contenido en el navegador', RiskLevel.LOW)


planner = Planner()

