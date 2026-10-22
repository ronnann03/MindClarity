"""Detección de wake word con soporte dual:

1. **openWakeWord** (preferido) — modelo ONNX dedicado, baja CPU, alta precisión.
   Requiere ``pip install openwakeword`` y un archivo ``.onnx`` configurado en
   ``WAKE_WORD_MODEL_PATH`` dentro de ``.env``.

2. **Energía + Whisper** (fallback) — sin modelo extra, funciona desde el primer
   arranque pero usa más CPU porque confirma cada pico de energía con Whisper.

El detector usa openWakeWord automáticamente si el modelo existe y la librería
está disponible; en caso contrario cae al método de energía+Whisper.
"""
from __future__ import annotations

import asyncio
import re
from collections import deque
from typing import Awaitable, Callable

import numpy as np

from config.settings import settings
from core.logger import log
from voice.speech_to_text import SpeechToText, speech_to_text

try:
    import sounddevice as sd
except Exception:  # noqa: BLE001
    sd = None  # type: ignore

try:
    from openwakeword.model import Model as _OWWModel  # type: ignore
    _OWW_AVAILABLE = True
except ImportError:
    _OWW_AVAILABLE = False

# ------------------------------------------------------------------ #
# Configuración de openWakeWord                                        #
# ------------------------------------------------------------------ #
# Para entrenar tu propio modelo "yu" consulta:
# https://github.com/dscripka/openWakeWord#training-new-models
# Luego pon la ruta en .env:  WAKE_WORD_MODEL_PATH=./models/yu.onnx
_OWW_MODEL_PATH: str = getattr(settings, "wake_word_model_path", "")
_OWW_THRESHOLD: float = 0.5       # probabilidad mínima para activar
_OWW_CHUNK_MS: int = 80           # milisegundos por bloque (estándar openWakeWord)
_OWW_SAMPLE_RATE: int = 16_000   # Hz que acepta openWakeWord


class WakeWordDetector:
    """Detecta la palabra de activación en un flujo de audio continuo."""

    def __init__(
        self,
        stt: SpeechToText | None = None,
        energy_threshold: float = 0.02,
    ) -> None:
        self.stt = stt or speech_to_text
        self.wake_word = settings.wake_word.lower().strip()
        self.sample_rate = settings.sample_rate
        self.energy_threshold = energy_threshold
        self._running = False
        self._force_stop = False
        # Variantes que Whisper puede transcribir de forma aproximada.
        self._variants = {self.wake_word, "yu", "iu", "hiu"}
        self.pending_text = ""
        self.can_listen = lambda: True

        # Determinar qué backend usar
        self._use_oww = _OWW_AVAILABLE and bool(_OWW_MODEL_PATH)
        if self._use_oww:
            try:
                self._oww = _OWWModel(
                    wakeword_models=[_OWW_MODEL_PATH],
                    inference_framework="onnx",
                )
                log.info("openWakeWord cargado desde '{}'.", _OWW_MODEL_PATH)
            except Exception as exc:  # noqa: BLE001
                log.warning("No se pudo cargar openWakeWord ({}); usando energía+Whisper.", exc)
                self._use_oww = False
        else:
            if _OWW_AVAILABLE and not _OWW_MODEL_PATH:
                log.info(
                    "openWakeWord instalado pero sin modelo configurado "
                    "(WAKE_WORD_MODEL_PATH). Usando energía+Whisper."
                )

    # ------------------------------------------------------------------ #
    # Backend 1: openWakeWord
    # ------------------------------------------------------------------ #
    async def _listen_oww(self, timeout: float = 3600.0) -> bool:
        """Escucha con openWakeWord hasta detectar la wake word o timeout."""
        if sd is None:
            raise RuntimeError("sounddevice no está instalado.")

        chunk_size = int(_OWW_SAMPLE_RATE * _OWW_CHUNK_MS / 1000)  # ~1280 muestras
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout

        log.debug("openWakeWord escuchando '{}'...", self.wake_word)
        while loop.time() < deadline and not self._force_stop:
            if not self.can_listen():
                await asyncio.sleep(0.2)
                continue

            def _read() -> np.ndarray:
                audio = sd.rec(
                    chunk_size, samplerate=_OWW_SAMPLE_RATE,
                    channels=1, dtype="int16",
                )
                sd.wait()
                return audio.flatten()

            chunk = await asyncio.to_thread(_read)

            def _predict(arr: np.ndarray) -> dict:
                return self._oww.predict(arr)

            scores: dict = await asyncio.to_thread(_predict, chunk)
            # scores es {model_name: probability}
            if any(v >= _OWW_THRESHOLD for v in scores.values()):
                log.info("Wake word detectada por openWakeWord (scores={}).", scores)
                return True

        return False

    # ------------------------------------------------------------------ #
    # Backend 2: Energía + Whisper
    # ------------------------------------------------------------------ #
    @staticmethod
    def _rms(block: np.ndarray) -> float:
        return float(np.sqrt(np.mean(np.square(block)))) if block.size else 0.0

    def _matches(self, text: str) -> bool:
        return self.extract_command(text) is not None

    def extract_command(self, text: str) -> str | None:
        words = '|'.join(re.escape(v) for v in self._variants | {'yú'})
        # La activación debe ser la primera palabra, nunca una mención interna.
        match = re.match(rf'^\s*[¿¡]?(?:{words})\b[\s,.!?¿¡:;-]*(.*)$', text, re.IGNORECASE)
        if not match:
            return None
        command = match.group(1).strip()
        # Una misma captura puede incluir varios intentos del usuario.
        # Solo colapsar repeticiones idénticas; conservar peticiones distintas.
        parts = re.split(rf'[.!?]+\s*(?:(?:oye|hola|hey)\s*[,.:]?\s*)?(?:{words})\b[\s,.!?¿¡:;-]*', command, flags=re.IGNORECASE)
        normalize = lambda value: re.sub(r'\s+', ' ', value.strip().rstrip('.!?').strip()).casefold()
        if len(parts) > 1 and normalize(parts[0]) and all(normalize(p) == normalize(parts[0]) for p in parts):
            return parts[0].strip().rstrip('.!?').strip()
        return command

    async def _listen_energy(self, timeout: float = 3600.0) -> bool:
        """Escucha por energía y verifica con Whisper."""
        deadline = asyncio.get_running_loop().time() + timeout
        while not self._force_stop and asyncio.get_running_loop().time() < deadline:
            if not self.can_listen():
                await asyncio.sleep(0.2)
                continue
            audio = await self.stt.record_audio(start_timeout=min(60.0, max(0.2, deadline - asyncio.get_running_loop().time())),
                should_stop=lambda: self._force_stop or not self.can_listen())
            if not audio.size or not self.can_listen():
                continue
            text = await self.stt.transcribe(audio)
            if not self.can_listen():
                continue
            command = self.extract_command(text)
            if command is not None:
                self.pending_text = command
                log.info("Activación reconocida; orden incluida={}", bool(command))
                return True
        return False

    async def listen_once(self, timeout: float = 3600.0) -> bool:
        """Escucha hasta detectar la wake word o agotar el timeout."""
        if settings.voice_backend == 'vosk':
            from voice.audio_service import audio_service
            if not self.can_listen():
                await asyncio.sleep(.2)
                return False
            detected = await audio_service.listen('wake', timeout=timeout,
                should_stop=lambda: self._force_stop or not self.can_listen())
            if detected and self.can_listen():
                self.pending_text = ''
                log.info('Activación Vosk «YU escucha» reconocida')
                return True
            return False
        if self._use_oww:
            return await self._listen_oww(timeout)
        return await self._listen_energy(timeout)

    async def run_forever(
        self,
        on_detected: Callable[[], Awaitable[None] | None],
    ) -> None:
        """Loop infinito; invoca ``on_detected`` (corrutina) en cada detección."""
        self._running = True
        self._force_stop = False
        backend = 'Vosk: YU escucha' if settings.voice_backend == 'vosk' else ("openWakeWord" if self._use_oww else "energía+Whisper")
        log.info("Detector de wake word iniciado (backend={}).", backend)
        try:
            while self._running:
                detected = await self.listen_once(timeout=3600)
                if detected and self._running:
                    result = on_detected()
                    if asyncio.iscoroutine(result):
                        await result
        except asyncio.CancelledError:
            log.info("Detector de wake word cancelado.")
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False
        self._force_stop = True


wake_word_detector = WakeWordDetector()
