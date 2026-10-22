"""La UI debe poder responder confirmaciones por su propia conexión."""
import asyncio

from fastapi.testclient import TestClient

from api.server import app, voice_pipeline, ws_manager
from config.constants import RiskLevel


def test_confirmation_and_response_share_connection(monkeypatch):
    async def command(text):
        approved = await ws_manager.request_confirmation('Acción simulada', RiskLevel.HIGH)
        await ws_manager._broadcast({'type':'message', 'role':'assistant', 'text':'permitida' if approved else 'cancelada'})
    monkeypatch.setattr(voice_pipeline, 'process_text_input', command)
    with TestClient(app) as client:
        with client.websocket_connect('/ws/stream') as ws:
            ws.send_json({'text':'prueba sin acciones reales'})
            confirmation = ws.receive_json()
            assert confirmation['type'] == 'confirmation'
            ws.send_json({'type':'confirmation_response', 'id':confirmation['id'], 'granted':False})
            assert ws.receive_json()['text'] == 'cancelada'
        assert not ws_manager._pending_confirmations


def test_disconnect_cleans_pending_confirmation(monkeypatch):
    async def command(text):
        await ws_manager.request_confirmation('Acción simulada', RiskLevel.HIGH)
    monkeypatch.setattr(voice_pipeline, 'process_text_input', command)
    with TestClient(app) as client:
        with client.websocket_connect('/ws/stream') as ws:
            ws.send_json({'text':'prueba'})
            assert ws.receive_json()['type'] == 'confirmation'
        assert not ws_manager._pending_confirmations


def test_invalid_payload_does_not_disconnect(monkeypatch):
    with TestClient(app) as client:
        with client.websocket_connect('/ws/stream') as ws:
            ws.send_json(['dato incorrecto'])
            assert ws.receive_json()['type'] == 'error'
            ws.send_json({'text':42})
            assert ws.receive_json()['type'] == 'error'
