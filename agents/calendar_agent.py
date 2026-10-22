"""Agente para Google Calendar: listar, crear y eliminar eventos.

Requiere un archivo ``credentials.json`` en la raíz del proyecto
(descargado desde Google Cloud Console → OAuth 2.0).  La primera vez se
abre el navegador para autorización; el token se guarda en
``token_calendar.json`` para sesiones posteriores.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from config.settings import settings
from core.logger import log

# ---- Importaciones opcionales de Google ---------------------------------- #
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build as _build_service

    _GOOGLE_OK = True
except ImportError:
    _GOOGLE_OK = False

_SCOPES = ["https://www.googleapis.com/auth/calendar"]
_CREDS_FILE = settings.base_dir / "credentials.json"
_TOKEN_FILE = settings.base_dir / "token_calendar.json"


# --------------------------------------------------------------------------- #
# Helpers bloqueantes (se ejecutan en hilos via asyncio.to_thread)
# --------------------------------------------------------------------------- #

def _get_service():  # type: ignore[return]
    """Construye y devuelve un servicio autenticado de Google Calendar."""
    if not _GOOGLE_OK:
        raise RuntimeError(
            "Las librerías de Google no están instaladas. "
            "Ejecuta: pip install google-api-python-client google-auth-oauthlib"
        )

    creds: Any = None
    if _TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN_FILE), _SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not _CREDS_FILE.exists():
                raise RuntimeError(
                    f"No se encontró {_CREDS_FILE}. "
                    "Descárgalo desde Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(_CREDS_FILE), _SCOPES)
            creds = flow.run_local_server(port=0)
        _TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    return _build_service("calendar", "v3", credentials=creds)


def _list_events_sync(max_results: int = 10) -> list[dict[str, Any]]:
    service = _get_service()
    now = datetime.now(timezone.utc).isoformat()
    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return result.get("items", [])


def _create_event_sync(
    title: str,
    start: str,
    end: str | None = None,
    description: str = "",
    location: str = "",
    timezone_str: str = "America/Mexico_City",
) -> dict[str, Any]:
    # Parsear inicio
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            start_dt = datetime.strptime(start, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"Formato de fecha no reconocido: '{start}'")

    end_dt = (
        datetime.strptime(end, "%Y-%m-%dT%H:%M:%S")
        if end
        else start_dt + timedelta(hours=1)
    )

    event_body = {
        "summary": title,
        "description": description,
        "location": location,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": timezone_str},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": timezone_str},
    }
    service = _get_service()
    return service.events().insert(calendarId="primary", body=event_body).execute()


def _delete_event_sync(event_id: str) -> None:
    _get_service().events().delete(calendarId="primary", eventId=event_id).execute()


# --------------------------------------------------------------------------- #
# Agente
# --------------------------------------------------------------------------- #

class CalendarAgent(BaseAgent):
    """Gestiona eventos de Google Calendar mediante la API oficial."""

    name = "calendar_agent"

    async def execute(  # type: ignore[override]
        self,
        action: str = "list_events",
        title: str = "",
        start: str = "",
        end: str | None = None,
        description: str = "",
        location: str = "",
        event_id: str = "",
        max_results: int = 10,
        **_: Any,
    ) -> AgentResult:
        action = (action or "list_events").lower()

        try:
            if action in {"list_events", "listar", "list", "ver_eventos"}:
                events = await asyncio.to_thread(_list_events_sync, max_results)
                if not events:
                    return self._ok(output=[], message="No tienes eventos próximos en tu calendario.")
                lines: list[str] = []
                for ev in events:
                    start_info = ev.get("start", {})
                    dt_str = start_info.get("dateTime") or start_info.get("date", "")
                    lines.append(f"• {ev.get('summary', '(Sin título)')} — {dt_str}")
                return self._ok(
                    output=events,
                    message="Tus próximos eventos:\n" + "\n".join(lines),
                )

            elif action in {"create_event", "crear", "add_event", "agendar", "crear_evento"}:
                if not title:
                    return self._fail("Se requiere un título para crear el evento.")
                if not start:
                    return self._fail("Se requiere la fecha/hora de inicio (campo 'start').")
                event = await asyncio.to_thread(
                    _create_event_sync, title, start, end, description, location
                )
                link = event.get("htmlLink", "")
                suffix = f" Ver en Calendar: {link}" if link else ""
                return self._ok(
                    output=event,
                    message=f"Evento '{title}' creado correctamente.{suffix}",
                )

            elif action in {"delete_event", "eliminar", "borrar", "eliminar_evento"}:
                if not event_id:
                    return self._fail("Se requiere el ID del evento para eliminarlo.")
                await asyncio.to_thread(_delete_event_sync, event_id)
                return self._ok(message="Evento eliminado correctamente.")

            else:
                return self._fail(f"Acción de calendario no reconocida: '{action}'.")

        except Exception as exc:  # noqa: BLE001
            log.error("[calendar_agent] Error inesperado: {}", exc)
            return self._fail(f"Error con Google Calendar: {exc}")


calendar_agent = CalendarAgent()
