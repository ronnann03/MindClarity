"""Configuración central de YU usando Pydantic Settings.

Lee variables desde el archivo .env y expone una instancia singleton `settings`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Raíz del proyecto (carpeta que contiene este archivo -> ../)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Modelo de configuración de la aplicación.

    Todos los valores pueden sobreescribirse mediante variables de entorno
    o un archivo .env situado en la raíz del proyecto.
    """

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # Claves de APIs externas
    # ------------------------------------------------------------------ #
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    elevenlabs_api_key: str = Field(default="", alias="ELEVENLABS_API_KEY")
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_key: str = Field(default="", alias="SUPABASE_KEY")
    openweather_api_key: str = Field(default="", alias="OPENWEATHER_API_KEY")
    obsidian_vault_path: str = Field(default="", alias="OBSIDIAN_VAULT_PATH")

    # ------------------------------------------------------------------ #
    # Modelos de IA
    # ------------------------------------------------------------------ #
    ai_provider: Literal["ollama", "auto"] = Field(default="ollama", alias="AI_PROVIDER")
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5:3b", alias="OLLAMA_MODEL")
    ollama_timeout: float = Field(default=180.0, gt=0, alias="OLLAMA_TIMEOUT")
    model_name: str = Field(default="gpt-4o", alias="MODEL_NAME")
    embedding_model: str = Field(
        default="text-embedding-3-small", alias="EMBEDDING_MODEL"
    )
    gemini_model_name: str = Field(default="gemini-3.6-flash", alias="GEMINI_MODEL_NAME")
    temperature: float = Field(default=0.7, alias="TEMPERATURE")
    max_tokens: int = Field(default=1024, alias="MAX_TOKENS")

    # ------------------------------------------------------------------ #
    # Voz
    # ------------------------------------------------------------------ #
    tts_provider: Literal["auto", "piper"] = Field(default="auto", alias="TTS_PROVIDER")
    voice_id: str = Field(default="EXAVITQu4vr4xnSDxMaL", alias="VOICE_ID")
    elevenlabs_model: str = Field(
        default="eleven_multilingual_v2", alias="ELEVENLABS_MODEL"
    )
    piper_voice: str = Field(default="es_ES-davefx-medium", alias="PIPER_VOICE")
    wake_word: str = Field(default="yu", alias="WAKE_WORD")
    voice_backend: Literal["whisper", "vosk"] = Field(default="whisper", alias="VOICE_BACKEND")
    vosk_model_path: str = Field(default=".cache/vosk/vosk-model-small-es-0.42", alias="VOSK_MODEL_PATH")
    voice_input_device: int | None = Field(default=None, alias="VOICE_INPUT_DEVICE")
    voice_input_hostapi: str = Field(default="", alias="VOICE_INPUT_HOSTAPI")
    wake_word_model_path: str = Field(
        default="",
        alias="WAKE_WORD_MODEL_PATH",
        description="Ruta a un archivo .onnx de openWakeWord para la wake word personalizada.",
    )
    whisper_model_size: str = Field(default="medium", alias="WHISPER_MODEL_SIZE")
    whisper_device: str = Field(default="cpu", alias="WHISPER_DEVICE")
    whisper_compute_type: str = Field(
        default="int8", alias="WHISPER_COMPUTE_TYPE"
    )
    language: Literal["es", "en", "auto"] = Field(default="auto", alias="LANGUAGE")
    sample_rate: int = Field(default=16000, alias="SAMPLE_RATE")
    record_seconds: int = Field(default=8, alias="RECORD_SECONDS")
    voice_language: Literal["es", "en", "auto"] = Field(default="es", alias="VOICE_LANGUAGE")
    voice_energy_threshold: float = Field(default=0.002, gt=0, alias="VOICE_ENERGY_THRESHOLD")
    voice_silence_seconds: float = Field(default=0.8, gt=0, alias="VOICE_SILENCE_SECONDS")
    voice_start_timeout: float = Field(default=6.0, gt=0, alias="VOICE_START_TIMEOUT")
    voice_max_seconds: float = Field(default=15.0, gt=0, alias="VOICE_MAX_SECONDS")

    # ------------------------------------------------------------------ #
    # Memoria / contexto
    # ------------------------------------------------------------------ #
    max_context_tokens: int = Field(default=6000, alias="MAX_CONTEXT_TOKENS")
    short_term_size: int = Field(default=20, alias="SHORT_TERM_SIZE")
    memory_similarity_threshold: float = Field(
        default=0.75, alias="MEMORY_SIMILARITY_THRESHOLD"
    )

    # ------------------------------------------------------------------ #
    # Comportamiento / seguridad
    # ------------------------------------------------------------------ #
    require_confirmation_high_risk: bool = Field(
        default=True, alias="REQUIRE_CONFIRMATION_HIGH_RISK"
    )
    assistant_name: str = Field(default="YU", alias="ASSISTANT_NAME")
    user_name: str = Field(default="Señor", alias="USER_NAME")

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_dir: Path = Field(default=BASE_DIR / "logs", alias="LOG_DIR")

    # ------------------------------------------------------------------ #
    # Rutas útiles
    # ------------------------------------------------------------------ #
    base_dir: Path = BASE_DIR
    cache_dir: Path = Field(default=BASE_DIR / ".cache", alias="CACHE_DIR")

    def ensure_dirs(self) -> None:
        """Crea los directorios necesarios si no existen."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la instancia singleton de configuración."""
    s = Settings()
    s.ensure_dirs()
    return s


# Instancia global de configuración
settings: Settings = get_settings()
