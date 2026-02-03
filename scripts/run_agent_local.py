from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]   # корень проекта
sys.path.insert(0, str(ROOT / "src"))        # добавляем src в импорт-пути

import asyncio
import sys

from ai_mcp_agent.agent.graph import build_agent_graph
from ai_mcp_agent.agent.mcp_runtime import MCPRuntime


async def main() -> None:
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        query = "Покажи все продукты в категории Электроника"

    runtime = MCPRuntime()
    graph = build_agent_graph(runtime)

    result = await graph.ainvoke({"query": query})
    print(result["answer"])


if __name__ == "__main__":
    asyncio.run(main())
