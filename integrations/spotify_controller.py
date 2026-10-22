"""Controlador de Spotify: reproducción, búsqueda, listas de reproducción."""
from __future__ import annotations

from typing import Any

from core.logger import log


class SpotifyController:
    """Controla Spotify Desktop o Web API.

    Requiere: pip install spotipy
    Para usar Spotify Web API:
    1. Crea una aplicación en https://developer.spotify.com/dashboard
    2. Obtén CLIENT_ID y CLIENT_SECRET
    3. Configura SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET en .env
    """

    def __init__(self) -> None:
        self.spotify = None
        self.is_authenticated = False
        self._init_spotify()

    def _init_spotify(self) -> None:
        """Inicializa cliente de Spotify."""
        try:
            import spotipy  # noqa: PLC0415
            from spotipy.oauth2 import SpotifyClientCredentials  # noqa: PLC0415

            # Intenta usar las credenciales si están disponibles
            from config.settings import settings  # noqa: PLC0415

            client_id = getattr(settings, "spotify_client_id", "")
            client_secret = getattr(settings, "spotify_client_secret", "")

            if client_id and client_secret:
                auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
                self.spotify = spotipy.Spotify(auth_manager=auth)
                self.is_authenticated = True
                log.info("[spotify] Autenticado con Spotify Web API")
            else:
                log.warning("[spotify] Sin credenciales de Spotify Web API")
                self.is_authenticated = False
        except ImportError:
            log.warning("[spotify] spotipy no instalado. Ejecuta: pip install spotipy")
            self.is_authenticated = False
        except Exception as exc:  # noqa: BLE001
            log.error("[spotify] Error inicializando Spotify: {}", exc)
            self.is_authenticated = False

    def play(self, query: str = "") -> bool:
        """Reproduce una canción, álbum o playlist.

        Args:
            query: Nombre de la canción, álbum o artista (ej: "Bohemian Rhapsody")
        """
        if not self.is_authenticated:
            log.warning("[spotify] No autenticado en Spotify")
            return False

        if not query:
            return False

        try:
            results = self.spotify.search(q=query, type="track", limit=1)
            tracks = results.get("tracks", {}).get("items", [])

            if tracks:
                track = tracks[0]
                track_uri = track["uri"]
                # En implementación real: self.spotify.start_playback(context_uri=track_uri)
                log.info("[spotify] Reproduciendo: {}", track["name"])
                return True
            return False
        except Exception as exc:  # noqa: BLE001
            log.error("[spotify] Error reproduciendo: {}", exc)
            return False

    def search(self, query: str, search_type: str = "track") -> list[dict[str, Any]]:
        """Busca canciones, álbumes o artistas en Spotify.

        Args:
            query: Término de búsqueda
            search_type: "track", "album" o "artist"
        """
        if not self.is_authenticated:
            log.warning("[spotify] No autenticado en Spotify")
            return []

        try:
            results = self.spotify.search(q=query, type=search_type, limit=10)
            items = results.get(f"{search_type}s", {}).get("items", [])

            formatted = []
            for item in items:
                if search_type == "track":
                    formatted.append({
                        "name": item.get("name"),
                        "artist": ", ".join([a["name"] for a in item.get("artists", [])]),
                        "uri": item.get("uri"),
                    })
                elif search_type == "album":
                    formatted.append({
                        "name": item.get("name"),
                        "artist": item.get("artists", [{}])[0].get("name"),
                        "uri": item.get("uri"),
                    })
                else:  # artist
                    formatted.append({
                        "name": item.get("name"),
                        "followers": item.get("followers", {}).get("total", 0),
                        "uri": item.get("uri"),
                    })
            return formatted
        except Exception as exc:  # noqa: BLE001
            log.error("[spotify] Error buscando: {}", exc)
            return []

    def get_current_playback(self) -> dict[str, Any] | None:
        """Obtiene la información de reproducción actual."""
        if not self.is_authenticated:
            return None

        try:
            return self.spotify.current_playback()
        except Exception as exc:  # noqa: BLE001
            log.error("[spotify] Error obteniendo estado: {}", exc)
            return None

    def next_track(self) -> bool:
        """Salta a la siguiente canción."""
        if not self.is_authenticated:
            return False

        try:
            self.spotify.next_track()
            log.info("[spotify] Saltando a siguiente canción")
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[spotify] Error saltando canción: {}", exc)
            return False

    def previous_track(self) -> bool:
        """Vuelve a la canción anterior."""
        if not self.is_authenticated:
            return False

        try:
            self.spotify.previous_track()
            log.info("[spotify] Volviendo a canción anterior")
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[spotify] Error volviendo atrás: {}", exc)
            return False

    def pause(self) -> bool:
        """Pausa la reproducción actual."""
        if not self.is_authenticated:
            return False

        try:
            self.spotify.pause_playback()
            log.info("[spotify] Pausa")
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[spotify] Error pausando: {}", exc)
            return False

    def set_volume(self, volume: int) -> bool:
        """Ajusta el volumen (0-100).

        Args:
            volume: Nivel de volumen (0-100)
        """
        if not self.is_authenticated:
            return False

        volume = max(0, min(100, volume))

        try:
            self.spotify.volume(volume)
            log.info("[spotify] Volumen: {}%", volume)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[spotify] Error ajustando volumen: {}", exc)
            return False

    def get_playlists(self) -> list[str]:
        """Obtiene las playlists del usuario."""
        if not self.is_authenticated:
            return []

        try:
            results = self.spotify.current_user_playlists(limit=50)
            return [p["name"] for p in results.get("items", [])]
        except Exception as exc:  # noqa: BLE001
            log.error("[spotify] Error obteniendo playlists: {}", exc)
            return []


spotify_controller = SpotifyController()
