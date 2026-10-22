"""Agente de email basado en la Gmail API.

Requiere credenciales OAuth de Google (credentials.json) la primera vez.
Si no hay credenciales, opera de forma degradada informando al usuario.
"""
from __future__ import annotations

import asyncio
import base64
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from config.settings import settings
from core.logger import log

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    _GMAIL_AVAILABLE = True
except Exception:  # noqa: BLE001
    _GMAIL_AVAILABLE = False

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


class EmailAgent(BaseAgent):
    """Lee, resume y envía correos mediante Gmail."""

    name = "email_agent"

    def __init__(self, model=None) -> None:
        super().__init__(model)
        self._service: Any = None
        self.creds_path = settings.base_dir / "credentials.json"
        self.token_path = settings.base_dir / "token.json"

    # ------------------------------------------------------------------ #
    def _get_service(self) -> Any:
        """Autentica y construye el servicio de Gmail (perezoso)."""
        if self._service is not None:
            return self._service
        if not _GMAIL_AVAILABLE:
            raise RuntimeError("Librerías de Google API no instaladas.")
        creds: Any = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.creds_path.exists():
                    raise RuntimeError("Falta credentials.json para Gmail.")
                flow = InstalledAppFlow.from_client_secrets_file(str(self.creds_path), SCOPES)
                creds = flow.run_local_server(port=0)
            self.token_path.write_text(creds.to_json(), encoding="utf-8")
        self._service = build("gmail", "v1", credentials=creds)
        return self._service

    # ------------------------------------------------------------------ #
    async def execute(  # type: ignore[override]
        self,
        action: str = "read_email",
        **kwargs: Any,
    ) -> AgentResult:
        """Acepta llamadas con kwargs sueltos del decision_engine.

        `kwargs` contiene el resto de entidades: recipient, subject, body,
        query, limit, etc.
        """
        task = {"action": action, **kwargs}
        action = action.lower()
        try:
            # Las llamadas a la API de Google son síncronas y bloqueantes;
            # se ejecutan en un hilo para no bloquear el event loop de asyncio.
            if "send" in action or "enviar" in action:
                return await asyncio.to_thread(self._send, task)
            return await asyncio.to_thread(self._read_inbox, task)
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"Error con el correo: {exc}")

    def _read_inbox(self, task: dict[str, Any]) -> AgentResult:
        service = self._get_service()
        limit = int(task.get("limit", 5))
        results = service.users().messages().list(
            userId="me", maxResults=limit, q=task.get("query", "is:unread")
        ).execute()
        messages = results.get("messages", [])
        summaries: list[str] = []
        for msg in messages:
            full = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "Subject"],
            ).execute()
            headers = {h["name"]: h["value"] for h in full["payload"]["headers"]}
            summaries.append(f"De {headers.get('From', '?')}: {headers.get('Subject', '(sin asunto)')}")
        text = "\n".join(summaries) if summaries else "No hay correos sin leer."
        return self._ok(output=summaries, message=text)

    def _send(self, task: dict[str, Any]) -> AgentResult:
        service = self._get_service()
        to = task.get("recipient") or task.get("to")
        subject = task.get("subject", "Mensaje de YU")
        body = task.get("body") or task.get("content", "")
        if not to:
            return self._fail("Falta el destinatario del correo.")
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        log.info("Correo enviado a {}.", to)
        return self._ok(message=f"Correo enviado a {to}.")


email_agent = EmailAgent()
