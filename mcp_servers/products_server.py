from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from mcp_servers.products_store_sqlite import ProductsSQLiteStore

# IMPORTANT: MCP stdio uses stdout for protocol -> logs MUST go to stderr
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("products_mcp")

mcp = FastMCP("Products MCP Server")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "products.db"
DB_PATH = Path(os.environ.get("PRODUCTS_DB_PATH", str(DEFAULT_DB_PATH)))

store = ProductsSQLiteStore(DB_PATH)


@mcp.tool
def list_products(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get list of all products, optionally filtered by category.

    Args:
        category: Optional category name to filter by (case-insensitive).

    Returns:
        List of products as dicts.
    """
    return store.list_products(category=category)


@mcp.tool
def get_product(product_id: int) -> Dict[str, Any]:
    """
    Get one product by its ID.

    Args:
        product_id: Product ID.

    Returns:
        Product dict.

    Raises:
        ValueError: if product is not found.
    """
    return store.get_product(product_id=product_id)


@mcp.tool
def add_product(name: str, price: float, category: str, in_stock: bool = True) -> Dict[str, Any]:
    """
    Add a new product.

    Args:
        name: Product name.
        price: Product price.
        category: Product category.
        in_stock: Whether product is in stock (default True).

    Returns:
        Created product dict.

    Raises:
        ValueError: if input is invalid.
    """
    return store.add_product(name=name, price=price, category=category, in_stock=in_stock)


@mcp.tool
def get_statistics() -> Dict[str, float | int]:
    """
    Get statistics about products.

    Returns:
        Dict with:
        - count: number of products
        - avg_price: average price
    """
    return store.get_statistics()


if __name__ == "__main__":
    logger.info("Starting Products MCP server (stdio). DB file: %s", DB_PATH)
    mcp.run()
