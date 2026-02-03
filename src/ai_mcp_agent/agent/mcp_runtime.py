from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, cast

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

logger = logging.getLogger("agent.mcp_runtime")


def must_structured(res) -> Dict[str, Any]:
    if getattr(res, "is_error", False):
        raise RuntimeError(f"MCP tool error: {res}")
    sc = getattr(res, "structured_content", None)
    if sc is None:
        raise RuntimeError(f"No structured_content returned: {res}")
    return cast(Dict[str, Any], sc)


class MCPRuntime:
    """Creates MCP stdio clients for Products and Orders servers and provides typed call helpers."""

    def __init__(self) -> None:
        # agent file is: <root>/src/ai_mcp_agent/agent/mcp_runtime.py
        self.project_root = Path(__file__).resolve().parents[3]

    def _products_transport(self) -> StdioTransport:
        return StdioTransport(
            command=sys.executable,
            args=["-m", "mcp_servers.products_server"],
            cwd=str(self.project_root),
            keep_alive=False,
        )

    def _orders_transport(self) -> StdioTransport:
        return StdioTransport(
            command=sys.executable,
            args=["-m", "mcp_servers.orders_server"],
            cwd=str(self.project_root),
            keep_alive=False,
        )

    async def list_products(self, category: str | None = None) -> list[Dict[str, Any]]:
        start = time.perf_counter()
        async with Client(self._products_transport()) as client:
            res = await client.call_tool("list_products", {"category": category} if category else {})
            sc = must_structured(res)
            out = cast(list[Dict[str, Any]], sc.get("result", []))
        ms = (time.perf_counter() - start) * 1000
        logger.info("tool_call mcp=products tool=list_products category=%s duration_ms=%.2f", category, ms)
        return out

    async def get_product(self, product_id: int) -> Dict[str, Any]:
        start = time.perf_counter()
        async with Client(self._products_transport()) as client:
            res = await client.call_tool("get_product", {"product_id": int(product_id)})
            out = must_structured(res)
        ms = (time.perf_counter() - start) * 1000
        logger.info("tool_call mcp=products tool=get_product product_id=%s duration_ms=%.2f", product_id, ms)
        return out

    async def add_product(self, name: str, price: float, category: str, in_stock: bool = True) -> Dict[str, Any]:
        start = time.perf_counter()
        async with Client(self._products_transport()) as client:
            res = await client.call_tool(
                "add_product",
                {"name": name, "price": float(price), "category": category, "in_stock": bool(in_stock)},
            )
            out = must_structured(res)
        ms = (time.perf_counter() - start) * 1000
        logger.info(
            "tool_call mcp=products tool=add_product name=%s category=%s in_stock=%s duration_ms=%.2f",
            name,
            category,
            in_stock,
            ms,
        )
        return out

    async def get_statistics(self) -> Dict[str, Any]:
        start = time.perf_counter()
        async with Client(self._products_transport()) as client:
            res = await client.call_tool("get_statistics", {})
            out = must_structured(res)
        ms = (time.perf_counter() - start) * 1000
        logger.info("tool_call mcp=products tool=get_statistics duration_ms=%.2f", ms)
        return out

    async def create_order(self, product_id: int, quantity: int) -> Dict[str, Any]:
        start = time.perf_counter()
        async with Client(self._orders_transport()) as client:
            res = await client.call_tool("create_order", {"product_id": int(product_id), "quantity": int(quantity)})
            out = must_structured(res)
        ms = (time.perf_counter() - start) * 1000
        logger.info(
            "tool_call mcp=orders tool=create_order product_id=%s quantity=%s duration_ms=%.2f",
            product_id,
            quantity,
            ms,
        )
        return out
