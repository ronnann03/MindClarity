"""Controlador de Home Assistant: control de dispositivos IoT."""
from __future__ import annotations

from typing import Any

import httpx

from core.logger import log


class HomeAssistantController:
    """Integración con Home Assistant para control de IoT.

    Requiere: Home Assistant corriendo en tu red
    Configuración en .env:
    - HOMEASSISTANT_URL: http://homeassistant.local:8123
    - HOMEASSISTANT_TOKEN: long-lived access token
    """

    def __init__(self) -> None:
        self.base_url = None
        self.token = None
        self.is_configured = False
        self._init_homeassistant()

    def _init_homeassistant(self) -> None:
        """Inicializa la conexión con Home Assistant."""
        try:
            from config.settings import settings  # noqa: PLC0415

            url = getattr(settings, "homeassistant_url", "")
            token = getattr(settings, "homeassistant_token", "")

            if url and token:
                self.base_url = url.rstrip("/")
                self.token = token
                self.is_configured = True
                log.info("[homeassistant] Configurado en {}", self.base_url)
            else:
                log.warning("[homeassistant] Sin configuración")
        except Exception as exc:  # noqa: BLE001
            log.error("[homeassistant] Error inicializando: {}", exc)

    async def get_states(self) -> list[dict[str, Any]]:
        """Obtiene el estado de todos los dispositivos."""
        if not self.is_configured:
            return []

        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/states", headers=headers)
                if resp.status_code == 200:
                    return resp.json()
                return []
        except Exception as exc:  # noqa: BLE001
            log.error("[homeassistant] Error obteniendo estados: {}", exc)
            return []

    async def call_service(self, domain: str, service: str, **data: Any) -> bool:
        """Llama a un servicio de Home Assistant.

        Args:
            domain: Dominio (light, climate, switch, etc.)
            service: Servicio (turn_on, turn_off, set_temperature, etc.)
            **data: Datos del servicio
        """
        if not self.is_configured:
            return False

        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/api/services/{domain}/{service}",
                    headers=headers,
                    json=data
                )
                success = resp.status_code in [200, 201]
                if success:
                    log.info("[homeassistant] {}/{} ejecutado", domain, service)
                return success
        except Exception as exc:  # noqa: BLE001
            log.error("[homeassistant] Error llamando servicio: {}", exc)
            return False

    async def turn_on(self, entity_id: str) -> bool:
        """Enciende un dispositivo."""
        return await self.call_service("homeassistant", "turn_on", entity_id=entity_id)

    async def turn_off(self, entity_id: str) -> bool:
        """Apaga un dispositivo."""
        return await self.call_service("homeassistant", "turn_off", entity_id=entity_id)

    async def set_brightness(self, light_id: str, brightness: int) -> bool:
        """Ajusta el brillo de una luz."""
        brightness = max(0, min(255, brightness))
        return await self.call_service(
            "light", "turn_on",
            entity_id=light_id,
            brightness=brightness
        )

    async def set_temperature(self, climate_id: str, temperature: float) -> bool:
        """Ajusta la temperatura de un termostato."""
        return await self.call_service(
            "climate", "set_temperature",
            entity_id=climate_id,
            temperature=temperature
        )

    async def get_entity_state(self, entity_id: str) -> dict[str, Any] | None:
        """Obtiene el estado de una entidad específica."""
        if not self.is_configured:
            return None

        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/api/states/{entity_id}",
                    headers=headers
                )
                if resp.status_code == 200:
                    return resp.json()
                return None
        except Exception as exc:  # noqa: BLE001
            log.error("[homeassistant] Error obteniendo estado: {}", exc)
            return None

    async def list_entities(self, domain: str | None = None) -> list[str]:
        """Lista entidades, opcionalmente filtradas por dominio."""
        states = await self.get_states()
        if domain:
            return [s["entity_id"] for s in states if s["entity_id"].startswith(domain)]
        return [s["entity_id"] for s in states]


homeassistant_controller = HomeAssistantController()
