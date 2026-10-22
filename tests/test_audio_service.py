import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest
from voice.audio_service import AudioService


def process_with(events):
    process = SimpleNamespace(returncode=None,
        stdin=SimpleNamespace(write=MagicMock(), drain=AsyncMock()),
        stdout=SimpleNamespace(readline=AsyncMock(side_effect=[(json.dumps(e)+'\n').encode() for e in events])),
        wait=AsyncMock(return_value=-9), communicate=AsyncMock(return_value=(b'', b'')))
    process.kill = MagicMock(side_effect=lambda: setattr(process, 'returncode', -9))
    return process


@pytest.mark.asyncio
async def test_worker_is_reused_and_closed_cleanly(monkeypatch):
    process = process_with([{'type':'result','value':True}, {'type':'result','value':'abre la calculadora'}])
    factory = AsyncMock(return_value=process)
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', factory)
    service = AudioService()
    assert await service.listen('wake') is True
    assert await service.listen('command') == 'abre la calculadora'
    factory.assert_awaited_once()
    await service.close()
    process.kill.assert_called_once()
    process.communicate.assert_awaited_once()
    assert service.process is None


@pytest.mark.asyncio
async def test_cancelled_wake_releases_microphone_process(monkeypatch):
    process = process_with([])
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', AsyncMock(return_value=process))
    service = AudioService()
    assert await service.listen('wake', should_stop=lambda: True) is False
    process.kill.assert_called_once()
    process.wait.assert_awaited_once()


@pytest.mark.asyncio
async def test_device_error_is_visible_and_worker_is_stopped(monkeypatch):
    process = process_with([{'type':'error','message':'micrófono desconectado'}])
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', AsyncMock(return_value=process))
    with pytest.raises(RuntimeError, match='desconectado'):
        await AudioService().listen('wake')
    process.kill.assert_called_once()
