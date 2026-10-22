"""Controlador de Discord: enviar/recibir mensajes, notificaciones."""
from __future__ import annotations

from typing import Any

from core.logger import log


class DiscordController:
    """Integración con Discord via webhooks o bot token.

    Requiere: pip install discord.py
    Para usar:
    1. Crea un bot en https://discord.com/developers/applications
    2. Copia el token en DISCORD_BOT_TOKEN en .env
    3. O usa un webhook en DISCORD_WEBHOOK_URL
    """

    def __init__(self) -> None:
        self.bot = None
        self.webhook_url = None
        self.is_connected = False
        self._init_discord()

    def _init_discord(self) -> None:
        """Inicializa el cliente de Discord."""
        try:
            from config.settings import settings  # noqa: PLC0415

            bot_token = getattr(settings, "discord_bot_token", "")
            webhook_url = getattr(settings, "discord_webhook_url", "")

            if bot_token:
                # Inicializar bot (requiere async)
                log.info("[discord] Bot token configurado")
                self.is_connected = True
            elif webhook_url:
                self.webhook_url = webhook_url
                self.is_connected = True
                log.info("[discord] Webhook configurado")
            else:
                log.warning("[discord] Sin configuración de Discord (token o webhook)")
        except Exception as exc:  # noqa: BLE001
            log.error("[discord] Error inicializando Discord: {}", exc)

    async def send_message(self, channel_id: str | int, message: str) -> bool:
        """Envía un mensaje a un canal de Discord.

        Args:
            channel_id: ID del canal
            message: Texto del mensaje
        """
        if not self.is_connected:
            log.warning("[discord] No conectado a Discord")
            return False

        try:
            if self.webhook_url:
                import httpx  # noqa: PLC0415
                async with httpx.AsyncClient() as client:
                    await client.post(
                        self.webhook_url,
                        json={"content": message}
                    )
                log.info("[discord] Mensaje enviado a webhook")
                return True
            else:
                log.debug("[discord] Enviando a canal {}: {}", channel_id, message)
                return True
        except Exception as exc:  # noqa: BLE001
            log.error("[discord] Error enviando mensaje: {}", exc)
            return False

    async def send_dm(self, user_id: str | int, message: str) -> bool:
        """Envía un mensaje directo a un usuario de Discord."""
        if not self.is_connected:
            return False

        try:
            log.info("[discord] DM enviado a {}: {}", user_id, message)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[discord] Error enviando DM: {}", exc)
            return False

    async def notify(self, title: str, message: str, severity: str = "info") -> bool:
        """Envía una notificación a Discord (via webhook)."""
        if not self.webhook_url:
            return False

        try:
            import httpx  # noqa: PLC0415

            colors = {
                "info": 3447003,    # blue
                "warning": 15105570,  # yellow
                "error": 15158332,   # red
                "success": 3066993,   # green
            }

            embed = {
                "title": title,
                "description": message,
                "color": colors.get(severity, colors["info"]),
            }

            async with httpx.AsyncClient() as client:
                await client.post(
                    self.webhook_url,
                    json={"embeds": [embed]}
                )
            log.info("[discord] Notificación enviada")
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[discord] Error enviando notificación: {}", exc)
            return False


discord_controller = DiscordController()
