"""Orquestador central de YU.

Coordina el pipeline completo:
  intención -> plan -> decisión/ejecución -> memoria -> respuesta natural.
"""
from __future__ import annotations

from typing import Any

from config.constants import ExecutionStatus, IntentType
from config.settings import settings
from core.decision_engine import DecisionEngine, decision_engine
from core.intent_detector import Intent, IntentDetector, intent_detector
from core.logger import log
from core.permissions import permission_manager
from core.conversation_style import ConversationStyle
from core.planner import Plan, Planner, planner
from memory.memory_manager import MemoryManager
from models.openai_model import OpenAIModel, openai_model
from models.model_router import ModelRouter, model_router as _model_router

_PERSONA_PROMPT = """\
Eres {name}, un asistente de inteligencia artificial avanzado, inspirado en Jarvis. \
Hablas con el usuario llamándolo '{user}'. Eres preciso, educado, ingenioso y conciso. \
Respondes en el mismo idioma en que te hablan (español o inglés). Cuando ejecutas \
acciones en el sistema, confirmas el resultado de forma natural y breve. \
Tu tono es cercano, sereno y discreto; evita fórmulas repetitivas y no uses \
el tratamiento del usuario en cada frase. No añadas saludos: la aplicación \
los incorpora según la hora y la pausa entre conversaciones. No inventes \
emociones, recuerdos ni acciones realizadas; sigues siendo un asistente de IA.
"""


class Orchestrator:
    """Cerebro central que ejecuta el pipeline de YU."""

    def __init__(
        self,
        detector: IntentDetector | None = None,
        plan_builder: Planner | None = None,
        engine: DecisionEngine | None = None,
        memory: MemoryManager | None = None,
        model: OpenAIModel | None = None,
    ) -> None:
        self.detector = detector or intent_detector
        self.planner = plan_builder or planner
        self.engine = engine or decision_engine
        self.memory = memory or MemoryManager()
        self.model = model or _model_router  # type: ignore[assignment]
        self.permissions = permission_manager
        self.conversation_style = ConversationStyle()

    def register_executors(self, modules: dict[str, Any]) -> None:
        """Registra los módulos de automatización/agentes en el motor."""
        self.engine.register_many(modules)

    async def initialize(self) -> None:
        """Inicializa subsistemas (memoria)."""
        await self.memory.initialize()
        log.info("Orquestador inicializado.")

    # ------------------------------------------------------------------ #
    # Pipeline principal
    # ------------------------------------------------------------------ #
    async def process(self, user_input: str) -> str:
        """Procesa una entrada del usuario y devuelve la respuesta final."""
        user_input = (user_input or "").strip()
        if not user_input:
            return "No he escuchado nada, ¿puedes repetirlo?"

        log.info("Procesando entrada: '{}'", user_input)

        # 1) Detección de intención.
        intent: Intent = await self.detector.detect(user_input)
        if intent.action == 'capabilities':
            return (f"{settings.user_name}, puedes decir: YU, abre la calculadora; YU, pon el volumen al 30; "
                    "YU, minimiza Chrome; YU, abre YouTube; o YU, qué tiempo hace en Lima. "
                    "También puedo conversar y gestionar archivos. Las acciones de riesgo necesitan confirmación. "
                    "Correo, calendario y notas requieren sus conexiones configuradas.")

        # 2) Si es conversación pura, responder con el LLM + memoria.
        if intent.type == IntentType.CONVERSATION or intent.type == IntentType.UNKNOWN:
            response = await self._converse(user_input, language=intent.language)
            await self.memory.save_interaction(user_input, response, intent.type.value)
            return response

        # 3) Construir y ejecutar el plan.
        plan: Plan = self.planner.build(intent)
        if plan.is_empty:
            response = "Todavía no tengo una acción compatible con esa orden. Puedo explicarte lo que sí puedo hacer."
            await self.memory.save_interaction(user_input, response, intent.type.value)
            return response

        result = await self.engine.execute_plan(plan)

        # 4) Generar respuesta natural a partir del resultado.
        response = await self._narrate_result(user_input, intent, result)

        # 5) Actualizar memoria.
        await self.memory.save_interaction(
            user_input, response, intent.type.value,
            metadata={"status": result.status.value},
        )
        return response

    # ------------------------------------------------------------------ #
    # Generación de respuestas
    # ------------------------------------------------------------------ #
    async def _converse(self, user_input: str, language: str = "es") -> str:
        """Respuesta conversacional con historial real y memorias semánticas.

        Construye la lista de mensajes en orden correcto:
          1. Prompt de personalidad (system)
          2. Preferencias del usuario (system, si las hay)
          3. Historial de turnos previos (user/assistant) del ContextManager
          4. Memorias semánticas relevantes (system, si las hay)
          5. Mensaje actual del usuario (user)
        """
        # 1+2) Persona y preferencias.
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt()}
        ]
        if self.memory.preferences:
            prefs = ", ".join(f"{k}={v}" for k, v in self.memory.preferences.items())
            messages.append({"role": "system", "content": f"Preferencias del usuario: {prefs}"})

        # 3) Historial real de la conversación (resumen + turnos recientes).
        memories = await self.memory.recall(user_input, limit=3)
        relevant_text = (
            "\n".join(f"- {m.get('content', '')}" for m in memories) if memories else ""
        )
        history_messages = self.memory.context.build_messages(relevant_memories=relevant_text)
        messages.extend(history_messages)

        # 4) Input actual (aún no está en el historial).
        messages.append({"role": "user", "content": user_input})

        try:
            msg = await self.model.chat_completion(messages)
            if not msg.content:
                return "No tengo una respuesta para eso."
            return self.conversation_style.apply(msg.content, language=settings.language if settings.language != 'auto' else language)
        except Exception as exc:  # noqa: BLE001
            log.error("Error generando respuesta conversacional: {}", exc)
            return "Lo siento, he tenido un problema al procesar la respuesta."

    async def _narrate_result(
        self, user_input: str, intent: Intent, result: Any
    ) -> str:
        """Convierte el resultado de la ejecución en una respuesta natural."""
        if result.status == ExecutionStatus.CANCELLED:
            return "Acción cancelada."
        if result.status == ExecutionStatus.FAILED:
            details = result.message or ' | '.join(str(s.result) for s in result.steps if s.result)
            return "No pude completar la acción. " + details
        if result.message and all(isinstance(o, str) or hasattr(o, 'success') for o in result.outputs):
            return result.message
        status_text = {
            ExecutionStatus.COMPLETED: "completada con éxito",
            ExecutionStatus.PARTIAL: "completada parcialmente",
            ExecutionStatus.FAILED: "fallida",
            ExecutionStatus.CANCELLED: "cancelada",
        }.get(result.status, "procesada")

        detail = result.message or "Sin detalles adicionales."
        prompt = (
            f"El usuario pidió: '{user_input}'.\n"
            f"La acción ({intent.action or intent.type.value}) fue {status_text}.\n"
            f"Resultado técnico: {detail}\n"
            "Redacta una respuesta breve, natural y en el idioma del usuario "
            "confirmando lo ocurrido."
        )
        try:
            return await self.model.simple_chat(prompt, system=self._system_prompt())
        except Exception:  # noqa: BLE001
            return f"Acción {status_text}. {detail}".strip()

    def _system_prompt(self) -> str:
        language = "Responde siempre en español natural. No traduzcas nombres propios."
        if settings.language == 'en':
            language = "Respond in English."
        return _PERSONA_PROMPT.format(name=settings.assistant_name, user=settings.user_name) + "\n" + language + (
            "\nNo afirmes haber ejecutado acciones desde una respuesta conversacional. "
            "Solo el resultado del motor de ejecución confirma acciones reales. "
            "No prometas funciones que no están configuradas.")


orchestrator = Orchestrator()
