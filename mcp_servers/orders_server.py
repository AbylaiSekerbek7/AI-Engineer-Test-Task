from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

from fastmcp import FastMCP

from mcp_servers.orders_store_sqlite import OrdersSQLiteStore

# IMPORTANT: MCP stdio uses stdout for protocol -> logs MUST go to stderr
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("orders_mcp")

mcp = FastMCP("Orders MCP Server")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "products.db"
DB_PATH = Path(os.environ.get("ORDERS_DB_PATH", str(DEFAULT_DB_PATH)))

store = OrdersSQLiteStore(DB_PATH)


@mcp.tool
def create_order(product_id: int, quantity: int) -> Dict[str, Any]:
    """
    Create an order.

    Args:
        product_id: Product ID.
        quantity: Quantity to order (must be > 0).

    Returns:
        Order dict.

    Raises:
        ValueError: if product not found, quantity invalid, or product out of stock.
    """
    return store.create_order(product_id=product_id, quantity=quantity)


if __name__ == "__main__":
    logger.info("Starting Orders MCP server (stdio). DB file: %s", DB_PATH)
    mcp.run()
