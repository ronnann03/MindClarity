"""Servicio de WhatsApp: enviar mensajes, leer chats."""
from __future__ import annotations

from typing import Any

from core.logger import log


class WhatsAppService:
    """Servicio para interactuar con WhatsApp Web via pywa.

    Requiere: pip install pywa
    Nota: Para usar, es necesario iniciar sesión una sola vez escaneando el QR.
    """

    def __init__(self) -> None:
        self.client = None
        self.authenticated = False
        self._init_client()

    def _init_client(self) -> None:
        """Inicializa el cliente de WhatsApp Web."""
        try:
            # pywa utiliza Selenium para controlar WhatsApp Web
            # La primera ejecución requiere que escanees el código QR
            from pywa import Client  # noqa: PLC0415

            self.client = Client(
                name="YU",
                phone_number_id="",  # Se configura tras autenticación
                business_account_access_token="",
            )
            self.authenticated = True
            log.info("[whatsapp] Cliente inicializado")
        except ImportError:
            log.warning(
                "[whatsapp] pywa no instalada. Ejecuta: pip install pywa"
            )
            self.authenticated = False
        except Exception as exc:  # noqa: BLE001
            log.error("[whatsapp] Error inicializando cliente: {}", exc)
            self.authenticated = False

    def send_message(self, phone: str, message: str) -> bool:
        """Envía un mensaje a un contacto de WhatsApp.

        Args:
            phone: Número de teléfono (ej: "+34612345678")
            message: Texto del mensaje
        """
        if not self.authenticated:
            log.warning("[whatsapp] No autenticado")
            return False

        if not phone or not message:
            log.warning("[whatsapp] Número o mensaje vacío")
            return False

        try:
            # Simulación: en producción se usaría self.client.send_message()
            log.info("[whatsapp] Mensaje a {}: {}", phone, message)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[whatsapp] Error enviando mensaje: {}", exc)
            return False

    def send_to_contact(self, contact_name: str, message: str) -> bool:
        """Envía un mensaje a un contacto por nombre.

        Args:
            contact_name: Nombre del contacto (ej: "Mamá", "Juan")
            message: Texto del mensaje
        """
        if not self.authenticated:
            log.warning("[whatsapp] No autenticado")
            return False

        try:
            # Simulación: buscaría el contacto en la lista de chats
            log.info("[whatsapp] Mensaje a {}: {}", contact_name, message)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[whatsapp] Error enviando mensaje a {}: {}", contact_name, exc)
            return False

    def get_unread_messages(self, limit: int = 5) -> list[dict[str, Any]]:
        """Obtiene los últimos mensajes sin leer.

        Returns:
            Lista de mensajes con formato:
            [{"from": "contacto", "message": "texto", "timestamp": ...}, ...]
        """
        if not self.authenticated:
            log.warning("[whatsapp] No autenticado")
            return []

        try:
            # Simulación: en producción usaría self.client.get_unread_messages()
            messages = [
                {
                    "from": "Contacto Simulado",
                    "message": "Este es un mensaje simulado de WhatsApp",
                    "timestamp": None,
                }
            ]
            log.info("[whatsapp] {} mensajes sin leer", len(messages))
            return messages[:limit]
        except Exception as exc:  # noqa: BLE001
            log.error("[whatsapp] Error obteniendo mensajes: {}", exc)
            return []

    def list_chats(self) -> list[str]:
        """Lista los nombres de los chats disponibles."""
        if not self.authenticated:
            log.warning("[whatsapp] No autenticado")
            return []

        try:
            # Simulación: en producción usaría self.client.get_chats()
            chats = [
                "Mamá",
                "Papá",
                "Juan",
                "Grupo Amigos",
                "Trabajo",
            ]
            log.info("[whatsapp] {} chats disponibles", len(chats))
            return chats
        except Exception as exc:  # noqa: BLE001
            log.error("[whatsapp] Error listando chats: {}", exc)
            return []

    def authenticate(self) -> bool:
        """Inicia el proceso de autenticación (requiere escanear QR)."""
        if self.authenticated:
            log.info("[whatsapp] Ya autenticado")
            return True

        try:
            log.info("[whatsapp] Iniciando autenticación... Escanea el código QR")
            # En producción: self.client.connect()
            self.authenticated = True
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[whatsapp] Error en autenticación: {}", exc)
            self.authenticated = False
            return False


whatsapp_service = WhatsAppService()
