"""Agente de Office y Spotify: control integrado de aplicaciones."""
from __future__ import annotations

from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from core.logger import log
from integrations.office_controller import office_controller
from integrations.spotify_controller import spotify_controller


class OfficeSpotifyAgent(BaseAgent):
    """Maneja tareas de Office (Word, Excel, PowerPoint, Outlook) y Spotify."""

    name = "office_spotify_agent"

    async def execute(  # type: ignore[override]
        self,
        action: str | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        """Ejecuta comandos de Office o Spotify.

        Acciones Office:
        - open_word, create_word, open_excel, create_excel, open_powerpoint,
          create_powerpoint, open_outlook, send_email

        Acciones Spotify:
        - play_spotify, pause_spotify, next_track, previous_track, search_spotify
        """
        if not action:
            action, kwargs = await self._infer_action(kwargs)

        match action:
            # ---- Word ---- #
            case "open_word":
                return self._open_word(**kwargs)
            case "create_word":
                return self._create_word(**kwargs)

            # ---- Excel ---- #
            case "open_excel":
                return self._open_excel(**kwargs)
            case "create_excel":
                return self._create_excel(**kwargs)

            # ---- PowerPoint ---- #
            case "open_powerpoint":
                return self._open_powerpoint(**kwargs)
            case "create_powerpoint":
                return self._create_powerpoint(**kwargs)

            # ---- Outlook ---- #
            case "open_outlook":
                return self._open_outlook(**kwargs)
            case "send_email":
                return self._send_email(**kwargs)

            # ---- Spotify ---- #
            case "play_spotify":
                return self._play_spotify(**kwargs)
            case "pause_spotify":
                return self._pause_spotify(**kwargs)
            case "next_track":
                return self._next_track(**kwargs)
            case "previous_track":
                return self._previous_track(**kwargs)
            case "search_spotify":
                return self._search_spotify(**kwargs)
            case "set_volume":
                return self._set_volume(**kwargs)

            case _:
                return self._fail(f"Acción no soportada: '{action}'")

    # ---- Word ---- #
    def _open_word(self, file_path: str = "", **_: Any) -> AgentResult:
        """Abre Word (con archivo opcional)."""
        success = office_controller.open_word(file_path or None)
        if success:
            msg = f"Word abierto con {file_path}" if file_path else "Word abierto"
            return self._ok(output={"app": "word", "file": file_path}, message=msg)
        return self._fail("No se pudo abrir Word")

    def _create_word(self, content: str = "", file_path: str = "", **_: Any) -> AgentResult:
        """Crea un documento de Word."""
        if not content or not file_path:
            return self._fail("Contenido y ruta requeridos")

        success = office_controller.create_word_document(content, file_path)
        if success:
            return self._ok(
                output={"file": file_path},
                message=f"Documento Word creado: {file_path}"
            )
        return self._fail("No se pudo crear documento Word")

    # ---- Excel ---- #
    def _open_excel(self, file_path: str = "", **_: Any) -> AgentResult:
        """Abre Excel (con archivo opcional)."""
        success = office_controller.open_excel(file_path or None)
        if success:
            msg = f"Excel abierto con {file_path}" if file_path else "Excel abierto"
            return self._ok(output={"app": "excel", "file": file_path}, message=msg)
        return self._fail("No se pudo abrir Excel")

    def _create_excel(self, data: list[list[Any]] | None = None, file_path: str = "", **_: Any) -> AgentResult:
        """Crea una hoja de Excel."""
        if not data or not file_path:
            return self._fail("Datos y ruta requeridos")

        success = office_controller.create_excel_spreadsheet(data, file_path)
        if success:
            return self._ok(
                output={"file": file_path, "rows": len(data)},
                message=f"Hoja Excel creada: {file_path} ({len(data)} filas)"
            )
        return self._fail("No se pudo crear hoja Excel")

    # ---- PowerPoint ---- #
    def _open_powerpoint(self, file_path: str = "", **_: Any) -> AgentResult:
        """Abre PowerPoint (con archivo opcional)."""
        success = office_controller.open_powerpoint(file_path or None)
        if success:
            msg = f"PowerPoint abierto con {file_path}" if file_path else "PowerPoint abierto"
            return self._ok(output={"app": "powerpoint", "file": file_path}, message=msg)
        return self._fail("No se pudo abrir PowerPoint")

    def _create_powerpoint(self, slides: list[dict[str, str]] | None = None, file_path: str = "", **_: Any) -> AgentResult:
        """Crea una presentación PowerPoint."""
        if not slides or not file_path:
            return self._fail("Diapositivas y ruta requeridas")

        success = office_controller.create_powerpoint_presentation(slides, file_path)
        if success:
            return self._ok(
                output={"file": file_path, "slides": len(slides)},
                message=f"Presentación PowerPoint creada: {file_path} ({len(slides)} diapositivas)"
            )
        return self._fail("No se pudo crear presentación PowerPoint")

    # ---- Outlook ---- #
    def _open_outlook(self, **_: Any) -> AgentResult:
        """Abre Outlook."""
        success = office_controller.open_outlook()
        if success:
            return self._ok(output={"app": "outlook"}, message="Outlook abierto")
        return self._fail("No se pudo abrir Outlook")

    def _send_email(self, to: str = "", subject: str = "", body: str = "", **_: Any) -> AgentResult:
        """Envía un email via Outlook."""
        if not to or not subject or not body:
            return self._fail("Destinatario, asunto y cuerpo requeridos")

        success = office_controller.send_email(to, subject, body)
        if success:
            return self._ok(
                output={"to": to, "subject": subject},
                message=f"Email enviado a {to}: {subject}"
            )
        return self._fail(f"No se pudo enviar email a {to}")

    # ---- Spotify ---- #
    def _play_spotify(self, query: str = "", **_: Any) -> AgentResult:
        """Reproduce una canción en Spotify."""
        if not query:
            return self._fail("Especifica una canción")

        success = spotify_controller.play(query)
        if success:
            return self._ok(
                output={"query": query},
                message=f"Reproduciendo: {query}"
            )
        return self._fail(f"No se pudo reproducir: {query}")

    def _pause_spotify(self, **_: Any) -> AgentResult:
        """Pausa Spotify."""
        success = spotify_controller.pause()
        if success:
            return self._ok(output={}, message="Spotify pausado")
        return self._fail("No se pudo pausar Spotify")

    def _next_track(self, **_: Any) -> AgentResult:
        """Salta a la siguiente canción."""
        success = spotify_controller.next_track()
        if success:
            return self._ok(output={}, message="Saltando a siguiente canción")
        return self._fail("No se pudo saltar canción")

    def _previous_track(self, **_: Any) -> AgentResult:
        """Vuelve a la canción anterior."""
        success = spotify_controller.previous_track()
        if success:
            return self._ok(output={}, message="Volviendo a canción anterior")
        return self._fail("No se pudo volver atrás")

    def _search_spotify(self, query: str = "", search_type: str = "track", **_: Any) -> AgentResult:
        """Busca en Spotify."""
        if not query:
            return self._fail("Especifica qué buscar")

        results = spotify_controller.search(query, search_type)
        if results:
            summary = f"Resultados ({len(results)}):\n"
            for item in results[:5]:
                summary += f"• {item.get('name', '')}\n"
            return self._ok(output=results, message=summary)
        return self._fail(f"No se encontraron resultados para: {query}")

    def _set_volume(self, volume: int = 50, **_: Any) -> AgentResult:
        """Ajusta el volumen de Spotify."""
        success = spotify_controller.set_volume(volume)
        if success:
            return self._ok(
                output={"volume": volume},
                message=f"Volumen Spotify: {volume}%"
            )
        return self._fail("No se pudo ajustar volumen")

    async def _infer_action(self, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Infiere la acción a partir del texto."""
        text = kwargs.get("query") or kwargs.get("text") or str(kwargs)
        prompt = (
            f"Dado el comando: '{text}', identifica la acción (Office o Spotify). "
            f"Acciones Office: open_word, create_word, open_excel, create_excel, "
            f"open_powerpoint, create_powerpoint, open_outlook, send_email. "
            f"Acciones Spotify: play_spotify, pause_spotify, next_track, previous_track, "
            f"search_spotify, set_volume. "
            f"Responde solo con el nombre de la acción."
        )
        action = (await self.ask_llm(prompt)).strip().split()[0] if text else ""
        log.debug("[office_spotify_agent] Acción inferida: {}", action)
        return action, kwargs


office_spotify_agent = OfficeSpotifyAgent()
