"""Agente de productividad: tareas, recordatorios y notas (persistidas en Supabase)."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from config.constants import TABLE_TASKS
from core.logger import log
from database.supabase_client import supabase_client
from database.local_tasks import local_tasks


class ProductivityAgent(BaseAgent):
    """Gestiona la productividad del usuario: crear y listar tareas/recordatorios."""

    name = "productivity_agent"

    async def execute(  # type: ignore[override]
        self,
        action: str = "create_task",
        **kwargs: Any,
    ) -> AgentResult:
        """Acepta llamadas con kwargs sueltos del decision_engine.

        `kwargs` puede contener: title, description, due_at, id, etc.
        """
        task = {"action": action, **kwargs}
        action = action.lower()
        if action in {"list", "listar", "list_tasks"}:
            return await self._list_tasks()
        if action in {"complete", "completar", "done", "complete_task"}:
            return await self._complete_task(task)
        # create / create_task / cualquier otro valor → crear tarea.
        return await self._create_task(task)

    async def _create_task(self, task: dict[str, Any]) -> AgentResult:
        title = task.get("title") or task.get("text") or task.get("query")
        if not title:
            return self._fail("No entendí qué tarea o recordatorio crear.")
        data: dict[str, Any] = {
            "title": title,
            "description": task.get("description", ""),
            "status": "pending",
        }
        due = task.get("due_at") or task.get("when")
        if due:
            data["due_at"] = due
        row = (await asyncio.to_thread(supabase_client.insert, TABLE_TASKS, data) if supabase_client.connected
               else await asyncio.to_thread(local_tasks.create, data))
        if not row or not row.get('id'):
            return self._fail("No se pudo guardar la tarea.")
        log.info("Tarea creada: {}", title)
        when_txt = f" para {due}" if due else ""
        note = " La fecha queda registrada; los avisos automáticos aún no están habilitados." if due else ""
        return self._ok(output=row, message=f"He guardado la tarea '{title}'{when_txt}." + note)

    async def _list_tasks(self) -> AgentResult:
        rows = await asyncio.to_thread(
            supabase_client.select, TABLE_TASKS, {"status": "pending"}, 50, "created_at", True
        ) if supabase_client.connected else await asyncio.to_thread(local_tasks.pending)
        if not rows:
            return self._ok(output=[], message="No tienes tareas pendientes.")
        lines = [f"- {r.get('title')}" + (f" (vence {r['due_at']})" if r.get("due_at") else "") for r in rows]
        return self._ok(output=rows, message="Tus tareas pendientes:\n" + "\n".join(lines))

    async def _complete_task(self, task: dict[str, Any]) -> AgentResult:
        task_id = task.get("id")
        if not task_id and task.get('title') and not supabase_client.connected:
            rows = await asyncio.to_thread(local_tasks.pending)
            matches = [r for r in rows if r['title'].casefold() == task['title'].strip().casefold()]
            if len(matches) == 1:
                task_id = matches[0]['id']
            else:
                return self._fail("No encontré una única tarea con ese nombre. Indica su identificador.")
        if not task_id:
            return self._fail("Falta el identificador de la tarea a completar.")
        if not supabase_client.connected:
            updated = await asyncio.to_thread(local_tasks.complete, task_id)
            return self._ok(message="Tarea completada.") if updated else self._fail("No encontré esa tarea pendiente.")
        row = await asyncio.to_thread(
            supabase_client.update, TABLE_TASKS, task_id,
            {"status": "done", "updated_at": datetime.utcnow().isoformat()},
        )
        if not row:
            return self._fail("No se pudo actualizar la tarea.")
        return self._ok(message="Tarea marcada como completada.")


productivity_agent = ProductivityAgent()
