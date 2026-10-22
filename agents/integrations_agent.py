"""Agente integrador: Discord, Telegram, Home Assistant, Google Drive, Slack."""
from __future__ import annotations

from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from core.logger import log
from integrations.discord_controller import discord_controller
from integrations.google_drive_controller import google_drive_controller
from integrations.homeassistant_controller import homeassistant_controller
from integrations.slack_controller import slack_controller
from integrations.telegram_controller import telegram_controller


class IntegrationsAgent(BaseAgent):
    """Maneja comunicaciones via Discord, Telegram, Slack y dispositivos IoT."""

    name = "integrations_agent"

    async def execute(  # type: ignore[override]
        self,
        action: str | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        """Ejecuta comandos de integraciones.

        Acciones Discord:
        - discord_message: enviar mensaje
        - discord_notify: enviar notificación

        Acciones Telegram:
        - telegram_message: enviar mensaje
        - telegram_photo: enviar foto
        - telegram_notify: enviar notificación

        Acciones Slack:
        - slack_message: enviar mensaje
        - slack_notify: enviar notificación

        Acciones Home Assistant:
        - ha_turn_on, ha_turn_off, ha_set_brightness, ha_set_temperature

        Acciones Google Drive:
        - drive_list, drive_upload, drive_download
        """
        if not action:
            action, kwargs = await self._infer_action(kwargs)

        # Discord
        if action.startswith("discord_"):
            return await self._handle_discord(action, **kwargs)
        # Telegram
        elif action.startswith("telegram_"):
            return await self._handle_telegram(action, **kwargs)
        # Slack
        elif action.startswith("slack_"):
            return await self._handle_slack(action, **kwargs)
        # Home Assistant
        elif action.startswith("ha_"):
            return await self._handle_homeassistant(action, **kwargs)
        # Google Drive
        elif action.startswith("drive_"):
            return await self._handle_drive(action, **kwargs)
        else:
            return self._fail(f"Acción desconocida: '{action}'")

    # ---- Discord ---- #
    async def _handle_discord(self, action: str, **kwargs: Any) -> AgentResult:
        """Maneja comandos de Discord."""
        match action:
            case "discord_message":
                text = kwargs.get("message", "")
                if not text:
                    return self._fail("Mensaje requerido")
                success = await discord_controller.send_message(
                    kwargs.get("channel_id", ""),
                    text
                )
                if success:
                    return self._ok(output={}, message="Mensaje enviado a Discord")
                return self._fail("No se pudo enviar a Discord")

            case "discord_notify":
                success = await discord_controller.notify(
                    kwargs.get("title", ""),
                    kwargs.get("message", ""),
                    kwargs.get("severity", "info")
                )
                if success:
                    return self._ok(output={}, message="Notificación enviada a Discord")
                return self._fail("No se pudo enviar notificación")

            case _:
                return self._fail(f"Acción Discord no soportada: {action}")

    # ---- Telegram ---- #
    async def _handle_telegram(self, action: str, **kwargs: Any) -> AgentResult:
        """Maneja comandos de Telegram."""
        match action:
            case "telegram_message":
                text = kwargs.get("message", "")
                if not text:
                    return self._fail("Mensaje requerido")
                success = await telegram_controller.send_message(text)
                if success:
                    return self._ok(output={}, message="Mensaje enviado a Telegram")
                return self._fail("No se pudo enviar a Telegram")

            case "telegram_notify":
                success = await telegram_controller.notify(
                    kwargs.get("title", ""),
                    kwargs.get("message", ""),
                    kwargs.get("severity", "info")
                )
                if success:
                    return self._ok(output={}, message="Notificación enviada a Telegram")
                return self._fail("No se pudo enviar notificación")

            case _:
                return self._fail(f"Acción Telegram no soportada: {action}")

    # ---- Slack ---- #
    async def _handle_slack(self, action: str, **kwargs: Any) -> AgentResult:
        """Maneja comandos de Slack."""
        match action:
            case "slack_message":
                text = kwargs.get("message", "")
                if not text:
                    return self._fail("Mensaje requerido")
                success = await slack_controller.send_message(text)
                if success:
                    return self._ok(output={}, message="Mensaje enviado a Slack")
                return self._fail("No se pudo enviar a Slack")

            case "slack_notify":
                success = await slack_controller.send_notification(
                    kwargs.get("title", ""),
                    kwargs.get("message", ""),
                    kwargs.get("severity", "info")
                )
                if success:
                    return self._ok(output={}, message="Notificación enviada a Slack")
                return self._fail("No se pudo enviar notificación")

            case _:
                return self._fail(f"Acción Slack no soportada: {action}")

    # ---- Home Assistant ---- #
    async def _handle_homeassistant(self, action: str, **kwargs: Any) -> AgentResult:
        """Maneja comandos de Home Assistant."""
        match action:
            case "ha_turn_on":
                entity_id = kwargs.get("entity_id", "")
                success = await homeassistant_controller.turn_on(entity_id)
                if success:
                    return self._ok(output={}, message=f"{entity_id} encendido")
                return self._fail(f"No se pudo encender {entity_id}")

            case "ha_turn_off":
                entity_id = kwargs.get("entity_id", "")
                success = await homeassistant_controller.turn_off(entity_id)
                if success:
                    return self._ok(output={}, message=f"{entity_id} apagado")
                return self._fail(f"No se pudo apagar {entity_id}")

            case "ha_set_brightness":
                success = await homeassistant_controller.set_brightness(
                    kwargs.get("light_id", ""),
                    kwargs.get("brightness", 128)
                )
                if success:
                    return self._ok(output={}, message="Brillo ajustado")
                return self._fail("No se pudo ajustar brillo")

            case "ha_set_temperature":
                success = await homeassistant_controller.set_temperature(
                    kwargs.get("climate_id", ""),
                    kwargs.get("temperature", 20)
                )
                if success:
                    return self._ok(output={}, message="Temperatura ajustada")
                return self._fail("No se pudo ajustar temperatura")

            case _:
                return self._fail(f"Acción Home Assistant no soportada: {action}")

    # ---- Google Drive ---- #
    async def _handle_drive(self, action: str, **kwargs: Any) -> AgentResult:
        """Maneja comandos de Google Drive."""
        match action:
            case "drive_list":
                files = await google_drive_controller.list_files(
                    kwargs.get("folder", ""),
                    kwargs.get("limit", 10)
                )
                if files:
                    summary = "Archivos encontrados:\n"
                    for f in files:
                        summary += f"• {f.get('name', 'Sin nombre')}\n"
                    return self._ok(output=files, message=summary)
                return self._ok(output=[], message="No hay archivos")

            case "drive_upload":
                success = await google_drive_controller.upload_file(
                    kwargs.get("file_path", ""),
                    kwargs.get("file_name", "")
                )
                if success:
                    return self._ok(output={}, message="Archivo subido a Drive")
                return self._fail("No se pudo subir archivo")

            case "drive_download":
                success = await google_drive_controller.download_file(
                    kwargs.get("file_id", ""),
                    kwargs.get("output_path", "")
                )
                if success:
                    return self._ok(output={}, message="Archivo descargado")
                return self._fail("No se pudo descargar")

            case _:
                return self._fail(f"Acción Drive no soportada: {action}")

    async def _infer_action(self, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Infiere la acción a partir del texto."""
        text = kwargs.get("query") or kwargs.get("text") or str(kwargs)
        prompt = (
            f"Dado el comando: '{text}', identifica la acción de integraciones. "
            f"Acciones: discord_message, discord_notify, telegram_message, telegram_notify, "
            f"slack_message, slack_notify, ha_turn_on, ha_turn_off, ha_set_brightness, "
            f"ha_set_temperature, drive_list, drive_upload, drive_download. "
            f"Responde solo con el nombre de la acción."
        )
        action = (await self.ask_llm(prompt)).strip().split()[0] if text else ""
        log.debug("[integrations_agent] Acción inferida: {}", action)
        return action, kwargs


integrations_agent = IntegrationsAgent()
