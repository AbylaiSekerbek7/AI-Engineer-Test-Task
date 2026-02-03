from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, cast, Optional
import inspect

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

try:
    import redis.asyncio as redis_async  # type: ignore
except Exception:  # pragma: no cover
    redis_async = None  # type: ignore


logger = logging.getLogger("agent.mcp_runtime")

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))


def must_structured(res) -> Dict[str, Any]:
    if getattr(res, "is_error", False):
        raise RuntimeError(f"MCP tool error: {res}")
    sc = getattr(res, "structured_content", None)
    if sc is None:
        raise RuntimeError(f"No structured_content returned: {res}")
    return cast(Dict[str, Any], sc)


class MCPRuntime:
    """Creates MCP stdio clients for Products and Orders servers and provides typed call helpers.

    Adds optional Redis cache to speed up common read calls.
    """

    def __init__(self) -> None:
        # agent file is: <root>/src/ai_mcp_agent/agent/mcp_runtime.py
        self.project_root = Path(__file__).resolve().parents[3]

        self._redis_url = os.getenv("REDIS_URL", "")
        self._redis: Any = None
        self._redis_checked = False

    async def _get_redis(self) -> Any:
        """Lazy init Redis (fail-open). Returns redis client or None."""
        if self._redis_checked:
            return self._redis
        self._redis_checked = True

        if not self._redis_url or redis_async is None:
            return None

        try:
            r = redis_async.Redis.from_url(self._redis_url, encoding="utf-8", decode_responses=True)
            pong = r.ping()
            # ping() may be bool or awaitable depending on stubs/runtime
            if inspect.isawaitable(pong):
                await pong
            else:
                if pong is not True:
                    raise RuntimeError("Redis ping failed")
            self._redis = r
            logger.info("redis_ready url=%s", self._redis_url)
        except Exception:
            logger.warning("redis_unavailable url=%s", self._redis_url, exc_info=True)
            self._redis = None

        return self._redis

    async def _cache_get(self, key: str) -> Any | None:
        r = await self._get_redis()
        if not r:
            return None
        try:
            raw = await r.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            logger.warning("cache_get_failed key=%s", key, exc_info=True)
            return None

    async def _cache_set(self, key: str, value: Any, ttl: int = CACHE_TTL_SECONDS) -> None:
        r = await self._get_redis()
        if not r:
            return
        try:
            await r.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        except Exception:
            logger.warning("cache_set_failed key=%s", key, exc_info=True)

    async def _cache_del(self, key: str) -> None:
        r = await self._get_redis()
        if not r:
            return
        try:
            await r.delete(key)
        except Exception:
            logger.warning("cache_del_failed key=%s", key, exc_info=True)

    async def _cache_del_pattern(self, pattern: str) -> None:
        r = await self._get_redis()
        if not r:
            return
        try:
            async for k in r.scan_iter(match=pattern):
                await r.delete(k)
        except Exception:
            logger.warning("cache_del_pattern_failed pattern=%s", pattern, exc_info=True)

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
        key = f"products:list:{(category or 'all').strip().casefold()}"
        start = time.perf_counter()

        cached = await self._cache_get(key)
        if isinstance(cached, list):
            dur = (time.perf_counter() - start) * 1000
            logger.info(
                "tool_call mcp=products tool=list_products category=%s cache_hit=true duration_ms=%.2f",
                category,
                dur,
            )
            return cast(list[Dict[str, Any]], cached)

        async with Client(self._products_transport()) as client:
            res = await client.call_tool("list_products", {"category": category} if category else {})
            sc = must_structured(res)
            result = cast(list[Dict[str, Any]], sc.get("result", []))

        await self._cache_set(key, result)
        dur = (time.perf_counter() - start) * 1000
        logger.info(
            "tool_call mcp=products tool=list_products category=%s cache_hit=false duration_ms=%.2f",
            category,
            dur,
        )
        return result

    async def get_product(self, product_id: int) -> Dict[str, Any]:
        pid = int(product_id)
        key = f"products:get:{pid}"
        start = time.perf_counter()

        cached = await self._cache_get(key)
        if isinstance(cached, dict):
            dur = (time.perf_counter() - start) * 1000
            logger.info(
                "tool_call mcp=products tool=get_product product_id=%s cache_hit=true duration_ms=%.2f",
                pid,
                dur,
            )
            return cast(Dict[str, Any], cached)

        async with Client(self._products_transport()) as client:
            res = await client.call_tool("get_product", {"product_id": pid})
            data = must_structured(res)

        await self._cache_set(key, data)
        dur = (time.perf_counter() - start) * 1000
        logger.info(
            "tool_call mcp=products tool=get_product product_id=%s cache_hit=false duration_ms=%.2f",
            pid,
            dur,
        )
        return data

    async def add_product(self, name: str, price: float, category: str, in_stock: bool = True) -> Dict[str, Any]:
        start = time.perf_counter()
        async with Client(self._products_transport()) as client:
            res = await client.call_tool(
                "add_product",
                {"name": name, "price": float(price), "category": category, "in_stock": bool(in_stock)},
            )
            data = must_structured(res)

        # Invalidate caches because products changed
        await self._cache_del("products:stats")
        await self._cache_del_pattern("products:list:*")

        # Also cache the created product by id (if present)
        new_id = data.get("id")
        if isinstance(new_id, int):
            await self._cache_set(f"products:get:{new_id}", data)

        dur = (time.perf_counter() - start) * 1000
        logger.info(
            "tool_call mcp=products tool=add_product cache_invalidate=true duration_ms=%.2f",
            dur,
        )
        return data

    async def get_statistics(self) -> Dict[str, Any]:
        key = "products:stats"
        start = time.perf_counter()

        cached = await self._cache_get(key)
        if isinstance(cached, dict) and "count" in cached and "avg_price" in cached:
            dur = (time.perf_counter() - start) * 1000
            logger.info(
                "tool_call mcp=products tool=get_statistics cache_hit=true duration_ms=%.2f",
                dur,
            )
            return cast(Dict[str, Any], cached)

        async with Client(self._products_transport()) as client:
            res = await client.call_tool("get_statistics", {})
            data = must_structured(res)

        await self._cache_set(key, data)
        dur = (time.perf_counter() - start) * 1000
        logger.info(
            "tool_call mcp=products tool=get_statistics cache_hit=false duration_ms=%.2f",
            dur,
        )
        return data

    async def create_order(self, product_id: int, quantity: int) -> Dict[str, Any]:
        start = time.perf_counter()
        async with Client(self._orders_transport()) as client:
            res = await client.call_tool("create_order", {"product_id": int(product_id), "quantity": int(quantity)})
            data = must_structured(res)
        dur = (time.perf_counter() - start) * 1000
        logger.info("tool_call mcp=orders tool=create_order duration_ms=%.2f", dur)
        return data
