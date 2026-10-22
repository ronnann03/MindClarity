"""Gestión de archivos y carpetas con seguridad en operaciones destructivas.

Las eliminaciones envían a la papelera de reciclaje (si send2trash está disponible).
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from core.logger import log

try:
    from send2trash import send2trash
except Exception:  # noqa: BLE001
    send2trash = None  # type: ignore


def _expand(path: str) -> Path:
    """Expande variables de entorno y `~` a una ruta absoluta."""
    return Path(path).expanduser().resolve()


class FileManager:
    """CRUD de archivos y carpetas."""

    def create_file(self, path: str, content: str = "") -> str:
        p = _expand(path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            log.info("Archivo creado: {}", p)
            return f"Archivo creado en {p}."
        except Exception as exc:  # noqa: BLE001
            log.error("Error creando archivo {}: {}", p, exc)
            return f"No pude crear el archivo: {exc}"

    def create_folder(self, path: str) -> str:
        p = _expand(path)
        try:
            p.mkdir(parents=True, exist_ok=True)
            log.info("Carpeta creada: {}", p)
            return f"Carpeta creada en {p}."
        except Exception as exc:  # noqa: BLE001
            return f"No pude crear la carpeta: {exc}"

    def delete_file(self, path: str) -> str:
        """Envía un archivo a la papelera de reciclaje (operación reversible)."""
        p = _expand(path)
        if not p.exists():
            return f"No existe: {p}."
        if p.is_dir():
            return f"'{p.name}' es una carpeta. Usa 'eliminar carpeta' para borrarla."
        try:
            if send2trash is not None:
                send2trash(str(p))
                log.info("Archivo enviado a la papelera: {}", p)
                return f"He enviado el archivo '{p.name}' a la papelera."
            p.unlink()
            log.warning("Archivo borrado permanentemente (sin papelera): {}", p)
            return f"He borrado '{p.name}' (permanente, no había papelera disponible)."
        except Exception as exc:  # noqa: BLE001
            log.error("Error borrando archivo {}: {}", p, exc)
            return f"No pude borrar el archivo: {exc}"

    def delete_folder(self, path: str) -> str:
        """Envía una carpeta completa a la papelera de reciclaje.

        Usa send2trash cuando está disponible (reversible); en caso contrario
        elimina recursivamente con advertencia de que es permanente.
        """
        p = _expand(path)
        if not p.exists():
            return f"No existe la carpeta: {p}."
        if not p.is_dir():
            return f"'{p.name}' no es una carpeta. Usa 'eliminar archivo' en su lugar."
        try:
            if send2trash is not None:
                send2trash(str(p))
                log.info("Carpeta enviada a la papelera: {}", p)
                return f"He enviado la carpeta '{p.name}' a la papelera."
            shutil.rmtree(p)
            log.warning("Carpeta borrada permanentemente (sin papelera): {}", p)
            return f"He borrado la carpeta '{p.name}' (permanente, no había papelera disponible)."
        except Exception as exc:  # noqa: BLE001
            log.error("Error borrando carpeta {}: {}", p, exc)
            return f"No pude borrar la carpeta: {exc}"

    def move_file(self, source: str, destination: str) -> str:
        src, dst = _expand(source), _expand(destination)
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            log.info("Movido {} -> {}", src, dst)
            return f"Moví '{src.name}' a {dst}."
        except Exception as exc:  # noqa: BLE001
            return f"No pude mover el archivo: {exc}"

    def copy_file(self, source: str, destination: str) -> str:
        src, dst = _expand(source), _expand(destination)
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            log.info("Copiado {} -> {}", src, dst)
            return f"Copié '{src.name}' a {dst}."
        except Exception as exc:  # noqa: BLE001
            return f"No pude copiar el archivo: {exc}"

    def list_directory(self, path: str = ".") -> list[dict[str, Any]]:
        p = _expand(path)
        if not p.is_dir():
            return []
        items: list[dict[str, Any]] = []
        try:
            for entry in p.iterdir():
                items.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": entry.stat().st_size if entry.is_file() else 0,
                })
        except Exception as exc:  # noqa: BLE001
            log.error("Error listando {}: {}", p, exc)
        return items

    def search_files(self, root: str, pattern: str, limit: int = 100) -> list[str]:
        """Busca archivos por patrón glob de forma recursiva."""
        base = _expand(root)
        results: list[str] = []
        try:
            for match in base.rglob(pattern):
                results.append(str(match))
                if len(results) >= limit:
                    break
        except Exception as exc:  # noqa: BLE001
            log.error("Error buscando '{}' en {}: {}", pattern, base, exc)
        return results


file_manager = FileManager()
