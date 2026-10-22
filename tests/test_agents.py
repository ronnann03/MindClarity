"""Tests de agentes: verifica firmas, lógica de acción y manejo de errores."""
from __future__ import annotations

import pytest

from agents.base_agent import AgentResult
from agents.research_agent import ResearchAgent
from agents.system_agent import SystemAgent
from agents.productivity_agent import ProductivityAgent
from agents.calendar_agent import CalendarAgent
from tests.conftest import FakeModel


# --------------------------------------------------------------------------- #
# ResearchAgent
# --------------------------------------------------------------------------- #
class TestResearchAgent:
    @pytest.fixture
    def agent(self, fake_model: FakeModel) -> ResearchAgent:
        return ResearchAgent(model=fake_model)

    @pytest.mark.asyncio
    async def test_execute_requires_query(self, agent: ResearchAgent) -> None:
        result = await agent.execute()
        assert not result.success
        assert "buscar" in result.message.lower() or "query" in result.message.lower()

    @pytest.mark.asyncio
    async def test_execute_uses_topic_fallback(self, fake_model: FakeModel) -> None:
        """topic= debe funcionar como alias de query=."""
        agent = ResearchAgent(model=fake_model)
        # Parchamos _duckduckgo para evitar llamadas de red
        async def _no_net(q):
            return []
        agent._duckduckgo = _no_net
        result = await agent.execute(topic="historia de Python")
        assert isinstance(result, AgentResult)

    @pytest.mark.asyncio
    async def test_quick_search_returns_string(self, fake_model: FakeModel) -> None:
        agent = ResearchAgent(model=fake_model)
        async def _no_net(q):
            return []
        agent._duckduckgo = _no_net
        msg = await agent.quick_search(query="capital de Francia")
        assert isinstance(msg, str)


# --------------------------------------------------------------------------- #
# SystemAgent
# --------------------------------------------------------------------------- #
class TestSystemAgent:
    @pytest.fixture
    def agent(self, fake_model: FakeModel) -> SystemAgent:
        return SystemAgent(model=fake_model)

    @pytest.mark.asyncio
    async def test_unknown_action_returns_failure(self, agent: SystemAgent) -> None:
        result = await agent.execute(action="accion_inexistente_xyz")
        assert not result.success

    @pytest.mark.asyncio
    async def test_no_action_returns_failure(self, agent: SystemAgent) -> None:
        result = await agent.execute()
        assert not result.success

    def test_has_expected_actions(self, agent: SystemAgent) -> None:
        expected = {"open_app", "set_volume", "take_screenshot", "minimize", "delete_file"}
        assert expected.issubset(set(agent.actions.keys()))


# --------------------------------------------------------------------------- #
# ProductivityAgent
# --------------------------------------------------------------------------- #
class TestProductivityAgent:
    @pytest.fixture
    def agent(self, fake_model: FakeModel) -> ProductivityAgent:
        a = ProductivityAgent(model=fake_model)
        # Supabase no disponible en tests — parcheamos métodos internos
        return a

    @pytest.mark.asyncio
    async def test_create_task_requires_title(self, agent: ProductivityAgent) -> None:
        """Sin título el agente debe fallar o manejar el caso graciosamente."""
        # Parcheamos _create_task para evitar llamadas a Supabase
        async def _fake_create(task):
            if not task.get("title"):
                return agent._fail("Se requiere un título.")
            return agent._ok(message="Tarea creada.")
        agent._create_task = _fake_create
        result = await agent.execute(action="create_task")
        assert not result.success

    @pytest.mark.asyncio
    async def test_list_tasks_action(self, agent: ProductivityAgent) -> None:
        async def _fake_list():
            return agent._ok(output=[], message="No hay tareas pendientes.")
        agent._list_tasks = _fake_list
        result = await agent.execute(action="list_tasks")
        assert result.success


# --------------------------------------------------------------------------- #
# CalendarAgent
# --------------------------------------------------------------------------- #
class TestCalendarAgent:
    @pytest.fixture
    def agent(self, fake_model: FakeModel) -> CalendarAgent:
        return CalendarAgent(model=fake_model)

    @pytest.mark.asyncio
    async def test_create_event_requires_title(self, agent: CalendarAgent) -> None:
        result = await agent.execute(action="create_event", start="2025-01-01 10:00")
        assert not result.success
        assert "título" in result.message.lower()

    @pytest.mark.asyncio
    async def test_create_event_requires_start(self, agent: CalendarAgent) -> None:
        result = await agent.execute(action="create_event", title="Reunión")
        assert not result.success
        assert "inicio" in result.message.lower() or "start" in result.message.lower()

    @pytest.mark.asyncio
    async def test_delete_event_requires_id(self, agent: CalendarAgent) -> None:
        result = await agent.execute(action="delete_event")
        assert not result.success
        assert "id" in result.message.lower()

    @pytest.mark.asyncio
    async def test_unknown_action_returns_failure(self, agent: CalendarAgent) -> None:
        result = await agent.execute(action="accion_rara_xyz")
        assert not result.success


# --------------------------------------------------------------------------- #
# AgentResult helpers
# --------------------------------------------------------------------------- #
class TestAgentResult:
    def test_str_uses_message(self) -> None:
        r = AgentResult(success=True, message="todo bien")
        assert str(r) == "todo bien"

    def test_str_falls_back_to_output(self) -> None:
        r = AgentResult(success=True, output="salida directa")
        assert str(r) == "salida directa"
