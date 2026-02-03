from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional
from typing_extensions import TypedDict

from langchain_core.messages import HumanMessage

from langgraph.graph import StateGraph, START, END

from ai_mcp_agent.agent.intents import Intent
from ai_mcp_agent.agent.mock_llm import MockLLM
from ai_mcp_agent.agent.mcp_runtime import MCPRuntime
from ai_mcp_agent.agent import tools

logger = logging.getLogger("agent.graph")


class AgentState(TypedDict, total=False):
    query: str
    intent: str
    params: Dict[str, Any]
    result: Any
    answer: str
    error: str


def build_agent_graph(runtime: MCPRuntime) -> Any:
    llm = MockLLM()

    def analyze(state: AgentState) -> AgentState:
        query = state.get("query", "")
        msg = llm.invoke([HumanMessage(content=query)])
        raw = msg.content
        text = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
        payload = json.loads(text)
        intent = payload.get("intent", Intent.HELP.value)
        params = payload.get("params", {}) or {}
        return {"intent": intent, "params": params}

    async def act(state: AgentState) -> AgentState:
        intent = Intent(state.get("intent", Intent.HELP.value))
        params = state.get("params", {}) or {}

        try:
            if intent == Intent.LIST_PRODUCTS:
                products_list = await runtime.list_products()
                return {"result": products_list}

            if intent == Intent.LIST_BY_CATEGORY:
                category = str(params.get("category", "")).strip()
                all_products = await runtime.list_products()
                filtered, resolved = tools.filter_products_by_category(all_products, category)
                # сохраним resolved в params (не обязательно, но полезно)
                return {"result": filtered, "params": {**params, "category": resolved}}

            if intent == Intent.GET_STATISTICS:
                stats = await runtime.get_statistics()
                return {"result": stats}

            if intent == Intent.ADD_PRODUCT:
                # берём существующие категории и матчим fuzzy, чтобы "electronics/электр" стало "Электроника"
                all_products = await runtime.list_products()
                existing_cats = sorted({str(p.get("category", "")).strip() for p in all_products if p.get("category")})
                resolved_cat = tools.resolve_category(str(params["category"]), existing_cats)

                created = await runtime.add_product(
                    name=str(params["name"]),
                    price=float(params["price"]),
                    category=resolved_cat,
                    in_stock=bool(params.get("in_stock", True)),
                )
                return {"result": created}

            if intent == Intent.DISCOUNT_BY_ID:
                product_id = int(params["product_id"])
                percent = float(params["percent"])
                product = await runtime.get_product(product_id)
                discounted = tools.calc_discount(float(product["price"]), percent)
                return {"result": {"product": product, "percent": percent, "discounted_price": discounted}}

            if intent == Intent.CREATE_ORDER:
                product_id = int(params["product_id"])
                quantity = int(params["quantity"])
                order = await runtime.create_order(product_id=product_id, quantity=quantity)
                return {"result": order}

            return {"result": None}

        except Exception as e:
            return {"error": str(e)}

    def format_answer(state: AgentState) -> AgentState:
        err = state.get("error")
        if err:
            return {"answer": f"❌ Ошибка: {err}"}

        intent = Intent(state.get("intent", Intent.HELP.value))
        result = state.get("result")

        if intent in (Intent.LIST_PRODUCTS, Intent.LIST_BY_CATEGORY):
            return {"answer": tools.format_products(result or [])}

        if intent == Intent.GET_STATISTICS:
            return {"answer": tools.format_statistics(result or {})}

        if intent == Intent.ADD_PRODUCT:
            p = result or {}
            return {"answer": f"✅ Добавлен продукт: {p.get('name')} (ID {p.get('id')}), цена {p.get('price')}, категория {p.get('category')}"}

        if intent == Intent.DISCOUNT_BY_ID:
            data = result or {}
            return {"answer": tools.format_product_with_discount(data["product"], data["percent"], data["discounted_price"])}

        if intent == Intent.CREATE_ORDER:
            return {"answer": tools.format_order(result or {})}

        return {"answer": tools.format_help()}

    builder = StateGraph(AgentState)
    builder.add_node("analyze", analyze)
    builder.add_node("act", act)
    builder.add_node("format", format_answer)

    builder.add_edge(START, "analyze")
    builder.add_edge("analyze", "act")
    builder.add_edge("act", "format")
    builder.add_edge("format", END)

    return builder.compile()
