"""Pipeline de voz completo: wake word -> STT -> orquestador -> TTS.

Gestiona los estados IDLE, LISTENING, PROCESSING, SPEAKING y notifica cambios
a la UI mediante callbacks opcionales.
"""
from __future__ import annotations

import asyncio
import re
import threading
from typing import Awaitable, Callable, Optional

from config.constants import VoiceState
from core.logger import log
from core.orchestrator import Orchestrator, orchestrator
from voice.speech_to_text import SpeechToText, speech_to_text
from voice.tts_router import TTSRouter, tts_router
from voice.wake_word import WakeWordDetector, wake_word_detector

# Callbacks que la UI puede registrar.
StateCallback = Callable[[VoiceState], None]
TextCallback = Callable[[str, str], None]  # (rol, texto)


class VoicePipeline:
    """Bucle de voz asíncrono que une todos los componentes."""

    def __init__(
        self,
        wake: WakeWordDetector | None = None,
        stt: SpeechToText | None = None,
        tts: TTSRouter | None = None,
        brain: Orchestrator | None = None,
    ) -> None:
        self.wake = wake or wake_word_detector
        self.stt = stt or speech_to_text
        self.tts = tts or tts_router
        self.brain = brain or orchestrator
        self.state: VoiceState = VoiceState.IDLE
        self._running = False
        self._on_state: Optional[StateCallback] = None
        self._on_text: Optional[TextCallback] = None
        self._turn_lock = threading.Lock()
        self.voice_turn = False
        self.wake.can_listen = lambda: self.state == VoiceState.IDLE

    # ------------------------------------------------------------------ #
    # Callbacks de UI
    # ------------------------------------------------------------------ #
    def on_state_change(self, callback: StateCallback) -> None:
        self._on_state = callback

    def on_text(self, callback: TextCallback) -> None:
        self._on_text = callback

    def _set_state(self, state: VoiceState) -> None:
        self.state = state
        log.debug("Estado de voz: {}", state.value)
        if self._on_state:
            try:
                self._on_state(state)
            except Exception as exc:  # noqa: BLE001
                log.error("Error en callback de estado: {}", exc)

    def _emit_text(self, role: str, text: str) -> None:
        if self._on_text and text:
            try:
                self._on_text(role, text)
            except Exception as exc:  # noqa: BLE001
                log.error("Error en callback de texto: {}", exc)

    # ------------------------------------------------------------------ #
    # Ciclo de un turno completo
    # ------------------------------------------------------------------ #
    async def handle_interaction(self, initial_text: str | None = None) -> None:
        """Ejecuta un turno: escuchar -> procesar -> hablar."""
        if not self._turn_lock.acquire(blocking=False):
            return
        self.voice_turn = True
        try:
            # 1) Escuchar y transcribir.
            self._set_state(VoiceState.LISTENING)
            pending = initial_text if initial_text is not None else getattr(self.wake, 'pending_text', '')
            self.wake.pending_text = ''
            if isinstance(pending, str) and pending.strip():
                user_text = pending.strip()
            else:
                await self.tts.speak_streaming("Te escucho.")
                user_text = await self.stt.listen_and_transcribe()
            if not user_text:
                self._set_state(VoiceState.IDLE)
                return
            self._emit_text("user", user_text)

            # 2) Procesar con el orquestador.
            self._set_state(VoiceState.PROCESSING)
            response = await self.brain.process(user_text)
            self._emit_text("assistant", response)

            # 3) Responder por voz (streaming para menor latencia).
            self._set_state(VoiceState.SPEAKING)
            await self.tts.speak_streaming(response)
        except Exception as exc:  # noqa: BLE001
            log.error("Error en interacción de voz: {}", exc)
            self._set_state(VoiceState.ERROR)
        finally:
            self.voice_turn = False
            self._set_state(VoiceState.IDLE)
            self._turn_lock.release()

    async def process_text_input(self, text: str) -> str:
        """Procesa una entrada de texto (desde la UI) y la habla."""
        if not self._turn_lock.acquire(blocking=False):
            message = "Estoy atendiendo otra petición. Inténtalo en un momento."
            self._emit_text("assistant", message)
            return message
        self._emit_text("user", text)
        try:
            self._set_state(VoiceState.PROCESSING)
            response = await self.brain.process(text)
            self._emit_text("assistant", response)
            self._set_state(VoiceState.SPEAKING)
            await self.tts.speak_streaming(response)
            return response
        except Exception as exc:  # noqa: BLE001
            log.error("Error procesando entrada de texto: {}", exc)
            self._set_state(VoiceState.ERROR)
            return "Lo siento, ocurrió un error al procesar tu mensaje."
        finally:
            self._set_state(VoiceState.IDLE)
            self._turn_lock.release()

    async def request_voice_confirmation(self, description: str, risk) -> bool:
        prompt = (f"Necesito tu autorización para: {description}. "
                  "Di exactamente: confirmar acción. Para rechazarla, di: cancelar acción.")
        self._emit_text('assistant', prompt)
        self._set_state(VoiceState.SPEAKING)
        await self.tts.speak_streaming(prompt)
        self._set_state(VoiceState.LISTENING)
        try:
            reply = await asyncio.wait_for(self.stt.listen_and_transcribe(), timeout=25)
        except Exception as exc:
            log.warning("No se recibió confirmación por voz: {}", type(exc).__name__)
            return False
        normalized = re.sub(r'[^a-záéíóúñ ]', '', reply.lower()).strip()
        self._emit_text('user', reply)
        self._set_state(VoiceState.PROCESSING)
        return normalized in {'confirmar acción', 'confirmar accion'}

    # ------------------------------------------------------------------ #
    # Bucle principal
    # ------------------------------------------------------------------ #
    async def run(self) -> None:
        """Bucle infinito: espera la wake word y atiende cada interacción."""
        self._running = True
        await self.brain.initialize()
        log.info("Pipeline de voz arrancado. Esperando wake word...")
        self._set_state(VoiceState.IDLE)

        async def _on_detected() -> None:
            await self.handle_interaction()
            self._set_state(VoiceState.IDLE)

        try:
            while self._running:
                try:
                    await self.wake.run_forever(_on_detected)
                    if self._running:
                        await asyncio.sleep(1)
                except Exception as exc:
                    log.error("Micrófono no disponible; reintentando: {}", exc)
                    self._set_state(VoiceState.ERROR)
                    await asyncio.sleep(3)
                    self._set_state(VoiceState.IDLE)
        except asyncio.CancelledError:
            log.info("Pipeline de voz detenido.")
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False
        self.wake.stop()
        from voice.audio_service import audio_service
        audio_service.stop()
        from voice.audio_capture import close_microphone
        close_microphone()


voice_pipeline = VoicePipeline()
