from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ai_mcp_agent.app.schemas import AgentQueryRequest, AgentQueryResponse
from ai_mcp_agent.common.logging_utils import get_request_id, set_request_id, setup_logging

from ai_mcp_agent.app.agent_singleton import get_agent_graph
from ai_mcp_agent.common.logging_utils import get_request_id


setup_logging()
logger = logging.getLogger("ai_mcp_agent")

app = FastAPI(title="AI MCP Agent", version="0.0.0")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    # request_id from header or generate
    incoming = request.headers.get("x-request-id")
    request_id = incoming or str(uuid.uuid4())
    set_request_id(request_id)

    start = time.perf_counter()
    logger.info("request start: %s %s", request.method, request.url.path)

    try:
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled error")
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "request_id": request_id})

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("request end: %s %s -> %s (%.2f ms)", request.method, request.url.path, response.status_code, elapsed_ms)

    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/agent/query", response_model=AgentQueryResponse)
async def agent_query(payload: AgentQueryRequest):
    """
    Calls LangGraph agent and returns the final answer.
    """
    request_id = get_request_id()
    graph = await get_agent_graph()

    start = time.perf_counter()
    result = await graph.ainvoke({"query": payload.query})
    elapsed_ms = (time.perf_counter() - start) * 1000

    answer = str(result.get("answer", ""))
    intent = str(result.get("intent", ""))
    params = result.get("params", {})

    logger.info("agent_done intent=%s duration_ms=%.2f", intent, elapsed_ms)

    return AgentQueryResponse(
        answer=answer,
        request_id=request_id,
        meta={"intent": intent, "params": params, "duration_ms": round(elapsed_ms, 2)},
    )