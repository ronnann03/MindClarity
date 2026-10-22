"""Cliente Supabase singleton con operaciones CRUD genéricas.

Si no hay credenciales configuradas, opera en modo "desconectado" devolviendo
estructuras vacías para no romper la aplicación durante el desarrollo.
"""
from __future__ import annotations

from typing import Any, Optional

from config.constants import (
    TABLE_CONVERSATIONS,
    TABLE_LOGS,
    TABLE_MEMORIES,
    TABLE_MESSAGES,
    TABLE_PREFERENCES,
    TABLE_TASKS,
)
from config.settings import settings
from core.logger import log

try:
    from supabase import Client, create_client
except Exception:  # noqa: BLE001 - librería opcional en desarrollo.
    Client = Any  # type: ignore
    create_client = None  # type: ignore


class SupabaseClient:
    """Wrapper singleton del cliente de Supabase."""

    _instance: Optional["SupabaseClient"] = None

    def __new__(cls) -> "SupabaseClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self) -> None:
        self.client: Any = None
        self.connected = False
        if not settings.supabase_url or not settings.supabase_key:
            log.warning("Supabase sin credenciales: modo desconectado.")
            return
        if create_client is None:
            log.warning("Librería 'supabase' no instalada: modo desconectado.")
            return
        try:
            self.client = create_client(settings.supabase_url, settings.supabase_key)
            self.connected = True
            log.info("Cliente Supabase conectado.")
        except Exception as exc:  # noqa: BLE001
            log.error("No se pudo conectar a Supabase: {}", exc)
            self.client = None
            self.connected = False

    # ------------------------------------------------------------------ #
    # CRUD genérico
    # ------------------------------------------------------------------ #
    def insert(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        if not self.connected:
            return data
        try:
            resp = self.client.table(table).insert(data).execute()
            return resp.data[0] if resp.data else {}
        except Exception as exc:  # noqa: BLE001
            log.error("Error insert en {}: {}", table, exc)
            return {}

    def select(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        order_by: str | None = None,
        descending: bool = True,
    ) -> list[dict[str, Any]]:
        if not self.connected:
            return []
        try:
            query = self.client.table(table).select("*")
            for key, value in (filters or {}).items():
                query = query.eq(key, value)
            if order_by:
                query = query.order(order_by, desc=descending)
            query = query.limit(limit)
            return query.execute().data or []
        except Exception as exc:  # noqa: BLE001
            log.error("Error select en {}: {}", table, exc)
            return []

    def update(self, table: str, row_id: str, data: dict[str, Any]) -> dict[str, Any]:
        if not self.connected:
            return data
        try:
            resp = self.client.table(table).update(data).eq("id", row_id).execute()
            return resp.data[0] if resp.data else {}
        except Exception as exc:  # noqa: BLE001
            log.error("Error update en {}: {}", table, exc)
            return {}

    def delete(self, table: str, row_id: str) -> bool:
        if not self.connected:
            return False
        try:
            self.client.table(table).delete().eq("id", row_id).execute()
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("Error delete en {}: {}", table, exc)
            return False

    def upsert(self, table: str, data: dict[str, Any], on_conflict: str = "id") -> dict[str, Any]:
        if not self.connected:
            return data
        try:
            resp = self.client.table(table).upsert(data, on_conflict=on_conflict).execute()
            return resp.data[0] if resp.data else {}
        except Exception as exc:  # noqa: BLE001
            log.error("Error upsert en {}: {}", table, exc)
            return {}

    def rpc(self, function_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Llama a una función RPC de Postgres (p.ej. búsqueda vectorial)."""
        if not self.connected:
            return []
        try:
            return self.client.rpc(function_name, params).execute().data or []
        except Exception as exc:  # noqa: BLE001
            log.error("Error RPC {}: {}", function_name, exc)
            return []

    # ------------------------------------------------------------------ #
    # Helpers de tablas concretas
    # ------------------------------------------------------------------ #
    def log_event(self, level: str, message: str, context: dict | None = None) -> None:
        self.insert(TABLE_LOGS, {"level": level, "message": message, "context": context or {}})

    def get_preferences(self) -> dict[str, Any]:
        rows = self.select(TABLE_PREFERENCES, limit=500)
        return {r["key"]: r["value"] for r in rows if "key" in r}

    def set_preference(self, key: str, value: Any) -> None:
        self.upsert(TABLE_PREFERENCES, {"key": key, "value": value}, on_conflict="key")


# Instancia singleton.
supabase_client = SupabaseClient()
