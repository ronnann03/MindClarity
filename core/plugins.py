"""Sistema de plugins para extender YU.

Los plugins son módulos Python que se cargan dinámicamente.
Estructura de un plugin:

plugins/
  └── mi_plugin/
      ├── __init__.py
      ├── config.json
      └── handler.py

config.json:
{
    "name": "Mi Plugin",
    "version": "1.0.0",
    "author": "Nombre",
    "description": "Descripción",
    "handler": "handler:MyPluginHandler"
}
"""
from __future__ import annotations

import importlib.util
import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.logger import log


@dataclass
class PluginConfig:
    """Configuración de un plugin."""
    name: str
    version: str
    author: str
    description: str
    handler: str
    enabled: bool = True


class BasePlugin(ABC):
    """Clase base para todos los plugins."""

    name: str = "base_plugin"
    version: str = "1.0.0"

    def __init__(self) -> None:
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Inicializa el plugin."""
        pass

    @abstractmethod
    async def on_command(self, text: str) -> str | None:
        """Procesa un comando. Retorna respuesta o None si no maneja el comando."""
        pass

    async def shutdown(self) -> None:
        """Limpia recursos al descargar el plugin."""
        pass


class PluginManager:
    """Gestor de plugins dinámicos."""

    def __init__(self, plugins_dir: Path | None = None) -> None:
        self.plugins_dir = plugins_dir or Path.cwd() / "plugins"
        self.plugins: dict[str, BasePlugin] = {}
        self.configs: dict[str, PluginConfig] = {}
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def load_plugin(self, plugin_name: str) -> bool:
        """Carga un plugin dinámicamente."""
        plugin_path = self.plugins_dir / plugin_name
        if not plugin_path.exists():
            log.error("[plugins] Plugin no encontrado: {}", plugin_name)
            return False

        try:
            # Cargar configuración
            config_file = plugin_path / "config.json"
            if not config_file.exists():
                log.error("[plugins] config.json no encontrado en {}", plugin_name)
                return False

            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            config = PluginConfig(**config_data)
            if not config.enabled:
                log.info("[plugins] Plugin deshabilitado: {}", plugin_name)
                return False

            # Cargar módulo
            module_path = plugin_path / config.handler.split(":")[0] + ".py"
            if not module_path.exists():
                log.error("[plugins] Módulo no encontrado: {}", module_path)
                return False

            spec = importlib.util.spec_from_file_location(plugin_name, module_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_name] = module
            spec.loader.exec_module(module)

            # Instanciar handler
            handler_class_name = config.handler.split(":")[1]
            handler_class = getattr(module, handler_class_name)
            plugin_instance: BasePlugin = handler_class()

            # Inicializar
            asyncio.run(plugin_instance.initialize())

            self.plugins[plugin_name] = plugin_instance
            self.configs[plugin_name] = config

            log.info("[plugins] Plugin cargado: {} v{}", config.name, config.version)
            return True

        except Exception as exc:  # noqa: BLE001
            log.error("[plugins] Error cargando plugin {}: {}", plugin_name, exc)
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """Descarga un plugin."""
        try:
            if plugin_name in self.plugins:
                import asyncio  # noqa: PLC0415
                plugin = self.plugins[plugin_name]
                asyncio.run(plugin.shutdown())
                del self.plugins[plugin_name]
                del self.configs[plugin_name]
                if plugin_name in sys.modules:
                    del sys.modules[plugin_name]
                log.info("[plugins] Plugin descargado: {}", plugin_name)
                return True
            return False
        except Exception as exc:  # noqa: BLE001
            log.error("[plugins] Error descargando plugin: {}", exc)
            return False

    async def process_command(self, text: str) -> str | None:
        """Permite que los plugins procesen el comando."""
        for plugin_name, plugin in self.plugins.items():
            try:
                result = await plugin.on_command(text)
                if result:
                    log.debug("[plugins] {} procesó comando", plugin_name)
                    return result
            except Exception as exc:  # noqa: BLE001
                log.error("[plugins] Error en {}: {}", plugin_name, exc)
        return None

    def list_plugins(self) -> list[dict[str, Any]]:
        """Lista todos los plugins disponibles y cargados."""
        available = []

        # Plugins cargados
        for name, config in self.configs.items():
            available.append({
                "name": config.name,
                "plugin_id": name,
                "version": config.version,
                "author": config.author,
                "description": config.description,
                "status": "loaded",
            })

        # Plugins disponibles no cargados
        for plugin_dir in self.plugins_dir.iterdir():
            if plugin_dir.is_dir() and plugin_dir.name not in self.configs:
                config_file = plugin_dir / "config.json"
                if config_file.exists():
                    try:
                        with open(config_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        available.append({
                            "name": data.get("name"),
                            "plugin_id": plugin_dir.name,
                            "version": data.get("version"),
                            "author": data.get("author"),
                            "description": data.get("description"),
                            "status": "available",
                        })
                    except Exception:  # noqa: BLE001
                        pass

        return available


import asyncio  # noqa: E402

plugin_manager = PluginManager()
