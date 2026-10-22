"""Reconocimiento de voz (STT) con faster-whisper.

Graba audio del micrófono y lo transcribe con detección automática de idioma
y VAD (Voice Activity Detection).
"""
from __future__ import annotations

import asyncio
import os
import io
import wave
import threading
from typing import Optional

import numpy as np

from config.settings import settings
from core.logger import log

try:
    import sounddevice as sd
except Exception:  # noqa: BLE001
    sd = None  # type: ignore

try:
    from faster_whisper import WhisperModel
except Exception:  # noqa: BLE001
    WhisperModel = None  # type: ignore


class SpeechToText:
    """Transcribe audio a texto usando faster-whisper."""

    def __init__(self) -> None:
        self._model: Optional["WhisperModel"] = None
        self.sample_rate = settings.sample_rate
        self._model_lock = threading.Lock()

    def _ensure_model(self) -> "WhisperModel":
        """Carga perezosa del modelo Whisper."""
        if self._model is None:
            if WhisperModel is None:
                raise RuntimeError("faster-whisper no está instalado.")
            log.info("Cargando modelo Whisper '{}'...", settings.whisper_model_size)
            self._model = WhisperModel(
                settings.whisper_model_size,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
                cpu_threads=4,
                num_workers=1,
            )
            log.info("Modelo Whisper cargado.")
        return self._model

    # ------------------------------------------------------------------ #
    # Grabación
    # ------------------------------------------------------------------ #
    async def record_audio(self, seconds: int | None = None, *, start_timeout: float | None = None,
                           should_stop=None) -> np.ndarray:
        """Graba audio del micrófono y devuelve un array float32 mono."""
        if sd is None:
            raise RuntimeError("sounddevice no está instalado.")
        from voice.audio_capture import capture_utterance, close_microphone
        try:
            return await asyncio.to_thread(capture_utterance, sample_rate=self.sample_rate,
                threshold=settings.voice_energy_threshold, silence_seconds=settings.voice_silence_seconds,
                start_timeout=start_timeout or settings.voice_start_timeout,
                max_seconds=seconds or settings.voice_max_seconds, should_stop=should_stop)
        except Exception:
            close_microphone()
            raise

    # ------------------------------------------------------------------ #
    # Transcripción
    # ------------------------------------------------------------------ #
    def _to_float_array(self, audio_data: bytes | np.ndarray) -> np.ndarray:
        """Convierte la entrada a un array float32 normalizado."""
        if isinstance(audio_data, np.ndarray):
            return audio_data.astype(np.float32)
        # Asume PCM 16-bit WAV en bytes.
        try:
            with wave.open(io.BytesIO(audio_data), "rb") as wf:
                frames = wf.readframes(wf.getnframes())
            samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
            return samples / 32768.0
        except Exception:
            samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            return samples / 32768.0

    async def transcribe(self, audio_data: bytes | np.ndarray) -> str:
        """Transcribe audio a texto."""
        audio = self._to_float_array(audio_data)
        if not audio.size or float(np.sqrt(np.mean(audio ** 2))) < settings.voice_energy_threshold / 4:
            return ""
        # La señal del micrófono de este equipo es baja; ajusta amplitud sin
        # amplificar silencio ni recortar picos de una señal ya normalizada.
        peak = float(np.max(np.abs(audio)))
        if 0 < peak < 0.1:
            audio = audio * min(12.0, 0.3 / peak)

        def _transcribe() -> str:
            language = None if settings.voice_language == "auto" else settings.voice_language
            with self._model_lock:
                model = self._ensure_model()
                segments, info = model.transcribe(audio, language=language,
                    initial_prompt="Conversación en español con YU. Nombre del usuario: " + settings.user_name,
                    vad_filter=True, vad_parameters={"min_silence_duration_ms": 500}, beam_size=3,
                    condition_on_previous_text=False)
                text = " ".join(seg.text for seg in segments if getattr(seg, 'no_speech_prob', 0) < 0.65).strip()
            log.info("Transcripción ({}): '{}'", getattr(info, "language", "?"), text)
            return text

        try:
            return await asyncio.to_thread(_transcribe)
        except Exception as exc:  # noqa: BLE001
            log.error("Error en transcripción: {}", exc)
            return ""

    async def listen_and_transcribe(self, seconds: int | None = None) -> str:
        """Graba y transcribe en un solo paso."""
        if settings.voice_backend == 'vosk' and not os.environ.get('YU_AUDIO_WORKER'):
            from voice.audio_service import audio_service
            return await audio_service.listen('command', timeout=seconds or settings.voice_start_timeout + settings.voice_max_seconds)
        audio = await self.record_audio(seconds)
        return await self.transcribe(audio)


speech_to_text = SpeechToText()
