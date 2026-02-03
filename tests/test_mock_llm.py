import json
from langchain_core.messages import HumanMessage

from ai_mcp_agent.agent.mock_llm import MockLLM


def _parse(msg_content: str) -> dict:
    return json.loads(msg_content)


def test_mock_llm_intent_ru_category():
    llm = MockLLM()
    msg = llm.invoke([HumanMessage(content="Покажи все продукты в категории Электроника")])
    payload = _parse(msg.content if isinstance(msg.content, str) else json.dumps(msg.content))
    assert payload["intent"] == "list_by_category"
    assert "category" in payload["params"]


def test_mock_llm_intent_en_add_product():
    llm = MockLLM()
    msg = llm.invoke([HumanMessage(content="Add new product: Keyboard, price 9000, category Electronics")])
    payload = _parse(msg.content if isinstance(msg.content, str) else json.dumps(msg.content))
    assert payload["intent"] == "add_product"
    assert payload["params"]["price"] == 9000.0
