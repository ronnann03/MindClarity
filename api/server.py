"""API REST + WebSocket de YU: backend de la interfaz web y del acceso remoto.

Sirve además la interfaz web estática (`ui_web/`), que reemplaza a la antigua
app de escritorio PyQt6. Un único proceso (ver el nuevo `main.py`) arranca este
servidor en el hilo principal y el pipeline de voz (wake word/mic) en un hilo
de fondo; `ConnectionManager` es el puente thread-safe entre ambos.

Inicia el servidor:
    python main.py

Accesible en: http://localhost:8000
Documentación: http://localhost:8000/docs
"""
from __future__ import annotations

import asyncio
from contextlib import suppress
import json
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config.constants import RiskLevel
from config.profiles import ProfileManager
from config.settings import BASE_DIR, settings
from core.logger import log
from core.orchestrator import orchestrator
from voice.voice_pipeline import voice_pipeline

WEB_DIR = BASE_DIR / "ui_web"


# ---------------------------------------------------------------------- #
# Puente thread-safe entre el loop de uvicorn y el loop del pipeline de voz
# ---------------------------------------------------------------------- #
class ConnectionManager:
    """Registro de conexiones WebSocket activas y canal de eventos push.

    El pipeline de voz puede correr en su propio event loop, en un hilo
    aparte (cuando reacciona a la wake word). Este manager permite empujar
    eventos a los clientes web desde cualquier hilo usando
    `run_coroutine_threadsafe` contra el loop de uvicorn.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._pending_confirmations: dict[str, asyncio.Future] = {}
        self._lock = threading.Lock()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Se llama una vez, al arrancar uvicorn, con su event loop."""
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def _broadcast(self, payload: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self._connections.discard(ws)

    def broadcast_threadsafe(self, payload: dict[str, Any]) -> None:
        """Llamable desde cualquier hilo (p.ej. el loop del pipeline de voz)."""
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(payload), self._loop)

    async def request_confirmation(self, description: str, risk: RiskLevel) -> bool:
        """Callback de `permission_manager`: pide confirmación a la(s) web(s)
        conectada(s) y espera la respuesta. Funciona sin importar en qué loop/
        hilo se ejecute (usa el loop actual para el Future).
        """
        confirmation_id = uuid.uuid4().hex
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        with self._lock:
            self._pending_confirmations[confirmation_id] = future
        self.broadcast_threadsafe(
            {
                "type": "confirmation",
                "id": confirmation_id,
                "description": description,
                "risk": risk.value,
            }
        )
        try:
            return await future
        finally:
            with self._lock:
                self._pending_confirmations.pop(confirmation_id, None)

    def resolve_confirmation(self, confirmation_id: str, granted: bool) -> bool:
        """Se llama desde el handler del WebSocket (loop de uvicorn)."""
        with self._lock:
            future = self._pending_confirmations.get(confirmation_id)
        if future is None or future.done():
            return False
        future.get_loop().call_soon_threadsafe(future.set_result, granted)
        return True


ws_manager = ConnectionManager()


# ---------------------------------------------------------------------- #
# Modelos
# ---------------------------------------------------------------------- #
class CommandRequest(BaseModel):
    """Solicitud de comando."""
    text: str
    user_id: str = "default"


class ResponseModel(BaseModel):
    """Respuesta de YU."""
    success: bool
    output: Any = None
    message: str = ""


class ProfileSelectRequest(BaseModel):
    """Selección de perfil desde la web."""
    name: str


class ProfileCreateRequest(BaseModel):
    """Creación de perfil desde la web."""
    name: str
    assistant_name: str = "YU"
    language: str = "auto"


# Crear app
app = FastAPI(
    title="YU API",
    description="API REST + WebSocket de YU - Asistente de IA",
    version="2.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _bind_ws_loop() -> None:
    """Registra el loop de uvicorn en cuanto arranca, para el puente thread-safe."""
    ws_manager.bind_loop(asyncio.get_running_loop())
    ProfileManager.ensure_default_profile()


# ---------------------------------------------------------------------- #
# Rutas
# ---------------------------------------------------------------------- #
@app.get("/favicon.ico")
async def favicon() -> Response:
    return Response(content=b"", media_type="image/x-icon")


@app.get("/health")
async def health() -> dict[str, str]:
    """Verifica el estado de YU."""
    return {"status": "ok", "message": "YU está funcionando"}


@app.post("/api/command")
async def execute_command(request: CommandRequest) -> ResponseModel:
    """Ejecuta un comando de texto (sin voz, sin push de eventos).

    Ejemplos:
    - {"text": "¿Qué tiempo hace?"}
    - {"text": "Abre Spotify"}
    - {"text": "Envía un mensaje a Juan"}
    """
    try:
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Comando vacío")

        log.info("[api] Comando recibido: {}", request.text)
        response = await orchestrator.process(request.text)

        return ResponseModel(
            success=True,
            message=response,
            output={"user_id": request.user_id, "command": request.text},
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        log.error("[api] Error procesando comando: {}", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/status")
async def get_status() -> dict[str, Any]:
    """Obtiene el estado actual de YU."""
    from voice.audio_capture import AUDIO_LEVEL
    return {
        "status": "active",
        "voice_state": voice_pipeline.state.value,
        "assistant_name": settings.assistant_name,
        "ai_provider": settings.ai_provider,
        "ai_model": settings.ollama_model if settings.ai_provider == "ollama" else settings.model_name,
        "voice_enabled": voice_pipeline._running,
        "wake_word": settings.wake_word,
        "voice_backend": settings.voice_backend,
        "activation_phrase": settings.wake_word + (' escucha' if settings.voice_backend == 'vosk' else ''),
        "voice_language": settings.voice_language,
        "microphone_level": dict(AUDIO_LEVEL),
        "voice_energy_threshold": settings.voice_energy_threshold,
    }


@app.get("/api/agents")
async def list_agents() -> dict[str, list[str]]:
    """Lista todos los agentes disponibles."""
    agents = list(orchestrator.engine._registry)
    return {"agents": agents}


@app.get("/api/profiles")
async def list_profiles() -> dict[str, Any]:
    """Lista los perfiles de usuario disponibles."""
    try:
        profiles = ProfileManager.list_profiles()
        return {"profiles": profiles}
    except Exception as exc:  # noqa: BLE001
        log.error("[api] Error listando perfiles: {}", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/profiles")
async def create_profile(request: ProfileCreateRequest) -> dict[str, Any]:
    """Crea un nuevo perfil de usuario."""
    try:
        profile = ProfileManager.create_profile(
            request.name,
            assistant_name=request.assistant_name,
            language=request.language,
        )
        return {"success": True, "profile": profile.to_dict()}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/profiles/select")
async def select_profile(request: ProfileSelectRequest) -> dict[str, Any]:
    """Aplica un perfil existente a la configuración global (settings)."""
    profile = ProfileManager.get_profile(request.name)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Perfil '{request.name}' no encontrado")

    settings.assistant_name = profile.assistant_name
    settings.voice_id = profile.voice_id
    settings.language = profile.language if profile.language in {'es', 'en'} else settings.voice_language  # type: ignore[assignment]
    settings.temperature = profile.temperature
    settings.user_name = profile.name if profile.name != 'Defecto' else settings.user_name
    log.info("[api] Perfil aplicado: {}", profile.name)
    return {"success": True, "profile": profile.to_dict()}


@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket bidireccional: comandos de texto + eventos push.

    Mensajes que acepta del cliente:
    - {"text": "..."}                                    -> procesa el comando
    - {"type": "confirmation_response", "id": ..., "granted": bool}

    Eventos que empuja al cliente:
    - {"type": "message", "role": "user"|"assistant", "text": "..."}
    - {"type": "state", "state": "idle"|"listening"|"processing"|"speaking"|"error"}
    - {"type": "confirmation", "id": ..., "description": ..., "risk": ...}
    """
    await ws_manager.connect(websocket)
    active_command: asyncio.Task | None = None
    try:
        while True:
            data = await websocket.receive_text()
            try:
                command = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "JSON inválido"})
                continue

            if not isinstance(command, dict):
                await websocket.send_json({"type": "error", "message": "Se esperaba un objeto JSON"})
                continue

            msg_type = command.get("type")
            if msg_type == "confirmation_response":
                ws_manager.resolve_confirmation(
                    command.get("id", ""), command.get("granted") is True
                )
                continue

            text = command.get("text", "")
            if not isinstance(text, str) or not text.strip() or len(text) > 8000:
                await websocket.send_json({"type": "error", "message": "Comando vacío"})
                continue

            if active_command is not None and not active_command.done():
                await websocket.send_json({"type": "error", "message": "YU está terminando la petición anterior"})
                continue

            # process_text_input ya emite los eventos "message"/"state" (y habla
            # la respuesta por TTS) a través de los callbacks del pipeline.
            # El receptor debe seguir leyendo la confirmación mientras se ejecuta
            # el comando; esperarlo aquí bloqueaba el modal de la misma conexión.
            active_command = asyncio.create_task(voice_pipeline.process_text_input(text))
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        log.error("[api] Error en WebSocket: {}", exc)
    finally:
        if active_command is not None:
            if not active_command.done():
                active_command.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await active_command
        ws_manager.disconnect(websocket)


# Sirve la interfaz web estática. Debe ir AL FINAL: al montar "/" como
# catch-all, cualquier ruta específica declarada después de esto quedaría
# eclipsada por los archivos estáticos.
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


if __name__ == "__main__":
    import uvicorn  # noqa: PLC0415

    uvicorn.run(app, host="0.0.0.0", port=8000)
