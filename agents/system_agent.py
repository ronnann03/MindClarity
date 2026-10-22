"""Agente de sistema: interpreta comandos complejos y los enruta a automation."""
from __future__ import annotations

from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from automation.app_launcher import app_launcher
from automation.file_manager import file_manager
from automation.pc_controller import pc_controller
from automation.task_automation import task_automation
from automation.window_manager import window_manager
from core.logger import log


class SystemAgent(BaseAgent):
    """Coordina la automatización del sistema a partir de instrucciones."""

    name = "system_agent"

    def __init__(self, model=None) -> None:
        super().__init__(model)
        # Acciones disponibles que el agente puede invocar.
        self.actions = {
            # ---- Aplicaciones ------------------------------------------ #
            "open_app":          app_launcher.open_app,
            "close_app":         app_launcher.close_app,
            "list_running_apps": app_launcher.list_running_apps,
            # ---- Control de PC ----------------------------------------- #
            "set_volume":        pc_controller.set_volume,
            "get_volume":        pc_controller.get_volume,
            "set_brightness":    pc_controller.set_brightness,
            "take_screenshot":   pc_controller.take_screenshot,
            "lock_screen":       pc_controller.lock_screen,
            "type_text":         pc_controller.type_text,
            "press_key":         pc_controller.press_key,
            "control_mouse":     pc_controller.control_mouse,
            # ---- Ventanas ---------------------------------------------- #
            "minimize":          window_manager.minimize,
            "minimize_window":   window_manager.minimize,
            "maximize":          window_manager.maximize,
            "maximize_window":   window_manager.maximize,
            "restore":           window_manager.restore,
            "restore_window":    window_manager.restore,
            "focus":             window_manager.focus,
            "focus_window":      window_manager.focus,
            "close_window":      window_manager.close,
            "move_window":       window_manager.move,
            "resize_window":     window_manager.resize,
            "get_windows_list":  window_manager.get_windows_list,
            # ---- Automatizaciones -------------------------------------- #
            "organize_downloads": task_automation.organize_downloads,
            "bulk_rename":        task_automation.bulk_rename,
            "create_shortcut":    task_automation.create_shortcut,
            "schedule_task":      task_automation.schedule_task,
            # ---- Gestión de archivos y carpetas ------------------------ #
            "create_file":       file_manager.create_file,
            "create_folder":     file_manager.create_folder,
            "delete_file":       file_manager.delete_file,
            "delete_folder":     file_manager.delete_folder,
            "move_file":         file_manager.move_file,
            "copy_file":         file_manager.copy_file,
            "list_directory":    file_manager.list_directory,
            "search_files":      file_manager.search_files,
        }

    async def execute(  # type: ignore[override]
        self,
        action: str | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        """Decide qué acción ejecutar.

        Acepta llamadas con kwargs sueltos del decision_engine:
          system_agent.execute(action="open_app", name="chrome")

        Si no hay 'action', usa el LLM para inferirla a partir de los kwargs.
        """
        task = {"action": action, **kwargs} if action else dict(kwargs)
        # Solo se excluye 'action' (clave de enrutamiento).
        # 'text', 'query', y cualquier otro kwarg son parámetros válidos para las funciones.
        params = {k: v for k, v in task.items() if k != "action"}

        if not action:
            action, params = await self._infer_action(task)

        func = self.actions.get(action)
        if func is None:
            return self._fail(f"Acción de sistema no soportada: '{action}'.")

        try:
            result = func(**params) if params else func()
            return self._ok(output=result, message=str(result))
        except TypeError as exc:
            # Si la función no acepta los kwargs extras, reintenta filtrando
            # solo los que la función declara en su firma.
            import inspect  # noqa: PLC0415
            try:
                sig = inspect.signature(func)
                accepted = set(sig.parameters)
                filtered = {k: v for k, v in params.items() if k in accepted}
                result = func(**filtered) if filtered else func()
                return self._ok(output=result, message=str(result))
            except Exception as exc2:  # noqa: BLE001
                return self._fail(f"Error ejecutando '{action}': {exc2}")
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"Error ejecutando '{action}': {exc}")

    async def _infer_action(self, task: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Usa el LLM para inferir la acción a partir de texto libre."""
        text = task.get("query") or task.get("text") or str(task)
        available = ", ".join(self.actions.keys())
        prompt = (
            f"Dado el comando del usuario: '{text}', elige UNA acción de esta lista: "
            f"{available}. Responde solo con el nombre de la acción."
        )
        action = (await self.ask_llm(prompt)).strip().split()[0] if text else ""
        log.debug("[system_agent] Acción inferida: {}", action)
        return action, {}


system_agent = SystemAgent()
