"""Gestión de ventanas de Windows con pygetwindow."""
from __future__ import annotations

from typing import Any

from core.logger import log

try:
    import pygetwindow as gw
except Exception:  # noqa: BLE001
    gw = None  # type: ignore


class WindowManager:
    """Controla las ventanas abiertas: minimizar, maximizar, mover, etc."""

    def _find(self, title: str):
        """Busca la primera ventana cuyo título contenga `title`."""
        if gw is None:
            return None
        matches = [w for w in gw.getAllWindows() if title.lower() in (w.title or "").lower()]
        return matches[0] if matches else None

    def get_windows_list(self) -> list[dict[str, Any]]:
        """Lista las ventanas con título visible."""
        if gw is None:
            return []
        result: list[dict[str, Any]] = []
        for w in gw.getAllWindows():
            if w.title:
                result.append({
                    "title": w.title,
                    "left": w.left, "top": w.top,
                    "width": w.width, "height": w.height,
                    "minimized": w.isMinimized, "maximized": w.isMaximized,
                })
        return result

    def minimize(self, title: str) -> str:
        w = self._find(title)
        if w:
            w.minimize()
            return f"Ventana '{title}' minimizada."
        return f"No encontré la ventana '{title}'."

    def maximize(self, title: str) -> str:
        w = self._find(title)
        if w:
            w.maximize()
            return f"Ventana '{title}' maximizada."
        return f"No encontré la ventana '{title}'."

    def restore(self, title: str) -> str:
        w = self._find(title)
        if w:
            w.restore()
            return f"Ventana '{title}' restaurada."
        return f"No encontré la ventana '{title}'."

    def focus(self, title: str) -> str:
        w = self._find(title)
        if w:
            try:
                w.activate()
            except Exception:  # noqa: BLE001
                w.minimize(); w.restore()
            return f"Ventana '{title}' en primer plano."
        return f"No encontré la ventana '{title}'."

    def move(self, title: str, x: int, y: int) -> str:
        w = self._find(title)
        if w:
            w.moveTo(int(x), int(y))
            return f"Ventana '{title}' movida a ({x}, {y})."
        return f"No encontré la ventana '{title}'."

    def resize(self, title: str, width: int, height: int) -> str:
        w = self._find(title)
        if w:
            w.resizeTo(int(width), int(height))
            return f"Ventana '{title}' redimensionada a {width}x{height}."
        return f"No encontré la ventana '{title}'."

    def close(self, title: str) -> str:
        w = self._find(title)
        if w:
            w.close()
            return f"Ventana '{title}' cerrada."
        return f"No encontré la ventana '{title}'."


window_manager = WindowManager()
