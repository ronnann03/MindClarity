"""Tests del VoicePipeline: máquina de estados, callbacks y manejo de errores."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.constants import VoiceState
from voice.voice_pipeline import VoicePipeline


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def pipeline() -> VoicePipeline:
    """Pipeline con todos los subsistemas mockeados."""
    wake = MagicMock()
    wake.run_forever = AsyncMock()
    wake.stop = MagicMock()

    stt = MagicMock()
    stt.listen_and_transcribe = AsyncMock(return_value="abrir chrome")
    stt.transcribe = AsyncMock(return_value="")

    tts = MagicMock()
    tts.speak = AsyncMock()
    tts.speak_streaming = AsyncMock()

    brain = MagicMock()
    brain.initialize = AsyncMock()
    brain.process = AsyncMock(return_value="He abierto Chrome para ti.")

    return VoicePipeline(wake=wake, stt=stt, tts=tts, brain=brain)


# --------------------------------------------------------------------------- #
# Estado inicial
# --------------------------------------------------------------------------- #
class TestInitialState:
    def test_starts_idle(self, pipeline: VoicePipeline) -> None:
        assert pipeline.state == VoiceState.IDLE

    def test_not_running(self, pipeline: VoicePipeline) -> None:
        assert not pipeline._running


# --------------------------------------------------------------------------- #
# Callbacks de estado y texto
# --------------------------------------------------------------------------- #
class TestCallbacks:
    def test_state_callback_is_called(self, pipeline: VoicePipeline) -> None:
        states: list[VoiceState] = []
        pipeline.on_state_change(states.append)
        pipeline._set_state(VoiceState.LISTENING)
        assert VoiceState.LISTENING in states

    def test_text_callback_is_called(self, pipeline: VoicePipeline) -> None:
        texts: list[tuple[str, str]] = []
        pipeline.on_text(lambda role, text: texts.append((role, text)))
        pipeline._emit_text("user", "hola")
        assert ("user", "hola") in texts

    def test_empty_text_not_emitted(self, pipeline: VoicePipeline) -> None:
        texts: list = []
        pipeline.on_text(lambda role, text: texts.append((role, text)))
        pipeline._emit_text("user", "")
        assert not texts

    def test_callback_exception_does_not_crash(self, pipeline: VoicePipeline) -> None:
        def _bad_cb(state: VoiceState) -> None:
            raise RuntimeError("callback roto")

        pipeline.on_state_change(_bad_cb)
        # No debe lanzar excepción
        pipeline._set_state(VoiceState.PROCESSING)
        assert pipeline.state == VoiceState.PROCESSING


# --------------------------------------------------------------------------- #
# handle_interaction
# --------------------------------------------------------------------------- #
class TestHandleInteraction:
    @pytest.mark.asyncio
    async def test_full_turn_states(self, pipeline: VoicePipeline) -> None:
        states: list[VoiceState] = []
        pipeline.on_state_change(states.append)
        await pipeline.handle_interaction()
        assert VoiceState.LISTENING in states
        assert VoiceState.PROCESSING in states
        assert VoiceState.SPEAKING in states
        assert states[-1] == VoiceState.IDLE

    @pytest.mark.asyncio
    async def test_empty_transcript_returns_idle(self, pipeline: VoicePipeline) -> None:
        pipeline.stt.listen_and_transcribe = AsyncMock(return_value="")
        states: list[VoiceState] = []
        pipeline.on_state_change(states.append)
        await pipeline.handle_interaction()
        assert states[-1] == VoiceState.IDLE
        pipeline.brain.process.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_brain_exception_sets_error_then_idle(self, pipeline: VoicePipeline) -> None:
        pipeline.brain.process = AsyncMock(side_effect=RuntimeError("boom"))
        states: list[VoiceState] = []
        pipeline.on_state_change(states.append)
        await pipeline.handle_interaction()
        assert VoiceState.ERROR in states
        assert states[-1] == VoiceState.IDLE


# --------------------------------------------------------------------------- #
# process_text_input
# --------------------------------------------------------------------------- #
class TestProcessTextInput:
    @pytest.mark.asyncio
    async def test_returns_response(self, pipeline: VoicePipeline) -> None:
        result = await pipeline.process_text_input("hola")
        assert result == "He abierto Chrome para ti."

    @pytest.mark.asyncio
    async def test_emits_user_and_assistant_text(self, pipeline: VoicePipeline) -> None:
        texts: list[tuple[str, str]] = []
        pipeline.on_text(lambda role, text: texts.append((role, text)))
        await pipeline.process_text_input("abre spotify")
        roles = [r for r, _ in texts]
        assert "user" in roles
        assert "assistant" in roles

    @pytest.mark.asyncio
    async def test_error_returns_fallback_message(self, pipeline: VoicePipeline) -> None:
        pipeline.brain.process = AsyncMock(side_effect=RuntimeError("error fatal"))
        result = await pipeline.process_text_input("crashear")
        assert "error" in result.lower() or "problema" in result.lower()

    @pytest.mark.asyncio
    async def test_always_returns_idle_after_error(self, pipeline: VoicePipeline) -> None:
        pipeline.brain.process = AsyncMock(side_effect=RuntimeError("ups"))
        states: list[VoiceState] = []
        pipeline.on_state_change(states.append)
        await pipeline.process_text_input("falla")
        assert states[-1] == VoiceState.IDLE

    @pytest.mark.asyncio
    async def test_uses_streaming_tts(self, pipeline: VoicePipeline) -> None:
        await pipeline.process_text_input("hola")
        pipeline.tts.speak_streaming.assert_awaited_once()


# --------------------------------------------------------------------------- #
# stop
# --------------------------------------------------------------------------- #
class TestStop:
    def test_stop_sets_running_false(self, pipeline: VoicePipeline) -> None:
        pipeline._running = True
        pipeline.stop()
        assert not pipeline._running
        pipeline.wake.stop.assert_called_once()
