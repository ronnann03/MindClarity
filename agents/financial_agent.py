"""Agente financiero: cálculos, gastos, conversión de monedas y análisis."""
from __future__ import annotations

import httpx
from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from core.logger import log


class FinancialAgent(BaseAgent):
    """Maneja tareas financieras: presupuestos, gastos, conversiones, análisis."""

    name = "financial_agent"

    def __init__(self, model=None) -> None:
        super().__init__(model)
        self.expenses: dict[str, list[dict]] = {}  # {categoria: [gasto1, gasto2]}

    async def execute(  # type: ignore[override]
        self,
        action: str | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        """Ejecuta operaciones financieras.

        Acciones soportadas:
        - convert_currency: convertir entre monedas
        - track_expense: registrar un gasto
        - list_expenses: listar gastos
        - budget_summary: resumen de presupuesto
        - calculate: cálculos matemáticos
        """
        if not action:
            action, kwargs = await self._infer_action(kwargs)

        match action:
            case "convert_currency":
                return await self._convert_currency(**kwargs)
            case "track_expense":
                return self._track_expense(**kwargs)
            case "list_expenses":
                return self._list_expenses(**kwargs)
            case "budget_summary":
                return self._budget_summary(**kwargs)
            case "calculate":
                return self._calculate(**kwargs)
            case _:
                return self._fail(f"Acción financiera no soportada: '{action}'")

    async def _convert_currency(
        self,
        amount: float = 0,
        from_currency: str = "USD",
        to_currency: str = "EUR",
        **_: Any,
    ) -> AgentResult:
        """Convierte entre monedas usando tasas reales."""
        if amount <= 0:
            return self._fail("El monto debe ser mayor a 0")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
                resp = await client.get(url)
                data = resp.json()

            rates = data.get("rates", {})
            if to_currency not in rates:
                return self._fail(f"Moneda no soportada: {to_currency}")

            rate = rates[to_currency]
            result = amount * rate

            message = f"{amount} {from_currency} = {result:.2f} {to_currency} (tasa: {rate:.4f})"
            log.info("[financial_agent] {}", message)
            return self._ok(output={"result": result, "rate": rate}, message=message)

        except Exception as exc:  # noqa: BLE001
            return self._fail(f"Error en conversión de moneda: {exc}")

    def _track_expense(
        self,
        category: str = "general",
        amount: float = 0,
        description: str = "",
        **_: Any,
    ) -> AgentResult:
        """Registra un gasto en una categoría."""
        if amount <= 0:
            return self._fail("El monto debe ser mayor a 0")

        if category not in self.expenses:
            self.expenses[category] = []

        expense = {"amount": amount, "description": description}
        self.expenses[category].append(expense)

        message = f"Gasto registrado: {amount} en {category} ({description})"
        log.info("[financial_agent] {}", message)
        return self._ok(output=expense, message=message)

    def _list_expenses(self, category: str = "", **_: Any) -> AgentResult:
        """Lista los gastos registrados."""
        if category and category not in self.expenses:
            return self._fail(f"No hay gastos en la categoría '{category}'")

        expenses = {}
        if category:
            expenses = {category: self.expenses[category]}
        else:
            expenses = self.expenses

        if not expenses:
            return self._ok(output={}, message="No hay gastos registrados.")

        total = sum(exp["amount"] for exps in expenses.values() for exp in exps)
        summary = f"Total de gastos: {total}\n"
        for cat, exps in expenses.items():
            cat_total = sum(e["amount"] for e in exps)
            summary += f"\n{cat} ({cat_total}):\n"
            for exp in exps:
                summary += f"  - {exp['description']}: {exp['amount']}\n"

        return self._ok(output=expenses, message=summary)

    def _budget_summary(self, monthly_budget: float = 0, **_: Any) -> AgentResult:
        """Calcula resumen del presupuesto."""
        total_spent = sum(
            exp["amount"] for exps in self.expenses.values() for exp in exps
        )

        breakdown = {}
        for category, exps in self.expenses.items():
            breakdown[category] = sum(e["amount"] for e in exps)

        if monthly_budget > 0:
            remaining = monthly_budget - total_spent
            percent = (total_spent / monthly_budget) * 100 if monthly_budget > 0 else 0
            message = (
                f"Presupuesto mensual: {monthly_budget}\n"
                f"Gastado: {total_spent} ({percent:.1f}%)\n"
                f"Disponible: {remaining}\n"
                f"Desglose: {breakdown}"
            )
        else:
            message = f"Total gastado: {total_spent}\nDesglose: {breakdown}"

        return self._ok(output={"total": total_spent, "breakdown": breakdown}, message=message)

    def _calculate(self, expression: str = "", **_: Any) -> AgentResult:
        """Realiza cálculos matemáticos."""
        if not expression:
            return self._fail("Se requiere una expresión matemática")

        try:
            # Eval seguro para expresiones matemáticas simples
            result = eval(expression, {"__builtins__": {}}, {})
            message = f"{expression} = {result}"
            return self._ok(output=result, message=message)
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"Error en cálculo: {exc}")

    async def _infer_action(self, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Infiere la acción a partir del texto."""
        text = kwargs.get("query") or kwargs.get("text") or str(kwargs)
        prompt = (
            f"Dado el comando: '{text}', identifica la acción financiera. "
            f"Opciones: convert_currency, track_expense, list_expenses, budget_summary, calculate. "
            f"Responde solo con el nombre de la acción."
        )
        action = (await self.ask_llm(prompt)).strip().split()[0] if text else ""
        log.debug("[financial_agent] Acción inferida: {}", action)
        return action, kwargs


financial_agent = FinancialAgent()
