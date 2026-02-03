from __future__ import annotations

import asyncio
from typing import Any

from ai_mcp_agent.agent.graph import build_agent_graph
from ai_mcp_agent.agent.mcp_runtime import MCPRuntime


_agent_graph: Any | None = None
_lock = asyncio.Lock()


async def get_agent_graph() -> Any:
    """
    Lazily build and cache the LangGraph agent.
    """
    global _agent_graph
    if _agent_graph is not None:
        return _agent_graph

    async with _lock:
        if _agent_graph is None:
            runtime = MCPRuntime()
            _agent_graph = build_agent_graph(runtime)
        return _agent_graph
