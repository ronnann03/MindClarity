"""Detección de intención mediante structured outputs (OpenAI, con fallback a Gemini).

Soporta español e inglés y devuelve un objeto `Intent` tipado.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from config.constants import DEFAULT_RISK_BY_INTENT, IntentType, RiskLevel
from config.settings import settings
from core.logger import log
from models.model_router import ModelRouter, model_router


class Intent(BaseModel):
    """Resultado estructurado de la detección de intención."""

    type: IntentType = Field(description="Categoría principal de la intención.")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confianza (0-1) en la clasificación."
    )
    action: str = Field(
        default="", description="Acción concreta solicitada, p.ej. 'open_app'."
    )
    entities: dict[str, Any] = Field(
        default_factory=dict, description="Entidades extraídas (app, archivo, ciudad...)."
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Parámetros adicionales para la acción."
    )
    risk_level: RiskLevel = Field(
        default=RiskLevel.LOW, description="Riesgo estimado de la acción."
    )
    language: str = Field(default="es", description="Idioma detectado: 'es' o 'en'.")
    reasoning: str = Field(default="", description="Breve justificación.")


_SYSTEM_PROMPT = """\
Eres el módulo de detección de intención de YU, un asistente de IA tipo Jarvis \
que controla un PC Windows. Analiza la petición del usuario (en español o inglés) \
y clasifícala con precisión.

══ TIPOS DE INTENCIÓN ══
- conversation   : charla, preguntas generales, saludos, chistes.
- system_control : apps, ventanas, volumen, brillo, captura, bloquear PC, mouse/teclado.
- file_operation : crear, borrar, mover, copiar, buscar archivos o carpetas.
- media_control  : reproducir música/vídeo en YouTube, control multimedia.
- search         : búsqueda web rápida (respuesta breve).
- email          : leer o enviar correos.
- reminder       : crear recordatorios, notas o tareas.
- automation     : automatizaciones complejas (organizar descargas, renombrar en lote, accesos directos).
- research       : investigación profunda y detallada sobre un tema.
- weather        : clima y pronóstico meteorológico.
- calendar       : ver, crear o eliminar eventos en Google Calendar.
- obsidian       : crear notas, buscar notas, escribir en diario, o consultar el cerebro de Obsidian.
- web            : abrir sitios web. Acciones: open_url(url), search(query), open_youtube(query), open_maps(location), open_gmail.
- unknown        : si no encaja en ninguna categoría anterior.

══ NIVELES DE RIESGO ══
- low      : sin efectos destructivos (conversar, buscar, abrir apps, consultar clima).
- medium   : cambia estado del sistema de forma reversible (volumen, cerrar apps).
- high     : potencialmente destructivo o privado (borrar archivos, enviar correos).
- critical : irreversible o impacto severo (borrado masivo, bloquear PC, formatear).

══ NOMBRES DE ACCIÓN EXACTOS ══
Usa SIEMPRE estos nombres de acción (campo `action`) según el tipo de intención:

system_control:
  open_app | close_app | list_running_apps
  set_volume | get_volume | set_brightness
  take_screenshot | lock_screen
  type_text | press_key | control_mouse
  minimize | maximize | restore | focus | close_window | move_window | resize_window

file_operation:
  create_file | create_folder
  delete_file | delete_folder
  move_file | copy_file
  list_directory | search_files

media_control:
  play_music | play_video | open_youtube

email:
  read_email | send_email

reminder:
  create_task | list_tasks | complete_task

automation:
  organize_downloads | bulk_rename | create_shortcut | schedule_task

calendar:
  list_events | create_event | delete_event

obsidian:
  create_note | append_daily_note | search_notes | read_note

══ NOMBRES DE ENTIDAD EXACTOS ══
Usa SIEMPRE estos nombres de clave en `entities` (coinciden con los parámetros de las funciones):

| Acción              | Entidades requeridas                                                   |
|---------------------|------------------------------------------------------------------------|
| open_app/close_app  | name (str): nombre de la app, ej. "chrome"                             |
| set_volume          | level (int 0-100)                                                      |
| set_brightness      | level (int 0-100)                                                      |
| take_screenshot     | path (str, opcional)                                                   |
| type_text           | text (str)                                                             |
| press_key           | key (str), ej. "ctrl+c", "enter", "f5"                                 |
| control_mouse       | x (int), y (int), click (bool, opcional)                               |
| minimize/maximize/… | title (str): título parcial de la ventana                              |
| create_file         | path (str), content (str, opcional)                                    |
| create_folder       | path (str)                                                             |
| delete_file         | path (str)                                                             |
| delete_folder       | path (str)                                                             |
| move_file/copy_file | source (str), destination (str)                                        |
| list_directory      | path (str), ej. "~/Desktop"                                            |
| search_files        | root (str), pattern (str glob), ej. root="~", pattern="*.pdf"          |
| play_music          | query (str)                                                            |
| play_video          | query (str)                                                            |
| read_email          | query (str, opcional), limit (int, opcional)                           |
| send_email          | recipient (str), subject (str), body (str)                             |
| create_task         | title (str), due_at (str ISO 8601, opcional)                           |
| complete_task       | id (str)                                                               |
| get_weather         | city (str)                                                             |
| quick_search        | query (str)                                                            |
| list_events         | max_results (int, opcional, default 10)                                |
| create_event        | title (str), start (str ISO 8601 o "YYYY-MM-DD HH:MM"),               |
|                     | end (str, opcional), description (str, opcional), location (str, opc.) |
| delete_event        | event_id (str)                                                         |
| execute (research)  | query (str), depth ("quick" | "detailed")                              |
| organize_downloads  | folder (str, opcional)                                                 |
| bulk_rename         | folder (str), prefix (str), start (int, opcional)                      |
| create_note         | title (str), content (str)                                             |
| append_daily_note   | content (str)                                                          |
| search_notes        | query (str)                                                            |
| read_note           | title (str)                                                            |

Detecta el idioma del usuario ('es' o 'en') y ponlo en el campo `language`.
"""


import re


def _clean_wake_word_prefix(text: str) -> str:
    """Elimina prefijos comunes de wake word como 'you', 'yu', 'hey yu', etc."""
    cleaned = re.sub(r"^(?:you|yu|hey yu|oye yu|hola yu)\b[\s,\.]*", "", text, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else text


def _fast_rule_match(text: str) -> Intent | None:
    """Reconocimiento determinista por reglas para comandos directos del sistema."""
    raw = text.strip()
    from core.voice_commands import match_command
    clean = _clean_wake_word_prefix(raw).lower()
    direct = match_command(_clean_wake_word_prefix(raw))
    if direct:
        return direct

    # 1. Obsidian - Diario / Append Daily Note
    if any(k in clean for k in ["mi diario", "en el diario", "al diario", "escribe en mi diario", "anota en mi diario"]):
        match = re.search(r"(?:diario|mi diario)\s*[:,\-]?\s*(.+)$", clean)
        content = match.group(1).strip() if match else clean
        return Intent(
            type=IntentType.OBSIDIAN,
            confidence=0.98,
            action="append_daily_note",
            entities={"content": content},
            reasoning="Regla directa: diario de Obsidian",
        )

    # 2. Obsidian - Crear Nota
    if "obsidian" in clean and any(k in clean for k in ["crea", "crear", "guarda", "guardar", "anota", "anotar"]):
        match = re.search(r"(?:nota|sobre|llamada)?\s*[\"']?([^\"':]+)[\"']?\s*[:\-]\s*(.+)", clean)
        if match:
            title, content = match.group(1).strip(), match.group(2).strip()
        else:
            title = "Nota de YU"
            content = re.sub(r"^(?:guarda|guardar|crea|crear|anota|anotar)\s+(?:en|una)?\s*obsidian\s*", "", clean).strip()
        return Intent(
            type=IntentType.OBSIDIAN,
            confidence=0.98,
            action="create_note",
            entities={"title": title, "content": content},
            reasoning="Regla directa: crear nota Obsidian",
        )

    # 3. Obsidian - Buscar notas
    if "obsidian" in clean and any(k in clean for k in ["busca", "buscar", "revisa", "revisar", "que dice"]):
        match = re.search(r"(?:busca|buscar|revisa|revisar|que dice)\s+(?:en|sobre)?\s*obsidian\s*(.+)$", clean)
        query = match.group(1).strip() if match else clean
        return Intent(
            type=IntentType.OBSIDIAN,
            confidence=0.98,
            action="search_notes",
            entities={"query": query},
            reasoning="Regla directa: buscar notas en Obsidian",
        )

    # 4. Abre / Abrir / Open / Lanza
    match = re.search(r"^(?:abre|abrir|open|lanza|lanzar)\s+(?:la|el|los|las)?\s*(.+)$", clean)
    if match:
        target = match.group(1).strip().rstrip('.!?').strip()
        target = re.sub(r"\b(?:por favor|please)\b", "", target).strip()
        if target:
            return Intent(
                type=IntentType.SYSTEM_CONTROL,
                confidence=0.98,
                action="open_app",
                entities={"name": target},
                reasoning="Regla directa: abrir aplicación",
            )

    # 5. Cierra / Cerrar / Close
    match = re.search(r"^(?:cierra|cerrar|close)\s+(?:la|el|los|las)?\s*(.+)$", clean)
    if match:
        target = match.group(1).strip().rstrip('.!?').strip()
        if target:
            return Intent(
                type=IntentType.SYSTEM_CONTROL,
                confidence=0.98,
                action="close_app",
                entities={"name": target},
                reasoning="Regla directa: cerrar aplicación",
            )

    # 6. Volumen
    if any(k in clean for k in ["sube el volumen", "subir volumen", "baja el volumen", "bajar volumen", "silencia", "silenciar"]):
        return Intent(
            type=IntentType.SYSTEM_CONTROL,
            confidence=0.98,
            action="set_volume",
            entities={"level": 70 if "sube" in clean else (20 if "baja" in clean else 0)},
            reasoning="Regla directa: volumen",
        )

    # 7. Clima
    if any(k in clean for k in ["clima", "qué tiempo hace", "pronóstico", "pronostico"]):
        return Intent(
            type=IntentType.WEATHER,
            confidence=0.98,
            action="get_weather",
            entities={},
            reasoning="Regla directa: clima",
        )

    # 8. Búsqueda
    match = re.search(r"^(?:busca|buscar|search)\s+(.+)$", clean)
    if match:
        query = match.group(1).strip()
        if query:
            return Intent(
                type=IntentType.SEARCH,
                confidence=0.95,
                action="quick_search",
                entities={"query": query},
                reasoning="Regla directa: búsqueda web",
            )

    return None


class IntentDetector:
    """Clasifica la entrada del usuario en un objeto `Intent`."""

    def __init__(self, model: ModelRouter | None = None) -> None:
        self.model = model or model_router

    async def detect(self, user_input: str) -> Intent:
        """Detecta la intención de `user_input`."""
        cleaned_input = _clean_wake_word_prefix(user_input)

        # 1. Comprobación rápida por reglas deterministas
        fast_intent = _fast_rule_match(user_input)
        if fast_intent is not None:
            log.info(
                "Intent detectado por REGLA RÁPIDA: {} (acción='{}', entidades={})",
                fast_intent.type.value,
                fast_intent.action,
                fast_intent.entities,
            )
            return fast_intent

        # 2. Detección por LLM
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": cleaned_input},
        ]
        try:
            intent = await self.model.structured_output(messages, Intent)
        except Exception as exc:  # noqa: BLE001
            log.error("Fallo en detección de intención, usando UNKNOWN: {}", exc)
            return Intent(
                type=IntentType.UNKNOWN,
                confidence=0.0,
                action="",
                reasoning=f"error: {exc}",
            )

        # Ajuste de seguridad: nunca rebajar el riesgo base del tipo de intención.
        base_risk = DEFAULT_RISK_BY_INTENT.get(intent.type, RiskLevel.LOW)
        if base_risk > intent.risk_level:
            intent.risk_level = base_risk

        log.info(
            "Intent detectado por LLM: {} (conf={:.2f}, riesgo={}, acción='{}')",
            intent.type.value,
            intent.confidence,
            intent.risk_level.value,
            intent.action,
        )
        return intent


intent_detector = IntentDetector()

