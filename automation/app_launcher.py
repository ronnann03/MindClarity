"""Lanzador de aplicaciones de Windows.

Abre y cierra aplicaciones, detecta apps comunes y lista procesos en ejecución.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

import psutil

from core.logger import log

# Mapeo de nombres comunes a ejecutables / comandos.
KNOWN_APPS: dict[str, str] = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "navegador": "chrome.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
    "bloc de notas": "notepad.exe",
    "notepad": "notepad.exe",
    "calculadora": "calc.exe",
    "calculator": "calc.exe",
    "explorador": "explorer.exe",
    "explorer": "explorer.exe",
    "paint": "mspaint.exe",
    "cmd": "cmd.exe",
    "terminal": "wt.exe",
    "powershell": "powershell.exe",
    "spotify": "spotify.exe",
    "discord": "discord.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "configuracion": "ms-settings:",
    "ajustes": "ms-settings:",
}


class AppLauncher:
    """Gestiona la apertura y cierre de aplicaciones."""

    def _resolve(self, name: str) -> str:
        """Resuelve un nombre amigable a un ejecutable/comando."""
        key = name.lower().strip().rstrip('.!?').strip()
        if key in KNOWN_APPS:
            return KNOWN_APPS[key]
        # Si parece un ejecutable directo, úsalo tal cual.
        return name

    def open_app(self, name: str) -> str:
        """Abre una aplicación por nombre."""
        target = self._resolve(name)
        try:
            if target.endswith(":"):  # URI de Windows (ms-settings:)
                os.startfile(target)  # type: ignore[attr-defined]
            elif shutil.which(target) or os.path.exists(target):
                subprocess.Popen([target], shell=False)
            else:
                # Intento mediante el shell (PATH / asociaciones del sistema).
                os.startfile(target)  # type: ignore[attr-defined]
            log.info("Aplicación abierta: {}", name)
            return f"He abierto {name}."
        except FileNotFoundError:
            log.warning("App no encontrada: {}", name)
            return f"No encuentro la aplicación '{name}'."
        except Exception as exc:  # noqa: BLE001
            log.error("Error abriendo {}: {}", name, exc)
            return f"No pude abrir '{name}': {exc}"

    def close_app(self, name: str) -> str:
        """Cierra todos los procesos cuyo nombre coincida."""
        target = self._resolve(name).lower().replace(".exe", "")
        closed = 0
        for proc in psutil.process_iter(["name"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                if target in pname:
                    proc.terminate()
                    closed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if closed:
            log.info("Cerrados {} proceso(s) de '{}'.", closed, name)
            return f"He cerrado {name}."
        return f"No encontré '{name}' en ejecución."

    def list_running_apps(self) -> list[dict[str, Any]]:
        """Devuelve la lista de procesos con ventana visible relevantes."""
        apps: list[dict[str, Any]] = []
        seen: set[str] = set()
        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                name = proc.info.get("name") or ""
                if name and name not in seen:
                    seen.add(name)
                    mem = proc.info.get("memory_info")
                    apps.append({
                        "pid": proc.info.get("pid"),
                        "name": name,
                        "memory_mb": round(mem.rss / 1_048_576, 1) if mem else 0,
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return sorted(apps, key=lambda a: a["memory_mb"], reverse=True)


app_launcher = AppLauncher()
