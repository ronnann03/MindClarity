"""Router de TTS que elige automáticamente entre ElevenLabs o Piper.

Prioridad:
1. ElevenLabs (si hay API key y conexión)
2. Piper (offline, ligero)
3. Fallback a texto sin voz
"""
from __future__ import annotations

from typing import Literal

from config.settings import settings
from core.logger import log
from voice.text_to_speech import text_to_speech
from voice.tts_offline import OfflineTTS


class TTSRouter:
    """Router inteligente de TTS con fallbacks automáticos."""

    def __init__(self) -> None:
        self.elevenlabs_available = settings.tts_provider != "piper" and bool(settings.elevenlabs_api_key)
        self.piper_tts: OfflineTTS | None = None
        self._init_offline()

    def _init_offline(self) -> None:
        """Inicializa el motor offline (Piper) si está disponible."""
        try:
            self.piper_tts = OfflineTTS(engine="piper", language="es", device="cpu")
            if self.piper_tts.piper and self.piper_tts.piper._initialized:
                log.info("[tts_router] Piper TTS disponible")
            else:
                self.piper_tts = None
        except Exception as exc:  # noqa: BLE001
            log.debug("[tts_router] Piper no disponible: {}", exc)
            self.piper_tts = None

    def _get_preferred_engine(self) -> Literal["elevenlabs", "piper", "none"]:
        """Elige el mejor motor TTS disponible."""
        if self.elevenlabs_available:
            return "elevenlabs"
        if self.piper_tts:
            return "piper"
        return "none"

    async def speak(self, text: str) -> None:
        """Sintetiza y reproduce texto usando el mejor motor disponible."""
        if not text.strip():
            return

        engine = self._get_preferred_engine()

        match engine:
            case "elevenlabs":
                log.debug("[tts_router] Usando ElevenLabs")
                try:
                    await text_to_speech.speak_streaming(text)
                except Exception as exc:  # noqa: BLE001
                    log.warning("[tts_router] ElevenLabs falló: {}, usando Piper", exc)
                    if self.piper_tts:
                        await self.piper_tts.speak(text)

            case "piper":
                log.debug("[tts_router] Usando Piper TTS")
                await self.piper_tts.speak(text)

            case _:
                log.warning("[tts_router] Sin motor TTS disponible")

    async def speak_streaming(self, text: str) -> None:
        """Sintetiza en streaming (solo ElevenLabs lo soporta)."""
        if not text.strip():
            return

        if self.elevenlabs_available:
            await text_to_speech.speak_streaming(text)
        else:
            # Fallback a reproducción normal
            await self.speak(text)

    async def enqueue(self, text: str) -> None:
        """Añade texto a la cola de reproducción."""
        if self.elevenlabs_available:
            await text_to_speech.enqueue(text)
        else:
            # Sin cola para offline, reproduce inmediatamente
            await self.speak(text)

    def get_engine_info(self) -> dict[str, bool]:
        """Devuelve información sobre qué motores están disponibles."""
        return {
            "elevenlabs": self.elevenlabs_available,
            "piper": self.piper_tts is not None,
        }


tts_router = TTSRouter()
