"""Síntesis de voz (TTS) con ElevenLabs.

Incluye caché de audios recientes y cola de reproducción asíncrona.
El audio se solicita en formato PCM 44100 Hz (sin cabecera MP3 ni container)
y se envuelve en WAV para soundfile, o se reproduce directamente en streaming
via sounddevice.RawOutputStream para latencia mínima.
"""
from __future__ import annotations

import asyncio
import hashlib
import queue
import threading
import wave
from collections import OrderedDict
from pathlib import Path

import httpx
import numpy as np

from config.settings import settings
from core.logger import log

try:
    import sounddevice as sd
    import soundfile as sf
except Exception:  # noqa: BLE001
    sd = None  # type: ignore
    sf = None  # type: ignore

_ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
_ELEVEN_STREAM_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
_PCM_SAMPLE_RATE = 44100   # Hz de la petición pcm_44100 a ElevenLabs
_PCM_CHANNELS = 1           # mono
_PCM_SAMPWIDTH = 2          # 16-bit → 2 bytes por muestra


def _pcm_to_wav(pcm_data: bytes, out_path: Path, sample_rate: int = _PCM_SAMPLE_RATE) -> None:
    """Envuelve PCM 16-bit mono en un contenedor WAV estándar."""
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(_PCM_CHANNELS)
        wf.setsampwidth(_PCM_SAMPWIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)


class TextToSpeech:
    """Convierte texto en voz y lo reproduce."""

    def __init__(self) -> None:
        self.voice_id = settings.voice_id
        self.api_key = settings.elevenlabs_api_key
        self.model_id = settings.elevenlabs_model
        self.cache_dir: Path = settings.cache_dir / "tts"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache: "OrderedDict[str, Path]" = OrderedDict()
        self._cache_size = 50
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------ #
    # Generación de audio
    # ------------------------------------------------------------------ #
    async def _synthesize(self, text: str) -> Path | None:
        """Genera el audio (WAV 44100 Hz) y lo guarda en caché. Devuelve la ruta.

        Se solicita formato PCM sin cabecera a ElevenLabs y se convierte a WAV
        en local para que soundfile pueda reproducirlo sin depender de ffmpeg.
        """
        key = self._key(text)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]

        if not self.api_key:
            log.warning("ELEVENLABS_API_KEY no configurada; TTS deshabilitado.")
            return None

        out_path = self.cache_dir / f"{key}.wav"
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
        url = _ELEVEN_URL.format(voice_id=self.voice_id)

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    params={"output_format": "pcm_44100"},
                )
                resp.raise_for_status()
                # Convierte PCM crudo → WAV con cabecera estándar.
                await asyncio.to_thread(_pcm_to_wav, resp.content, out_path)
            self._cache[key] = out_path
            self._cache.move_to_end(key)
            while len(self._cache) > self._cache_size:
                old_key, old_path = self._cache.popitem(last=False)
                try:
                    old_path.unlink(missing_ok=True)
                except Exception:  # noqa: BLE001
                    pass
            return out_path
        except Exception as exc:  # noqa: BLE001
            log.error("Error sintetizando voz: {}", exc)
            return None

    async def _play(self, path: Path) -> None:
        """Reproduce un archivo WAV de forma bloqueante (en thread)."""
        if sd is None or sf is None:
            log.warning("sounddevice/soundfile no instalados; no se reproduce audio.")
            return

        def _do_play() -> None:
            data, samplerate = sf.read(str(path), dtype="float32")
            sd.play(data, samplerate)
            sd.wait()

        await asyncio.to_thread(_do_play)

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    async def speak(self, text: str) -> None:
        """Sintetiza y reproduce el texto inmediatamente."""
        if not text.strip():
            return
        log.info("TTS: '{}'", text[:80])
        path = await self._synthesize(text)
        if path:
            await self._play(path)

    async def speak_streaming(self, text: str) -> None:
        """Síntesis y reproducción en streaming de baja latencia (~300 ms).

        Abre un ``sounddevice.RawOutputStream`` en un hilo separado y
        alimenta los chunks PCM que llegan de ElevenLabs conforme se reciben,
        reduciendo la latencia de ~2-3 s (descarga completa + play) a ~0.3 s.
        Cae automáticamente a ``speak()`` si sounddevice no está disponible.
        """
        if not text.strip():
            return
        if not self.api_key:
            log.warning("ELEVENLABS_API_KEY no configurada; TTS deshabilitado.")
            return
        if sd is None:
            log.warning("sounddevice no instalado; usando TTS sin streaming.")
            await self.speak(text)
            return

        log.info("TTS streaming: '{}'", text[:80])

        pcm_q: "queue.Queue[bytes | None]" = queue.Queue(maxsize=64)
        error_holder: list[Exception] = []

        def _player() -> None:
            """Hilo reproductor: extrae chunks de la cola y los envía al dispositivo."""
            try:
                with sd.RawOutputStream(
                    samplerate=_PCM_SAMPLE_RATE,
                    channels=_PCM_CHANNELS,
                    dtype="int16",
                ) as stream:
                    while True:
                        chunk = pcm_q.get()
                        if chunk is None:  # sentinel de fin
                            break
                        stream.write(chunk)
            except Exception as exc:  # noqa: BLE001
                error_holder.append(exc)

        player_thread = threading.Thread(target=_player, daemon=True, name="yu-tts-stream")
        player_thread.start()

        url = _ELEVEN_STREAM_URL.format(voice_id=self.voice_id)
        headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    "POST", url,
                    json=payload,
                    headers=headers,
                    params={"output_format": "pcm_44100"},
                ) as resp:
                    resp.raise_for_status()
                    async for chunk in resp.aiter_bytes(4096):
                        if chunk:
                            pcm_q.put(chunk)
        except Exception as exc:  # noqa: BLE001
            log.error("Error en TTS streaming: {}", exc)
        finally:
            pcm_q.put(None)  # indica al hilo que terminó la transmisión
            await asyncio.to_thread(player_thread.join, 15)

        if error_holder:
            log.error("Error en hilo reproductor TTS: {}", error_holder[0])

    async def enqueue(self, text: str) -> None:
        """Añade texto a la cola de reproducción."""
        await self._queue.put(text)
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._consume_queue())

    async def _consume_queue(self) -> None:
        """Reproduce los textos de la cola en orden."""
        while not self._queue.empty():
            text = await self._queue.get()
            await self.speak(text)
            self._queue.task_done()


text_to_speech = TextToSpeech()
