"""Controlador de Slack: enviar mensajes, notificaciones."""
from __future__ import annotations

from typing import Any

from core.logger import log


class SlackController:
    """Integración con Slack para notificaciones y mensajes.

    Requiere: pip install slack-sdk
    Configuración en .env:
    - SLACK_BOT_TOKEN: xoxb-... (Bot token)
    - SLACK_CHANNEL_ID: C0xxxxx (ID del canal)
    """

    def __init__(self) -> None:
        self.client = None
        self.bot_token = None
        self.channel_id = None
        self.is_configured = False
        self._init_slack()

    def _init_slack(self) -> None:
        """Inicializa el cliente de Slack."""
        try:
            from slack_sdk import WebClient  # noqa: PLC0415
            from config.settings import settings  # noqa: PLC0415

            bot_token = getattr(settings, "slack_bot_token", "")
            channel_id = getattr(settings, "slack_channel_id", "")

            if bot_token:
                self.client = WebClient(token=bot_token)
                self.bot_token = bot_token
                self.channel_id = channel_id
                self.is_configured = True
                log.info("[slack] Configurado")
            else:
                log.warning("[slack] Sin token de bot")
        except ImportError:
            log.warning("[slack] slack-sdk no instalado. Ejecuta: pip install slack-sdk")
        except Exception as exc:  # noqa: BLE001
            log.error("[slack] Error inicializando: {}", exc)

    async def send_message(self, text: str, channel: str | None = None) -> bool:
        """Envía un mensaje a Slack.

        Args:
            text: Contenido del mensaje
            channel: ID o nombre del canal (usa el predeterminado si no se especifica)
        """
        if not self.is_configured or not self.client:
            return False

        target_channel = channel or self.channel_id

        try:
            self.client.chat_postMessage(
                channel=target_channel,
                text=text
            )
            log.info("[slack] Mensaje enviado")
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[slack] Error enviando mensaje: {}", exc)
            return False

    async def send_notification(self, title: str, message: str, severity: str = "info") -> bool:
        """Envía una notificación formateada a Slack."""
        if not self.is_configured or not self.client:
            return False

        colors = {
            "info": "#0099ff",
            "warning": "#ffaa00",
            "error": "#ff3333",
            "success": "#00cc44",
        }

        try:
            self.client.chat_postMessage(
                channel=self.channel_id,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{title}*\n{message}"
                        }
                    }
                ],
                attachments=[
                    {
                        "color": colors.get(severity, colors["info"]),
                        "text": message
                    }
                ]
            )
            log.info("[slack] Notificación enviada")
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[slack] Error en notificación: {}", exc)
            return False

    async def list_channels(self) -> list[dict[str, Any]]:
        """Lista todos los canales de Slack."""
        if not self.is_configured or not self.client:
            return []

        try:
            result = self.client.conversations_list()
            channels = result.get("channels", [])
            log.info("[slack] {} canales encontrados", len(channels))
            return channels
        except Exception as exc:  # noqa: BLE001
            log.error("[slack] Error listando canales: {}", exc)
            return []

    async def get_messages(self, channel: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        """Obtiene los últimos mensajes de un canal."""
        if not self.is_configured or not self.client:
            return []

        target_channel = channel or self.channel_id

        try:
            result = self.client.conversations_history(
                channel=target_channel,
                limit=limit
            )
            messages = result.get("messages", [])
            log.info("[slack] {} mensajes obtenidos", len(messages))
            return messages
        except Exception as exc:  # noqa: BLE001
            log.error("[slack] Error obteniendo mensajes: {}", exc)
            return []

    async def react_to_message(self, channel: str, timestamp: str, emoji: str) -> bool:
        """Añade una reacción a un mensaje."""
        if not self.is_configured or not self.client:
            return False

        try:
            self.client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=emoji
            )
            log.info("[slack] Reacción añadida: :{}", emoji)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[slack] Error añadiendo reacción: {}", exc)
            return False


slack_controller = SlackController()
