"""Controlador de navegador: abrir URLs, búsquedas, navegar."""
from __future__ import annotations

import webbrowser
from typing import Any

from core.logger import log


class BrowserController:
    """Controla el navegador predeterminado del sistema."""

    def __init__(self) -> None:
        self.default_browser = webbrowser.get()

    def open_url(self, url: str) -> bool:
        """Abre una URL en el navegador."""
        if not url:
            log.warning("[browser] URL vacía")
            return False

        # Asegura que la URL tenga protocolo
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        try:
            webbrowser.open(url)
            log.info("[browser] Abierto: {}", url)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[browser] Error abriendo URL: {}", exc)
            return False

    def search(self, query: str, engine: str = "google") -> bool:
        """Realiza una búsqueda en el navegador."""
        if not query:
            log.warning("[browser] Query vacío")
            return False

        # URLs de búsqueda populares
        search_engines = {
            "google": "https://www.google.com/search?q={}",
            "bing": "https://www.bing.com/search?q={}",
            "duckduckgo": "https://duckduckgo.com/?q={}",
            "youtube": "https://www.youtube.com/results?search_query={}",
        }

        url_template = search_engines.get(engine, search_engines["google"])
        search_url = url_template.format(query.replace(" ", "+"))

        return self.open_url(search_url)

    def open_mail(self) -> bool:
        """Abre Gmail en el navegador."""
        return self.open_url("https://mail.google.com")

    def open_maps(self, location: str = "") -> bool:
        """Abre Google Maps (opcionalmente con una ubicación)."""
        if location:
            return self.search(location, engine="google")
        return self.open_url("https://maps.google.com")

    def open_youtube(self, query: str = "") -> bool:
        """Abre YouTube (opcionalmente con una búsqueda)."""
        if query:
            return self.search(query, engine="youtube")
        return self.open_url("https://www.youtube.com")

    def open_github(self) -> bool:
        """Abre GitHub."""
        return self.open_url("https://github.com")

    def open_website(self, domain: str) -> bool:
        """Abre un sitio web por dominio."""
        if not domain:
            return False
        url = domain if domain.startswith("http") else f"https://{domain}"
        return self.open_url(url)


browser_controller = BrowserController()
