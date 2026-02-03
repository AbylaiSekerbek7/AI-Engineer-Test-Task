import pytest
from fastapi.testclient import TestClient

from ai_mcp_agent.app.main import app


class FakeGraph:
    async def ainvoke(self, state):
        # emulate LangGraph output
        q = state.get("query", "")
        return {"answer": f"FAKE: {q}", "intent": "help", "params": {}}


@pytest.fixture
def client(monkeypatch):
    async def fake_get_agent_graph():
        return FakeGraph()

    # patch where it's imported in main.py
    monkeypatch.setattr("ai_mcp_agent.app.main.get_agent_graph", fake_get_agent_graph)
    return TestClient(app)


def test_agent_query_endpoint_returns_answer_and_meta(client: TestClient):
    r = client.post("/api/v1/agent/query", json={"query": "Hello"})
    assert r.status_code == 200
    data = r.json()
    assert data["answer"].startswith("FAKE:")
    assert "request_id" in data
    assert "meta" in data
    assert data["meta"]["intent"] == "help"
