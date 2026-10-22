"""Agente web: control de navegador, búsquedas, WhatsApp."""
from __future__ import annotations

from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from core.logger import log
from integrations.browser_controller import browser_controller
from integrations.whatsapp_service import whatsapp_service


class WebAgent(BaseAgent):
    """Maneja tareas web: navegador, búsquedas y WhatsApp."""

    name = "web_agent"

    async def execute(  # type: ignore[override]
        self,
        action: str | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        """Ejecuta comandos web.

        Acciones soportadas:
        - open_url: abrir una URL
        - search: buscar en la web
        - open_youtube: abrir YouTube
        - open_maps: abrir Maps
        - open_gmail: abrir Gmail
        - whatsapp_send: enviar mensaje por WhatsApp
        - whatsapp_read: leer mensajes de WhatsApp
        - whatsapp_list_chats: listar chats de WhatsApp
        """
        if not action:
            action, kwargs = await self._infer_action(kwargs)

        match action:
            case "open_url":
                return self._open_url(**kwargs)
            case "search":
                return self._search(**kwargs)
            case "open_youtube":
                return self._open_youtube(**kwargs)
            case "open_maps":
                return self._open_maps(**kwargs)
            case "open_gmail":
                return self._open_gmail(**kwargs)
            case "whatsapp_send":
                return self._whatsapp_send(**kwargs)
            case "whatsapp_read":
                return self._whatsapp_read(**kwargs)
            case "whatsapp_list_chats":
                return self._whatsapp_list_chats(**kwargs)
            case _:
                return self._fail(f"Acción web no soportada: '{action}'")

    def _open_url(self, url: str = "", **_: Any) -> AgentResult:
        """Abre una URL en el navegador."""
        if not url:
            return self._fail("URL requerida")

        success = browser_controller.open_url(url)
        if success:
            return self._ok(output={"url": url}, message=f"Abriendo {url}...")
        return self._fail(f"No se pudo abrir {url}")

    def _search(self, query: str = "", engine: str = "google", **_: Any) -> AgentResult:
        """Realiza una búsqueda en la web."""
        if not query:
            return self._fail("Búsqueda requerida")

        success = browser_controller.search(query, engine)
        if success:
            return self._ok(output={"query": query, "engine": engine}, message=f"Buscando '{query}' en {engine}...")
        return self._fail(f"Error en la búsqueda")

    def _open_youtube(self, query: str = "", **_: Any) -> AgentResult:
        """Abre YouTube (opcionalmente con una búsqueda)."""
        success = browser_controller.open_youtube(query)
        if success:
            message = f"Abriendo YouTube{'...' if not query else f' - Buscando {query}'}"
            return self._ok(output={"query": query}, message=message)
        return self._fail("Error abriendo YouTube")

    def _open_maps(self, location: str = "", **_: Any) -> AgentResult:
        """Abre Google Maps (opcionalmente con una ubicación)."""
        success = browser_controller.open_maps(location)
        if success:
            message = f"Abriendo Maps{'...' if not location else f' - {location}'}"
            return self._ok(output={"location": location}, message=message)
        return self._fail("Error abriendo Maps")

    def _open_gmail(self, **_: Any) -> AgentResult:
        """Abre Gmail."""
        success = browser_controller.open_mail()
        if success:
            return self._ok(output={}, message="Abriendo Gmail...")
        return self._fail("Error abriendo Gmail")

    def _whatsapp_send(self, contact: str = "", message: str = "", **_: Any) -> AgentResult:
        """Envía un mensaje por WhatsApp."""
        if not contact or not message:
            return self._fail("Contacto y mensaje requeridos")

        # Intenta enviar por nombre de contacto primero
        success = whatsapp_service.send_to_contact(contact, message)
        if success:
            return self._ok(
                output={"contact": contact, "message": message},
                message=f"Mensaje enviado a {contact}"
            )
        return self._fail(f"No se pudo enviar mensaje a {contact}")

    def _whatsapp_read(self, **_: Any) -> AgentResult:
        """Lee mensajes sin leer de WhatsApp."""
        messages = whatsapp_service.get_unread_messages()
        if messages:
            summary = "Mensajes sin leer:\n"
            for msg in messages:
                summary += f"• {msg['from']}: {msg['message']}\n"
            return self._ok(output=messages, message=summary)
        return self._ok(output=[], message="No hay mensajes sin leer")

    def _whatsapp_list_chats(self, **_: Any) -> AgentResult:
        """Lista los chats disponibles en WhatsApp."""
        chats = whatsapp_service.list_chats()
        if chats:
            summary = "Chats disponibles:\n" + "\n".join(f"• {chat}" for chat in chats)
            return self._ok(output=chats, message=summary)
        return self._ok(output=[], message="No hay chats disponibles")

    async def _infer_action(self, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Infiere la acción a partir del texto."""
        text = kwargs.get("query") or kwargs.get("text") or str(kwargs)
        prompt = (
            f"Dado el comando: '{text}', identifica la acción web. "
            f"Opciones: open_url, search, open_youtube, open_maps, open_gmail, "
            f"whatsapp_send, whatsapp_read, whatsapp_list_chats. "
            f"Responde solo con el nombre de la acción."
        )
        action = (await self.ask_llm(prompt)).strip().split()[0] if text else ""
        log.debug("[web_agent] Acción inferida: {}", action)
        return action, kwargs


web_agent = WebAgent()
