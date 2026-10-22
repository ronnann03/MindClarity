"""Controlador de integración con Obsidian.

Conecta YU con el Vault de Obsidian para usarlo como cerebro de notas y memoria a largo plazo.
"""
from __future__ import annotations

import datetime
from pathlib import Path
import re
from typing import Any

from config.settings import settings
from core.logger import log


class ObsidianController:
    """Gestiona lecturas, escrituras y búsquedas en el Vault de Obsidian."""

    def __init__(self) -> None:
        self._vault_path: Path | None = None

    def get_vault_path(self) -> Path:
        """Obtiene o detecta la ruta del Vault de Obsidian en el sistema."""
        if self._vault_path and self._vault_path.exists():
            return self._vault_path

        # 1. Configuración explícita en settings (.env)
        if settings.obsidian_vault_path:
            configured = Path(settings.obsidian_vault_path)
            if configured.exists():
                self._vault_path = configured
                return configured

        # 2. Rutas comunes en Windows
        home = Path.home()
        candidates = [
            home / "OneDrive" / "Documentos" / "Obsidian Vault",
            home / "Documents" / "Obsidian Vault",
            home / "Documentos" / "Obsidian Vault",
            home / "OneDrive" / "Documents" / "Obsidian Vault",
            home / "Desktop" / "Obsidian Vault",
            home / "Escritorio" / "Obsidian Vault",
        ]

        for cand in candidates:
            if cand.exists() and cand.is_dir():
                log.info("[obsidian] Vault detectado automáticamente en: {}", cand)
                self._vault_path = cand
                return cand

        # 3. Fallback: crear un Vault de YU en Documentos
        fallback = home / "Documents" / "YU_Obsidian_Vault"
        fallback.mkdir(parents=True, exist_ok=True)
        log.info("[obsidian] Creado Vault de YU por defecto en: {}", fallback)
        self._vault_path = fallback
        return fallback

    def create_note(
        self,
        title: str,
        content: str,
        folder: str = "YU Brain",
        tags: list[str] | None = None,
    ) -> str:
        """Crea una nueva nota de Markdown en Obsidian con metadatos."""
        try:
            vault = self.get_vault_path()
            target_dir = vault / folder if folder else vault
            target_dir.mkdir(parents=True, exist_ok=True)

            # Limpiar nombre del archivo
            clean_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
            if not clean_title.endswith(".md"):
                filename = f"{clean_title}.md"
            else:
                filename = clean_title

            file_path = target_dir / filename
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            tags_list = tags or ["yu-brain", "asistente-ia"]
            tags_str = "\n".join(f"  - {t}" for t in tags_list)

            markdown_body = f"""---
title: "{clean_title}"
date: "{now}"
created_by: "YU AI Assistant"
tags:
{tags_str}
---

# {clean_title}

{content.strip()}

---
*Nota registrada automáticamente por YU (Cerebro IA).*
"""
            file_path.write_text(markdown_body, encoding="utf-8")
            log.info("[obsidian] Nota creada: {}", file_path)
            return f"He guardado la nota '{clean_title}' en tu cerebro de Obsidian."
        except Exception as exc:  # noqa: BLE001
            log.error("[obsidian] Error creando nota: {}", exc)
            return f"No pude guardar la nota en Obsidian: {exc}"

    def append_to_daily_note(self, content: str) -> str:
        """Agrega un registro con timestamp a la Nota Diaria de hoy en Obsidian."""
        try:
            vault = self.get_vault_path()
            daily_dir = vault / "Daily Notes"
            daily_dir.mkdir(parents=True, exist_ok=True)

            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            time_str = datetime.datetime.now().strftime("%H:%M")
            daily_path = daily_dir / f"{today_str}.md"

            if not daily_path.exists():
                header = f"# Diario - {today_str}\n\n## Registros de YU (Cerebro IA)\n\n"
                daily_path.write_text(header, encoding="utf-8")

            entry = f"- **[{time_str}]** {content.strip()}\n"
            with daily_path.open("a", encoding="utf-8") as f:
                f.write(entry)

            log.info("[obsidian] Registro agregado a Nota Diaria: {}", daily_path)
            return f"He anotado la idea en tu diario de Obsidian ({today_str})."
        except Exception as exc:  # noqa: BLE001
            log.error("[obsidian] Error en diario: {}", exc)
            return f"No pude escribir en el diario de Obsidian: {exc}"

    def search_notes(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Busca notas en el Vault por título o contenido."""
        results: list[dict[str, Any]] = []
        try:
            vault = self.get_vault_path()
            keywords = [k.lower() for k in query.split() if len(k) > 2]
            if not keywords:
                keywords = [query.lower()]

            for md_file in vault.rglob("*.md"):
                try:
                    text = md_file.read_text(encoding="utf-8", errors="ignore")
                    title = md_file.stem
                    lower_text = text.lower()
                    lower_title = title.lower()

                    matches = sum(1 for k in keywords if k in lower_title or k in lower_text)
                    if matches > 0:
                        # Extraer un extracto relevante
                        snippet = text[:200].replace("\n", " ").strip()
                        results.append({
                            "title": title,
                            "path": str(md_file.relative_to(vault)),
                            "snippet": snippet,
                            "matches": matches,
                        })
                except Exception:  # noqa: BLE001
                    continue

            results.sort(key=lambda x: x["matches"], reverse=True)
            return results[:limit]
        except Exception as exc:  # noqa: BLE001
            log.error("[obsidian] Error buscando notas: {}", exc)
            return []

    def read_note(self, title: str) -> str:
        """Lee el contenido completo de una nota por nombre."""
        try:
            vault = self.get_vault_path()
            clean_name = re.sub(r'[\\/*?:"<>|]', "", title).strip().lower()

            for md_file in vault.rglob("*.md"):
                if clean_name in md_file.stem.lower():
                    content = md_file.read_text(encoding="utf-8", errors="ignore")
                    # Quitar frontmatter
                    content_clean = re.sub(r"^---[\s\S]*?---\n", "", content).strip()
                    return f"Nota '{md_file.stem}':\n\n{content_clean[:800]}"

            return f"No encontré ninguna nota que coincida con '{title}' en Obsidian."
        except Exception as exc:  # noqa: BLE001
            log.error("[obsidian] Error leyendo nota: {}", exc)
            return f"No pude leer la nota: {exc}"


obsidian_controller = ObsidianController()
