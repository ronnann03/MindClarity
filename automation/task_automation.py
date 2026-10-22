"""Automatizaciones complejas: organizar descargas, renombrar en lote, etc."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from core.logger import log

# Categorías de organización por extensión.
CATEGORIES: dict[str, set[str]] = {
    "Imagenes": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"},
    "Documentos": {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"},
    "Videos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
    "Comprimidos": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Programas": {".exe", ".msi", ".bat"},
}


class TaskAutomation:
    """Tareas automatizadas de mantenimiento y organización."""

    def organize_downloads(self, folder: str | None = None) -> str:
        """Organiza la carpeta de descargas por tipo de archivo."""
        downloads = Path(folder) if folder else Path.home() / "Downloads"
        if not downloads.is_dir():
            return f"No encuentro la carpeta {downloads}."
        moved = 0
        try:
            for item in downloads.iterdir():
                if item.is_file():
                    category = self._category_for(item.suffix.lower())
                    target_dir = downloads / category
                    target_dir.mkdir(exist_ok=True)
                    shutil.move(str(item), str(target_dir / item.name))
                    moved += 1
            log.info("Organizados {} archivos en {}.", moved, downloads)
            return f"He organizado {moved} archivos en {downloads}."
        except Exception as exc:  # noqa: BLE001
            log.error("Error organizando descargas: {}", exc)
            return f"Error organizando: {exc}"

    @staticmethod
    def _category_for(ext: str) -> str:
        for category, exts in CATEGORIES.items():
            if ext in exts:
                return category
        return "Otros"

    def bulk_rename(self, folder: str, prefix: str, start: int = 1) -> str:
        """Renombra en lote los archivos de una carpeta con un prefijo + número."""
        base = Path(folder).expanduser()
        if not base.is_dir():
            return f"No encuentro la carpeta {base}."
        count = start
        renamed = 0
        try:
            for item in sorted(base.iterdir()):
                if item.is_file():
                    new_name = f"{prefix}_{count:03d}{item.suffix}"
                    item.rename(base / new_name)
                    count += 1
                    renamed += 1
            return f"He renombrado {renamed} archivos con el prefijo '{prefix}'."
        except Exception as exc:  # noqa: BLE001
            return f"Error renombrando: {exc}"

    def create_shortcut(self, target: str, shortcut_path: str) -> str:
        """Crea un acceso directo (.lnk) en Windows."""
        try:
            import pythoncom  # type: ignore
            from win32com.client import Dispatch  # type: ignore

            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(str(Path(shortcut_path).with_suffix(".lnk")))
            shortcut.TargetPath = target
            shortcut.save()
            return f"Acceso directo creado en {shortcut_path}."
        except Exception as exc:  # noqa: BLE001
            log.error("Error creando acceso directo: {}", exc)
            return f"No pude crear el acceso directo: {exc}"

    def schedule_task(self, name: str, command: str, time_str: str) -> str:
        """Programa una tarea con el Programador de tareas de Windows (schtasks).

        Usa subprocess.run con lista de argumentos (sin shell=True) para evitar
        inyección de comandos.
        """
        try:
            result = subprocess.run(
                [
                    "schtasks", "/create",
                    "/tn", name,
                    "/tr", command,
                    "/sc", "once",
                    "/st", time_str,
                    "/f",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                err = result.stderr.strip() or result.stdout.strip()
                log.error("schtasks error: {}", err)
                return f"No pude programar la tarea: {err}"
            log.info("Tarea '{}' programada para las {}.", name, time_str)
            return f"Tarea '{name}' programada para las {time_str}."
        except Exception as exc:  # noqa: BLE001
            return f"No pude programar la tarea: {exc}"


task_automation = TaskAutomation()
