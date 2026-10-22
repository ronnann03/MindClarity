"""Punto de entrada de YU.

Un único proceso que:
1. Registra los agentes/módulos ejecutables en el orquestador.
2. Arranca el pipeline de voz (wake word + mic) en un event loop de fondo.
3. Sirve la interfaz web + API REST/WebSocket (FastAPI/uvicorn) en el hilo
   principal, en http://localhost:8000.

Reemplaza a la antigua app de escritorio PyQt6: la interfaz ahora es la web
servida por `api/server.py` (carpeta `ui_web/`), accesible desde el navegador
en esta PC o desde cualquier dispositivo de la misma red.
"""
from __future__ import annotations

import asyncio
import threading

from config.settings import settings
from core.logger import log
from core.orchestrator import orchestrator
from core.permissions import permission_manager

# Módulos de ejecución que el motor de decisión necesita.
from agents.calendar_agent import calendar_agent
from agents.email_agent import email_agent
from agents.financial_agent import financial_agent
from agents.integrations_agent import integrations_agent
from agents.obsidian_agent import obsidian_agent
from agents.office_spotify_agent import office_spotify_agent
from agents.productivity_agent import productivity_agent
from agents.research_agent import research_agent
from agents.smart_home_agent import smart_home_agent
from agents.system_agent import system_agent
from agents.web_agent import web_agent
from automation.app_launcher import app_launcher
from automation.file_manager import file_manager
from automation.pc_controller import pc_controller
from automation.task_automation import task_automation
from automation.window_manager import window_manager
from integrations.weather_service import weather_service
from integrations.youtube_controller import youtube_controller

from voice.voice_pipeline import voice_pipeline
from api.server import app, ws_manager


def register_executors() -> None:
    """Registra todos los módulos ejecutables en el orquestador."""
    orchestrator.register_executors({
        "calendar_agent": calendar_agent,
        "app_launcher": app_launcher,
        "window_manager": window_manager,
        "file_manager": file_manager,
        "pc_controller": pc_controller,
        "task_automation": task_automation,
        "youtube_controller": youtube_controller,
        "weather_service": weather_service,
        "system_agent": system_agent,
        "research_agent": research_agent,
        "email_agent": email_agent,
        "productivity_agent": productivity_agent,
        "financial_agent": financial_agent,
        "smart_home_agent": smart_home_agent,
        "web_agent": web_agent,
        "office_spotify_agent": office_spotify_agent,
        "integrations_agent": integrations_agent,
        "obsidian_agent": obsidian_agent,
    })
    log.info("Módulos de ejecución registrados.")


def wire_web_events() -> None:
    """Conecta el pipeline de voz y las confirmaciones de riesgo a la web.

    `ws_manager.broadcast_threadsafe` es seguro de llamar desde cualquier
    hilo/loop, así que estos callbacks funcionan tanto si el turno viene de
    la wake word (loop de fondo) como de un mensaje de texto de la propia web
    (loop de uvicorn).
    """
    voice_pipeline.on_text(
        lambda role, text: ws_manager.broadcast_threadsafe(
            {"type": "message", "role": role, "text": text}
        )
    )
    voice_pipeline.on_state_change(
        lambda state: ws_manager.broadcast_threadsafe(
            {"type": "state", "state": state.value}
        )
    )
    async def confirm_action(description, risk):
        if voice_pipeline.voice_turn:
            return await voice_pipeline.request_voice_confirmation(description, risk)
        return await ws_manager.request_confirmation(description, risk)
    permission_manager.set_confirmation_callback(confirm_action)


def start_voice_loop() -> asyncio.AbstractEventLoop:
    """Crea un event loop en un hilo separado y arranca el pipeline de voz."""
    loop = asyncio.new_event_loop()

    def _run() -> None:
        asyncio.set_event_loop(loop)
        loop.create_task(voice_pipeline.run())
        loop.run_forever()

    thread = threading.Thread(target=_run, daemon=True, name="yu-voice-loop")
    thread.start()
    return loop


def main() -> int:
    """Función principal."""
    import os  # noqa: PLC0415
    import uvicorn  # noqa: PLC0415

    port = int(os.environ.get("YU_PORT", "8000"))
    log.info("==== Iniciando {} ====", settings.assistant_name)

    if settings.ai_provider == "ollama":
        log.info("Proveedor local Ollama: {} ({})", settings.ollama_model, settings.ollama_base_url)
    elif not settings.openai_api_key and not settings.gemini_api_key:
        log.warning("Ni OPENAI_API_KEY ni GEMINI_API_KEY configuradas: las funciones de IA fallarán.")
    if settings.tts_provider == "piper" or not settings.elevenlabs_api_key:
        log.info("YU usará el TTS offline (Piper).")

    register_executors()
    wire_web_events()
    voice_loop = start_voice_loop()

    log.info("Interfaz web disponible en http://localhost:{}", port)
    try:
        uvicorn.run(app, host="0.0.0.0", port=port)
    finally:
        log.info("Cerrando {}...", settings.assistant_name)
        voice_pipeline.stop()
        voice_loop.call_soon_threadsafe(voice_loop.stop)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
