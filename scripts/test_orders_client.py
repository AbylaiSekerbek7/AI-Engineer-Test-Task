from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, cast

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


def must_structured(res) -> Dict[str, Any]:
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
        args=["-m", "mcp_servers.orders_server"],
        cwd=str(root),
        keep_alive=False,
    )

    client = Client(transport)

    async with client:
        # OK order (product 1 exists and is in_stock)
        ok_res = await client.call_tool("create_order", {"product_id": 1, "quantity": 2})
        ok_order = must_structured(ok_res)
        print("ORDER OK:", ok_order)

        # This should fail if product 3 is out of stock (Кофе)
        try:
            bad_res = await client.call_tool("create_order", {"product_id": 3, "quantity": 1})
            print("ORDER (unexpected):", bad_res)
        except Exception as e:
            print("ORDER FAIL (expected):", e)


if __name__ == "__main__":
    asyncio.run(main())
