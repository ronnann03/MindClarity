"""Controlador de Google Drive: acceso a archivos en la nube."""
from __future__ import annotations

from typing import Any

from core.logger import log


class GoogleDriveController:
    """Integración con Google Drive para almacenamiento en la nube.

    Requiere: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
    Usa el mismo credentials.json de Google Calendar/Gmail
    """

    def __init__(self) -> None:
        self.service = None
        self.is_authenticated = False
        self._init_drive()

    def _init_drive(self) -> None:
        """Inicializa el cliente de Google Drive."""
        try:
            from google.auth.transport.requests import Request  # noqa: PLC0415
            from google.oauth2.service_account import Credentials  # noqa: PLC0415
            from googleapiclient.discovery import build  # noqa: PLC0415
            from pathlib import Path  # noqa: PLC0415

            creds_path = Path.cwd() / "credentials.json"
            if creds_path.exists():
                # Modo OAuth2 (recomendado)
                try:
                    from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: PLC0415
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(creds_path),
                        scopes=["https://www.googleapis.com/auth/drive"]
                    )
                    creds = flow.run_local_server(port=0)
                    self.service = build("drive", "v3", credentials=creds)
                    self.is_authenticated = True
                    log.info("[google_drive] Autenticado")
                except Exception:  # noqa: BLE001
                    log.warning("[google_drive] Error con OAuth2")
            else:
                log.warning("[google_drive] credentials.json no encontrado")
        except ImportError:
            log.warning("[google_drive] Librerías de Google Drive no instaladas")
        except Exception as exc:  # noqa: BLE001
            log.error("[google_drive] Error inicializando: {}", exc)

    async def list_files(self, folder_name: str = "", limit: int = 10) -> list[dict[str, Any]]:
        """Lista archivos en Google Drive."""
        if not self.is_authenticated:
            log.warning("[google_drive] No autenticado")
            return []

        try:
            query = "trashed=false"
            if folder_name:
                query += f" and name contains '{folder_name}'"

            results = self.service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name, mimeType, createdTime)",
                pageSize=limit
            ).execute()

            files = results.get("files", [])
            log.info("[google_drive] {} archivos encontrados", len(files))
            return files
        except Exception as exc:  # noqa: BLE001
            log.error("[google_drive] Error listando archivos: {}", exc)
            return []

    async def upload_file(self, local_path: str, file_name: str = "") -> bool:
        """Sube un archivo a Google Drive."""
        if not self.is_authenticated:
            return False

        try:
            from googleapiclient.http import MediaFileUpload  # noqa: PLC0415
            from pathlib import Path  # noqa: PLC0415

            path = Path(local_path)
            if not path.exists():
                log.error("[google_drive] Archivo no existe: {}", local_path)
                return False

            file_metadata = {"name": file_name or path.name}
            media = MediaFileUpload(str(path))

            self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id"
            ).execute()

            log.info("[google_drive] Archivo subido: {}", file_name or path.name)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[google_drive] Error subiendo archivo: {}", exc)
            return False

    async def download_file(self, file_id: str, output_path: str) -> bool:
        """Descarga un archivo de Google Drive."""
        if not self.is_authenticated:
            return False

        try:
            from googleapiclient.http import MediaIoBaseDownload  # noqa: PLC0415
            import io  # noqa: PLC0415

            request = self.service.files().get_media(fileId=file_id)
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request)

            done = False
            while not done:
                _, done = downloader.next_chunk()

            with open(output_path, "wb") as f:
                f.write(file.getvalue())

            log.info("[google_drive] Archivo descargado: {}", output_path)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[google_drive] Error descargando: {}", exc)
            return False

    async def delete_file(self, file_id: str) -> bool:
        """Elimina un archivo de Google Drive."""
        if not self.is_authenticated:
            return False

        try:
            self.service.files().delete(fileId=file_id).execute()
            log.info("[google_drive] Archivo eliminado: {}", file_id)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("[google_drive] Error eliminando archivo: {}", exc)
            return False

    async def create_folder(self, folder_name: str) -> str | None:
        """Crea una carpeta en Google Drive."""
        if not self.is_authenticated:
            return None

        try:
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder"
            }
            folder = self.service.files().create(
                body=file_metadata,
                fields="id"
            ).execute()

            folder_id = folder.get("id")
            log.info("[google_drive] Carpeta creada: {}", folder_name)
            return folder_id
        except Exception as exc:  # noqa: BLE001
            log.error("[google_drive] Error creando carpeta: {}", exc)
            return None


google_drive_controller = GoogleDriveController()
