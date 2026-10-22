"""Tests del Planner: verifica que cada tipo de Intent genera el Plan correcto."""
from __future__ import annotations

import pytest

from config.constants import IntentType, RiskLevel
from core.intent_detector import Intent
from core.planner import Planner


@pytest.fixture
def planner() -> Planner:
    return Planner()


def _intent(
    type: IntentType,
    action: str = "",
    entities: dict | None = None,
    params: dict | None = None,
) -> Intent:
    return Intent(
        type=type,
        action=action,
        entities=entities or {},
        parameters=params or {},
    )


# --------------------------------------------------------------------------- #
# system_control
# --------------------------------------------------------------------------- #
class TestSystemControl:
    def test_open_app(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.SYSTEM_CONTROL, "open_app", {"name": "chrome"}))
        assert len(plan.steps) == 1
        step = plan.steps[0]
        assert step.module == "app_launcher"
        assert step.function == "open_app"
        assert step.params["name"] == "chrome"
        assert step.risk_level == RiskLevel.LOW

    def test_close_app(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.SYSTEM_CONTROL, "close_app", {"name": "notepad"}))
        step = plan.steps[0]
        assert step.module == "app_launcher"
        assert step.function == "close_app"
        assert step.risk_level == RiskLevel.MEDIUM

    def test_set_volume(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.SYSTEM_CONTROL, "set_volume", {"level": 50}))
        step = plan.steps[0]
        assert step.module == "pc_controller"
        assert step.function == "set_volume"

    def test_minimize_window(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.SYSTEM_CONTROL, "minimize", {"title": "Chrome"}))
        step = plan.steps[0]
        assert step.module == "window_manager"
        assert step.function == "minimize"

    def test_lock_screen_is_high_risk(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.SYSTEM_CONTROL, "lock_screen"))
        assert plan.max_risk == RiskLevel.HIGH

    def test_unknown_action_is_not_executed(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.SYSTEM_CONTROL, "accion_desconocida"))
        assert plan.is_empty


# --------------------------------------------------------------------------- #
# file_operation
# --------------------------------------------------------------------------- #
class TestFileOperation:
    def test_create_file(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.FILE_OPERATION, "create_file", {"path": "~/test.txt"}))
        step = plan.steps[0]
        assert step.module == "file_manager"
        assert step.function == "create_file"
        assert step.risk_level == RiskLevel.MEDIUM

    def test_delete_folder_is_critical(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.FILE_OPERATION, "delete_folder", {"path": "/tmp/x"}))
        assert plan.max_risk == RiskLevel.CRITICAL

    def test_list_directory_is_low_risk(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.FILE_OPERATION, "list_directory", {"path": "~/Desktop"}))
        assert plan.max_risk == RiskLevel.LOW


# --------------------------------------------------------------------------- #
# email
# --------------------------------------------------------------------------- #
class TestEmail:
    def test_read_email(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.EMAIL, "read_email"))
        step = plan.steps[0]
        assert step.module == "email_agent"
        assert step.params.get("action") == "read_email"
        assert step.risk_level == RiskLevel.MEDIUM

    def test_send_email_is_high_risk(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.EMAIL, "send_email", {"recipient": "a@b.com"}))
        assert plan.max_risk == RiskLevel.HIGH


# --------------------------------------------------------------------------- #
# reminder / productivity
# --------------------------------------------------------------------------- #
class TestReminder:
    def test_create_task_has_action(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.REMINDER, "create_task", {"title": "Llamar"}))
        step = plan.steps[0]
        assert step.module == "productivity_agent"
        assert step.params.get("action") == "create_task"
        assert step.params.get("title") == "Llamar"


# --------------------------------------------------------------------------- #
# calendar
# --------------------------------------------------------------------------- #
class TestCalendar:
    def test_list_events(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.CALENDAR, "list_events"))
        step = plan.steps[0]
        assert step.module == "calendar_agent"
        assert step.params.get("action") == "list_events"
        assert step.risk_level == RiskLevel.LOW

    def test_create_event(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.CALENDAR, "create_event", {"title": "Reunión"}))
        step = plan.steps[0]
        assert step.params.get("action") == "create_event"

    def test_delete_event_is_high_risk(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.CALENDAR, "delete_event", {"event_id": "abc"}))
        assert plan.max_risk == RiskLevel.HIGH


# --------------------------------------------------------------------------- #
# weather / search / research / media
# --------------------------------------------------------------------------- #
class TestOtherIntents:
    def test_weather(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.WEATHER, "get_weather", {"city": "Madrid"}))
        step = plan.steps[0]
        assert step.module == "weather_service"
        assert step.function == "get_weather"

    def test_search(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.SEARCH, "", {"query": "Python asyncio"}))
        step = plan.steps[0]
        assert step.module == "research_agent"
        assert step.function == "quick_search"

    def test_research(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.RESEARCH, "", {"query": "machine learning"}))
        step = plan.steps[0]
        assert step.module == "research_agent"
        assert step.function == "execute"

    def test_media_video(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.MEDIA_CONTROL, "play_video", {"query": "cat videos"}))
        step = plan.steps[0]
        assert step.module == "youtube_controller"

    def test_conversation_has_no_steps(self, planner: Planner) -> None:
        plan = planner.build(_intent(IntentType.CONVERSATION))
        assert plan.is_empty
