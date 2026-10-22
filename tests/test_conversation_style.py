from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.conversation_style import ConversationStyle, LIMA, humanize_response_by_time


@pytest.mark.parametrize("hour,greeting", [(0,"Buenas noches"),(4,"Buenas noches"),
    (5,"Buenos días"),(11,"Buenos días"),(12,"Buenas tardes"),(19,"Buenas tardes"),
    (20,"Buenas noches"),(23,"Buenas noches")])
def test_time_boundaries(hour, greeting):
    now = datetime(2026, 10, 16, hour, tzinfo=LIMA)
    assert humanize_response_by_time("Listo.", now=now) == f"{greeting}. Listo."


def test_lima_hour_instead_of_host_timezone():
    now = datetime(2026, 10, 16, 14, tzinfo=timezone.utc)
    assert humanize_response_by_time("Listo.", now=now).startswith("Buenos días.")


def test_existing_greeting_is_not_duplicated():
    now = datetime(2026, 10, 16, 9, tzinfo=LIMA)
    assert humanize_response_by_time("¡Buenas noches! Estoy aquí.", now=now) == "Buenos días. Estoy aquí."
    assert humanize_response_by_time("", now=now) == ""
    assert humanize_response_by_time("Hello! Ready.", language="en", now=now) == "Good morning. Ready."


def test_greetings_resume_after_idle_or_new_day():
    style = ConversationStyle()
    def at(day, hour):
        return datetime(2026, 10, day, hour, tzinfo=LIMA)
    assert style.apply("Aquí estoy.", now=at(16,9)).startswith("Buenos días.")
    assert style.apply("Hola, seguimos.", now=at(16,10)) == "seguimos."
    assert style.apply("Listo.", now=at(16,13)) == "Listo."
    assert style.apply("Aquí estoy.", now=at(16,17)).startswith("Buenas tardes.")
    assert style.apply("Hola.", now=at(17,0)) == "Buenas noches."


@pytest.mark.asyncio
async def test_orchestrator_saves_exact_humanized_response(fake_memory):
    from config.constants import IntentType
    from core.intent_detector import Intent
    from core.orchestrator import Orchestrator
    detector = MagicMock()
    detector.detect = AsyncMock(return_value=Intent(type=IntentType.CONVERSATION, language="es"))
    model = MagicMock()
    model.chat_completion = AsyncMock(return_value=MagicMock(content="Estoy aquí."))
    brain = Orchestrator(detector=detector, memory=fake_memory, model=model)
    brain.conversation_style.apply = MagicMock(return_value="Buenas tardes. Estoy aquí.")
    response = await brain.process("Hola")
    assert response == "Buenas tardes. Estoy aquí."
    fake_memory.save_interaction.assert_awaited_once_with("Hola", response, "conversation")
