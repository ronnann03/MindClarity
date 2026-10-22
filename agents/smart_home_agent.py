"""Agente de hogar inteligente: control de luces, temperatura, dispositivos."""
from __future__ import annotations

from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from core.logger import log


class SmartHomeAgent(BaseAgent):
    """Controla dispositivos del hogar inteligente: luces, temperatura, enchufes."""

    name = "smart_home_agent"

    def __init__(self, model=None) -> None:
        super().__init__(model)
        # Simulación de dispositivos conectados (en producción, se conectaría a APIs reales)
        self.devices: dict[str, dict[str, Any]] = {
            "sala": {"type": "light", "status": "off", "brightness": 0, "color_temp": "warm"},
            "dormitorio": {"type": "light", "status": "off", "brightness": 0, "color_temp": "warm"},
            "cocina": {"type": "light", "status": "off", "brightness": 0, "color_temp": "cool"},
            "termostato": {"type": "thermostat", "status": "on", "temperature": 21, "mode": "auto"},
            "enchufe_tv": {"type": "plug", "status": "off"},
            "enchufe_cafetera": {"type": "plug", "status": "off"},
        }
        self.routines: dict[str, list[tuple[str, dict]]] = {}

    async def execute(  # type: ignore[override]
        self,
        action: str | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        """Ejecuta comandos de hogar inteligente.

        Acciones soportadas:
        - turn_on: encender dispositivo
        - turn_off: apagar dispositivo
        - set_brightness: ajustar brillo (luces)
        - set_temperature: ajustar temperatura
        - list_devices: listar todos los dispositivos
        - create_routine: crear automatización
        - activate_routine: activar rutina
        """
        if not action:
            action, kwargs = await self._infer_action(kwargs)

        match action:
            case "turn_on":
                return self._turn_on(**kwargs)
            case "turn_off":
                return self._turn_off(**kwargs)
            case "set_brightness":
                return self._set_brightness(**kwargs)
            case "set_temperature":
                return self._set_temperature(**kwargs)
            case "list_devices":
                return self._list_devices(**kwargs)
            case "create_routine":
                return self._create_routine(**kwargs)
            case "activate_routine":
                return self._activate_routine(**kwargs)
            case _:
                return self._fail(f"Acción de hogar inteligente no soportada: '{action}'")

    def _turn_on(self, device: str = "", **_: Any) -> AgentResult:
        """Enciende un dispositivo."""
        if not device or device not in self.devices:
            return self._fail(f"Dispositivo no encontrado: '{device}'")

        dev = self.devices[device]
        dev["status"] = "on"
        if dev["type"] == "light" and "brightness" in dev:
            dev["brightness"] = 100

        message = f"✓ {device.capitalize()} encendido"
        log.info("[smart_home_agent] {}", message)
        return self._ok(output={"device": device, "status": "on"}, message=message)

    def _turn_off(self, device: str = "", **_: Any) -> AgentResult:
        """Apaga un dispositivo."""
        if not device or device not in self.devices:
            return self._fail(f"Dispositivo no encontrado: '{device}'")

        dev = self.devices[device]
        dev["status"] = "off"
        if dev["type"] == "light" and "brightness" in dev:
            dev["brightness"] = 0

        message = f"✓ {device.capitalize()} apagado"
        log.info("[smart_home_agent] {}", message)
        return self._ok(output={"device": device, "status": "off"}, message=message)

    def _set_brightness(self, device: str = "", brightness: int = 50, **_: Any) -> AgentResult:
        """Ajusta el brillo de una luz."""
        if not device or device not in self.devices:
            return self._fail(f"Dispositivo no encontrado: '{device}'")

        dev = self.devices[device]
        if dev["type"] != "light":
            return self._fail(f"'{device}' no es una luz")

        brightness = max(0, min(100, brightness))
        dev["brightness"] = brightness
        dev["status"] = "on" if brightness > 0 else "off"

        message = f"Brillo de {device} ajustado a {brightness}%"
        log.info("[smart_home_agent] {}", message)
        return self._ok(output={"device": device, "brightness": brightness}, message=message)

    def _set_temperature(self, temperature: float = 20, mode: str = "auto", **_: Any) -> AgentResult:
        """Ajusta la temperatura del termostato."""
        if "termostato" not in self.devices:
            return self._fail("Termostato no disponible")

        temperature = max(15, min(30, temperature))
        thermo = self.devices["termostato"]
        thermo["temperature"] = temperature
        thermo["mode"] = mode

        message = f"Termostato ajustado a {temperature}°C en modo {mode}"
        log.info("[smart_home_agent] {}", message)
        return self._ok(
            output={"temperature": temperature, "mode": mode}, message=message
        )

    def _list_devices(self, **_: Any) -> AgentResult:
        """Lista todos los dispositivos disponibles."""
        summary = "Dispositivos disponibles:\n"
        for device_name, dev in self.devices.items():
            status = dev.get("status", "unknown")
            if dev["type"] == "light" and "brightness" in dev:
                summary += f"• {device_name}: {status} (brillo: {dev['brightness']}%)\n"
            elif dev["type"] == "thermostat":
                temp = dev.get("temperature", "?")
                mode = dev.get("mode", "?")
                summary += f"• {device_name}: {status} ({temp}°C, modo {mode})\n"
            else:
                summary += f"• {device_name}: {status}\n"

        return self._ok(output=self.devices, message=summary)

    def _create_routine(self, name: str = "", actions: list[tuple[str, dict]] | None = None, **_: Any) -> AgentResult:
        """Crea una rutina (automatización) con múltiples acciones."""
        if not name or not actions:
            return self._fail("Nombre y acciones requeridas para crear una rutina")

        self.routines[name] = actions
        message = f"Rutina '{name}' creada con {len(actions)} acción(es)"
        log.info("[smart_home_agent] {}", message)
        return self._ok(output={"routine": name}, message=message)

    def _activate_routine(self, name: str = "", **_: Any) -> AgentResult:
        """Activa una rutina guardada."""
        if not name or name not in self.routines:
            return self._fail(f"Rutina no encontrada: '{name}'")

        actions = self.routines[name]
        results = []
        for action, params in actions:
            # Ejecuta cada acción secuencialmente
            match action:
                case "turn_on":
                    results.append(self._turn_on(**params))
                case "turn_off":
                    results.append(self._turn_off(**params))
                case "set_brightness":
                    results.append(self._set_brightness(**params))
                case "set_temperature":
                    results.append(self._set_temperature(**params))

        message = f"Rutina '{name}' activada ({len(results)} acciones ejecutadas)"
        log.info("[smart_home_agent] {}", message)
        return self._ok(output={"routine": name, "executed": len(results)}, message=message)

    async def _infer_action(self, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Infiere la acción a partir del texto."""
        text = kwargs.get("query") or kwargs.get("text") or str(kwargs)
        prompt = (
            f"Dado el comando: '{text}', identifica la acción de hogar inteligente. "
            f"Opciones: turn_on, turn_off, set_brightness, set_temperature, list_devices, create_routine, activate_routine. "
            f"Responde solo con el nombre de la acción."
        )
        action = (await self.ask_llm(prompt)).strip().split()[0] if text else ""
        log.debug("[smart_home_agent] Acción inferida: {}", action)
        return action, kwargs


smart_home_agent = SmartHomeAgent()
