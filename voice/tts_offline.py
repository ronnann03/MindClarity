"""Síntesis de voz offline con Piper TTS.

Alternativa local a ElevenLabs para modo offline o cuando no hay API key
disponible. Piper es liviano, rápido (ONNX) y no requiere GPU ni compilar
nada — instala limpio con `pip install piper-tts`.

El modelo de voz (ej. "es_ES-carme-x_low") se descarga automáticamente la
primera vez y se cachea en `<cache_dir>/piper/`.
"""
from __future__ import annotations

import asyncio
from typing import Literal

import numpy as np

from config.settings import settings
from core.logger import log

try:
    import sounddevice as sd
    import soundfile as sf
except Exception:  # noqa: BLE001
    sd = None  # type: ignore
    sf = None  # type: ignore

_DEFAULT_SAMPLE_RATE = 22050


class PiperTTS:
    """Sintetizador Piper TTS (ligero y rápido)."""

    def __init__(self, voice: str = "es_ES-davefx-medium", device: str = "cpu") -> None:
        """Inicializa Piper.

        Args:
            voice: Nombre de voz de Piper (ej: es_ES-davefx-medium, es_ES-sharvard-medium).
            device: "cpu" o "cuda".
        """
        self.voice = voice
        self.device = device
        self.piper = None
        self.sample_rate = _DEFAULT_SAMPLE_RATE
        self._initialized = False
        self._init_piper()

    def _init_piper(self) -> None:
        """Descarga (si hace falta) y carga el modelo de Piper."""
        try:
            from piper import PiperVoice  # noqa: PLC0415
            from piper.download_voices import download_voice  # noqa: PLC0415

            download_dir = settings.cache_dir / "piper"
            download_dir.mkdir(parents=True, exist_ok=True)
            model_path = download_dir / f"{self.voice}.onnx"
            config_path = download_dir / f"{self.voice}.onnx.json"
            if not model_path.exists() or not config_path.exists():
                log.info("[piper] Descargando voz '{}' (primera vez)...", self.voice)
                download_voice(self.voice, download_dir)

            self.piper = PiperVoice.load(model_path, config_path, use_cuda=(self.device == "cuda"))
            self.sample_rate = self.piper.config.sample_rate
            self._initialized = True
            log.info("[piper] Modelo '{}' cargado ({} Hz)", self.voice, self.sample_rate)
        except ImportError:
            log.warning("[piper] piper-tts no instalado. Ejecuta: pip install piper-tts")
            self._initialized = False
        except Exception as exc:  # noqa: BLE001
            log.error("[piper] Error cargando Piper: {}", exc)
            self._initialized = False

    async def synthesize(self, text: str) -> bytes | None:
        """Genera audio PCM a partir de texto.

        Returns:
            Bytes PCM 16-bit mono a `self.sample_rate` Hz (o None si falla).
        """
        if not self._initialized or not self.piper:
            return None

        def _synth() -> bytes | None:
            chunks = [chunk.audio_int16_bytes for chunk in self.piper.synthesize(text)]
            return b"".join(chunks) if chunks else None

        try:
            # Piper corre de forma síncrona: se ejecuta en un thread para no
            # bloquear el event loop.
            return await asyncio.to_thread(_synth)
        except Exception as exc:  # noqa: BLE001
            log.error("[piper] Error sintetizando: {}", exc)
            return None


class OfflineTTS:
    """Router de TTS offline (Piper)."""

    def __init__(
        self,
        engine: Literal["piper"] = "piper",
        language: str = "es",
        device: str = "cpu",
    ) -> None:
        """Inicializa TTS offline.

        Args:
            engine: solo "piper" por ahora (se mantiene el parámetro por
                compatibilidad con quien instancie esta clase).
            language: código de idioma (es, en...).
            device: "cpu" o "cuda".
        """
        self.engine = engine
        self.language = language
        self.device = device
        voice = settings.piper_voice if language == "es" else "en_US-lessac-medium"
        self.piper: PiperTTS | None = PiperTTS(voice=voice, device=device)

    async def synthesize(self, text: str) -> bytes | None:
        """Sintetiza texto a audio PCM."""
        if self.piper:
            return await self.piper.synthesize(text)
        return None

    async def speak(self, text: str) -> None:
        """Sintetiza y reproduce el texto."""
        if not text.strip():
            return

        if sd is None or sf is None:
            log.warning("[offline_tts] sounddevice/soundfile no instalados")
            return

        audio_data = await self.synthesize(text)
        if not audio_data:
            log.warning("[offline_tts] No se pudo sintetizar")
            return

        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0
            sample_rate = self.piper.sample_rate if self.piper else _DEFAULT_SAMPLE_RATE

            def _play() -> None:
                sd.play(audio_float, samplerate=sample_rate)
                sd.wait()

            await asyncio.to_thread(_play)
            log.info("[offline_tts] Reproducido: '{}'", text[:50])
        except Exception as exc:  # noqa: BLE001
            log.error("[offline_tts] Error reproduciendo: {}", exc)
