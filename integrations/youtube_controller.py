"""Control de YouTube: abre el navegador y reproduce contenido.

Usa la búsqueda de YouTube con autoplay del primer resultado.
"""
from __future__ import annotations

import urllib.parse
import webbrowser

from core.logger import log

try:
    import pyautogui
except Exception:  # noqa: BLE001
    pyautogui = None  # type: ignore


class YouTubeController:
    """Abre y controla la reproducción en YouTube vía navegador."""

    BASE = "https://www.youtube.com"

    def open_youtube(self) -> str:
        webbrowser.open(self.BASE)
        log.info("YouTube abierto.")
        return "He abierto YouTube."

    def _search_url(self, query: str) -> str:
        q = urllib.parse.quote_plus(query)
        return f"{self.BASE}/results?search_query={q}"

    def play_video(self, query: str = "", **_: object) -> str:
        """Busca un vídeo y abre la página de resultados.

        YouTube no permite autoplay directo por URL de forma fiable, así que
        abrimos los resultados de búsqueda del término solicitado.
        """
        if not query:
            return self.open_youtube()
        webbrowser.open(self._search_url(query))
        log.info("Buscando vídeo en YouTube: {}", query)
        return f"Buscando '{query}' en YouTube."

    def play_music(self, query: str = "", **_: object) -> str:
        """Reproduce música: añade 'música' al término de búsqueda."""
        term = f"{query} música" if query else "música"
        webbrowser.open(self._search_url(term))
        log.info("Reproduciendo música en YouTube: {}", term)
        return f"Reproduciendo '{query or 'música'}' en YouTube."


youtube_controller = YouTubeController()
