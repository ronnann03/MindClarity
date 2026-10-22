from unittest.mock import AsyncMock, MagicMock
import asyncio
import numpy as np
import pytest

from core.voice_commands import match_command
from voice.audio_capture import SpeechSegmenter
from voice.wake_word import WakeWordDetector
from voice.voice_pipeline import VoicePipeline
from config.constants import RiskLevel, VoiceState, ExecutionStatus, IntentType
from core.decision_engine import DecisionEngine
from core.planner import Plan, ActionStep
from agents.base_agent import AgentResult


@pytest.mark.parametrize('phrase,expected', [('YU, abre la calculadora','abre la calculadora'),
    ('Yu, pon el volumen al 30','pon el volumen al 30'),('Yu',''),
    ('Oye YU, abre la calculadora.',None),('you open calculator',None),
    ('hablando de YU abre la calculadora',None),
    ('ayuda con mis ideas',None),('hay un ayudante aquí',None),('incluye un texto',None)])
def test_wake_word_is_a_prefix_not_substring(phrase, expected):
    detector = WakeWordDetector(stt=MagicMock())
    assert detector.extract_command(phrase) == expected


def test_phrase_ends_after_silence_not_mid_sentence():
    segmenter = SpeechSegmenter(100, .01, .4)
    speech = np.full(20, .1, dtype=np.float32)
    silence = np.zeros(20, dtype=np.float32)
    assert not segmenter.feed(silence)
    assert not segmenter.feed(speech)
    assert not segmenter.feed(silence)
    assert not segmenter.feed(speech)
    assert not segmenter.feed(silence)
    assert segmenter.feed(silence)
    assert segmenter.audio().size == 120


@pytest.mark.parametrize('phrase,action,entities',[
    ('pon el volumen al 30','set_volume',{'level':30}),
    ('ajusta el brillo al 50 por ciento','set_brightness',{'level':50}),
    ('minimiza Chrome','minimize',{'title':'Chrome'}),
    ('abre YouTube','open_url',{'url':'https://www.youtube.com'}),
    ('¿Qué tiempo hace en Arequipa?','get_weather',{'city':'Arequipa'}),
    ('anota una tarea: llamar a Ana','create_task',{'title':'llamar a Ana'}),
])
def test_spanish_commands_keep_parameters(phrase,action,entities):
    result = match_command(phrase)
    assert result.action == action
    assert result.entities == entities


def pipeline():
    wake = MagicMock(pending_text='abre la calculadora')
    stt = MagicMock(listen_and_transcribe=AsyncMock(return_value=''))
    tts = MagicMock(speak_streaming=AsyncMock())
    brain = MagicMock(process=AsyncMock(return_value='He abierto la calculadora.'))
    return VoicePipeline(wake=wake,stt=stt,tts=tts,brain=brain)


@pytest.mark.asyncio
async def test_single_phrase_does_not_ask_to_repeat():
    voice = pipeline()
    await voice.handle_interaction()
    voice.brain.process.assert_awaited_once_with('abre la calculadora')
    voice.stt.listen_and_transcribe.assert_not_awaited()
    assert voice.state == VoiceState.IDLE and not voice.voice_turn


@pytest.mark.asyncio
@pytest.mark.parametrize('reply,approved',[('Confirmar acción.',True),('cancelar acción',False),('sí',False),('',False),('no confirmar acción',False)])
async def test_voice_confirmation_is_explicit(reply, approved):
    voice = pipeline()
    voice.stt.listen_and_transcribe.return_value = reply
    assert await voice.request_voice_confirmation('acción de prueba',RiskLevel.HIGH) is approved


@pytest.mark.asyncio
async def test_parallel_commands_do_not_share_microphone():
    voice = pipeline()
    voice._turn_lock.acquire()
    result = await voice.process_text_input('otra petición')
    assert 'otra petición' in result
    voice.brain.process.assert_not_awaited()
    voice._turn_lock.release()


@pytest.mark.asyncio
async def test_failed_agent_is_not_reported_as_success():
    engine = DecisionEngine()
    executor = MagicMock(execute=AsyncMock(return_value=AgentResult(success=False,message='No configurado')))
    engine.register('fake',executor)
    plan = Plan(intent_type=IntentType.CONVERSATION,steps=[ActionStep(module='fake',function='execute')])
    result = await engine.execute_plan(plan)
    assert result.status == ExecutionStatus.FAILED


def test_local_tasks_survive_a_new_instance(tmp_path):
    from database.local_tasks import LocalTasks
    path = tmp_path / 'tasks.sqlite3'
    row = LocalTasks(path).create({'title':'Tarea de prueba'})
    assert LocalTasks(path).pending()[0]['title'] == 'Tarea de prueba'
    assert LocalTasks(path).complete(row['id'])
    assert not LocalTasks(path).pending()


def test_microphone_stream_is_reused_between_listens(monkeypatch):
    import sounddevice as sd
    from voice import audio_capture
    from config.settings import settings
    monkeypatch.setattr(settings, 'voice_input_device', None)
    monkeypatch.setattr(settings, 'voice_input_hostapi', '')
    stream = MagicMock()
    stream.active = True
    stream.read_available = 0
    stream.read.return_value = (np.zeros((3200,1),dtype=np.float32),False)
    factory = MagicMock(return_value=stream)
    monkeypatch.setattr(sd,'InputStream',factory)
    monkeypatch.setattr(audio_capture,'_STREAM',None)
    for _ in range(2):
        audio_capture.capture_utterance(sample_rate=16000,threshold=.002,
            silence_seconds=.8,start_timeout=0,max_seconds=1)
    factory.assert_called_once()
    stream.start.assert_called_once()


def test_spoken_app_name_with_terminal_punctuation():
    from core.intent_detector import _fast_rule_match
    from automation.app_launcher import AppLauncher
    command = _fast_rule_match('abre la calculadora.')
    assert command.entities['name'] == 'calculadora'
    assert AppLauncher()._resolve('calculadora.') == 'calc.exe'


def test_repeated_wake_command_is_one_application_name():
    from core.intent_detector import _fast_rule_match
    detector = WakeWordDetector()
    command = detector.extract_command('YU, abre la calculadora. YU, abre la calculadora.')
    assert _fast_rule_match(command).entities['name'] == 'calculadora'
    assert detector.extract_command('YU, abre Chrome. Oye YU, cierra Chrome.') == 'abre Chrome. Oye YU, cierra Chrome.'


def test_quiet_wake_prefix_survives_until_louder_command():
    segmenter = SpeechSegmenter(100, .01, .4)
    quiet = np.full(20, .005, dtype=np.float32)
    for _ in range(6):
        segmenter.feed(quiet)
    segmenter.feed(np.full(20, .1, dtype=np.float32))
    assert segmenter.audio().size == 140
