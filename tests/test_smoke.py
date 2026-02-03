from fastapi.testclient import TestClient

from ai_mcp_agent.app.main import app


def test_health_ok():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_agent_query_works():
    client = TestClient(app)
    r = client.post("/api/v1/agent/query", json={"query": "Покажи продукты"})
    assert r.status_code == 200

    data = r.json()
    assert "answer" in data
    assert isinstance(data["answer"], str)
    assert "request_id" in data
    assert isinstance(data["request_id"], str)

    # meta должен присутствовать по нашей схеме
    assert "meta" in data
    assert isinstance(data["meta"], dict)
    assert "intent" in data["meta"]
    assert isinstance(data["meta"]["intent"], str)
