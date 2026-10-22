"""Saludos contextuales compartidos por las respuestas de texto y voz."""
from datetime import datetime, timedelta, timezone
import re
import threading

# Lima no aplica horario de verano; no requiere instalar tzdata en Windows.
LIMA = timezone(timedelta(hours=-5), name="America/Lima")
_GREETING = re.compile(
    r"^\s*[¡!]*\s*(?:buenos días|buenas tardes|buenas noches|hola|hey|hello|hi|"
    r"good morning|good afternoon|good evening)\b[!¡,.:\s]*", re.IGNORECASE)


def humanize_response_by_time(base_response: str, *, language: str = "es",
                              now: datetime | None = None) -> str:
    """Normaliza un saludo inicial a la hora de Lima, sin duplicarlo."""
    if not base_response.strip():
        return base_response
    hour = (now or datetime.now(LIMA)).astimezone(LIMA).hour
    period = 0 if 5 <= hour < 12 else 1 if 12 <= hour < 20 else 2
    greetings = (("Good morning", "Good afternoon", "Good evening") if language == "en"
                 else ("Buenos días", "Buenas tardes", "Buenas noches"))
    body = _GREETING.sub("", base_response, count=1).strip()
    return f"{greetings[period]}. {body}" if body else f"{greetings[period]}."


class ConversationStyle:
    """Saluda al primer contacto, al cambiar de día o tras cuatro horas de pausa."""
    def __init__(self) -> None:
        self._last_interaction: datetime | None = None
        self._lock = threading.Lock()

    def apply(self, response: str, *, language: str = "es", now: datetime | None = None) -> str:
        if not response.strip():
            return response
        current = (now or datetime.now(LIMA)).astimezone(LIMA)
        with self._lock:
            previous = self._last_interaction
            greet = (previous is None or current.date() != previous.date()
                     or current - previous >= timedelta(hours=4))
            self._last_interaction = current
        if greet:
            return humanize_response_by_time(response, language=language, now=current)
        body = _GREETING.sub("", response, count=1).strip()
        return body or response
