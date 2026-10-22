"""La configuración local de voz debe evitar ElevenLabs aunque exista clave."""
from config.settings import settings
from voice.tts_router import TTSRouter


def test_piper_selection_disables_cloud_voice(monkeypatch):
    monkeypatch.setattr(settings, "tts_provider", "piper")
    monkeypatch.setattr(settings, "elevenlabs_api_key", "test-key-not-used")
    monkeypatch.setattr(TTSRouter, "_init_offline", lambda self: None)
    router = TTSRouter()
    assert router.elevenlabs_available is False
    assert router._get_preferred_engine() == "none"
