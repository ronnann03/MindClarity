"""Controlador de Telegram: enviar/recibir mensajes, controlar YU remotamente."""
from __future__ import annotations

from typing import Any

from core.logger import log


class TelegramController:
    """Integración con Telegram via Bot API.

    Requiere: pip install python-telegram-bot
    Para usar:
    1. Crea un bot con @BotFather en Telegram
    2. Copia el token en TELEGRAM_BOT_TOKEN en .env
    3. Obtén tu TELEGRAM_CHAT_ID enviando un mensaje al bot
    """

    def __init__(self) -> None:
        self.bot_token = None
        self.chat_id = None
        self.is_configured = False
        self._init_telegram()

    def _init_telegram(self) -> None:
        """Inicializa el cliente de Telegram."""
        try:
            from config.settings import settings  # noqa: PLC0415

            bot_token = getattr(settings, "telegram_bot_token", "")
            chat_id = getattr(settings, "telegram_chat_id", "")

            if bot_token and chat_id:
                self.bot_token = bot_token
                self.chat_id = chat_id
                self.is_configured = True
                log.info("[telegram] Configurado")
            else:
                log.warning("[telegram] Sin configuración (requiere token y chat_id)")
        except Exception as exc:  # noqa: BLE001
            log.error("[telegram] Error inicializando: {}", exc)

    async def send_message(self, message: str, chat_id: str | None = None) -> bool:
        """Envía un mensaje por Telegram.

        Args:
            message: Texto del mensaje
            chat_id: ID del chat (usa el predeterminado si no se especifica)
        """
        if not self.is_configured:
            log.warning("[telegram] No configurado")
            return False

        target_chat = chat_id or self.chat_id

        try:
            import httpx  # noqa: PLC0415

            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json={"chat_id": target_chat, "text": message}
                )
                if resp.status_code == 200:
                    log.info("[telegram] Mensaje enviado")
                    return True
                else:
                    log.error("[telegram] Error: {}", resp.text)
                    return False
        except Exception as exc:  # noqa: BLE001
            log.error("[telegram] Error enviando: {}", exc)
            return False

    async def send_photo(self, photo_url: str, caption: str = "") -> bool:
        """Envía una foto por Telegram."""
        if not self.is_configured:
            return False

        try:
            import httpx  # noqa: PLC0415

            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "photo": photo_url,
                        "caption": caption
                    }
                )
                return resp.status_code == 200
        except Exception as exc:  # noqa: BLE001
            log.error("[telegram] Error enviando foto: {}", exc)
            return False

    async def notify(self, title: str, message: str, severity: str = "info") -> bool:
        """Envía una notificación formateada por Telegram."""
        if not self.is_configured:
            return False

        icons = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
        }

        icon = icons.get(severity, "")
        formatted = f"{icon} *{title}*\n\n{message}"

        try:
            import httpx  # noqa: PLC0415

            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": formatted,
                        "parse_mode": "Markdown"
                    }
                )
                return resp.status_code == 200
        except Exception as exc:  # noqa: BLE001
            log.error("[telegram] Error en notificación: {}", exc)
            return False

    async def get_updates(self) -> list[dict[str, Any]]:
        """Obtiene los últimos mensajes recibidos (para procesar comandos)."""
        if not self.is_configured:
            return []

        try:
            import httpx  # noqa: PLC0415

            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("result", [])
                return []
        except Exception as exc:  # noqa: BLE001
            log.error("[telegram] Error obteniendo updates: {}", exc)
            return []


telegram_controller = TelegramController()
