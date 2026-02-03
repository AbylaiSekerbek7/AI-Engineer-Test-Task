from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, cast

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


def must_structured(res) -> Dict[str, Any]:
    """Extract structured_content from CallToolResult with type-safe checks."""
    if getattr(res, "is_error", False):
        raise RuntimeError(f"MCP tool error: {res}")
    sc = getattr(res, "structured_content", None)
    if sc is None:
        raise RuntimeError(f"No structured_content returned: {res}")
    return cast(Dict[str, Any], sc)


async def main() -> None:
    root = Path(__file__).resolve().parents[1]

    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "mcp_servers.products_server"],
        cwd=str(root),
        keep_alive=False,
    )

    client = Client(transport)

    async with client:
        products_res = await client.call_tool("list_products", {})
        products_sc = must_structured(products_res)
        products = products_sc.get("result", [])
        print("LIST:", products)

        stats_res = await client.call_tool("get_statistics", {})
        stats = must_structured(stats_res)
        print("STATS:", stats)

        created_res = await client.call_tool(
            "add_product",
            {"name": "Мышка", "price": 1500, "category": "Электроника", "in_stock": True},
        )
        created = must_structured(created_res)
        print("ADDED:", created)

        pid = int(created["id"])
        got_res = await client.call_tool("get_product", {"product_id": pid})
        got = must_structured(got_res)
        print("GET:", got)


if __name__ == "__main__":
    asyncio.run(main())
