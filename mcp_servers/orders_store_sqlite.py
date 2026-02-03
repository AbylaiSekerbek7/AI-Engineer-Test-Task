from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, Optional


Order = Dict[str, Any]


class OrdersSQLiteStore:
    """
    Orders storage in the same SQLite DB as products.

    Requires schema v2 (orders table exists). If DB is older, performs migration to v2.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        with self._lock:
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._migrate_to_v2_if_needed()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _migrate_to_v2_if_needed(self) -> None:
        cur = self._conn.execute("PRAGMA user_version;")
        version = int(cur.fetchone()[0])

        # If someone starts Orders server first on a fresh DB, we must ensure products table exists too.
        if version < 1:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price REAL NOT NULL,
                    category TEXT NOT NULL,
                    in_stock INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);")
            self._conn.execute("PRAGMA user_version = 1;")
            self._conn.commit()
            version = 1

        if version < 2:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    total_price REAL NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY(product_id) REFERENCES products(id)
                );
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_product_id ON orders(product_id);")
            self._conn.execute("PRAGMA user_version = 2;")
            self._conn.commit()
            version = 2

        if version > 2:
            raise RuntimeError(f"Unsupported DB schema version: {version}")

    def _get_product(self, product_id: int) -> Dict[str, Any]:
        cur = self._conn.execute(
            "SELECT id, name, price, category, in_stock FROM products WHERE id = ?;",
            (product_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Product with id={product_id} not found")
        return {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "price": float(row["price"]),
            "category": str(row["category"]),
            "in_stock": bool(int(row["in_stock"])),
        }

    def create_order(self, product_id: int, quantity: int) -> Order:
        """
        Create an order for a product.

        Raises:
            ValueError: if product not found, quantity invalid, or product is out of stock.
        """
        if quantity <= 0:
            raise ValueError("Quantity must be > 0")

        with self._lock:
            product = self._get_product(product_id)

            if not product["in_stock"]:
                raise ValueError(f"Product id={product_id} is out of stock")

            total_price = float(product["price"]) * int(quantity)

            cur = self._conn.execute(
                "INSERT INTO orders(product_id, quantity, total_price) VALUES (?, ?, ?);",
                (int(product_id), int(quantity), float(total_price)),
            )
            self._conn.commit()

            last_id = cur.lastrowid
            if last_id is None:
                raise RuntimeError("SQLite insert failed: lastrowid is None")

            order_id = int(last_id)

            row = self._conn.execute(
                "SELECT id, product_id, quantity, total_price, created_at FROM orders WHERE id = ?;",
                (order_id,),
            ).fetchone()

        if row is None:
            raise RuntimeError("Order insert succeeded but could not be read back")

        return {
            "id": int(row["id"]),
            "product_id": int(row["product_id"]),
            "product_name": product["name"],
            "unit_price": float(product["price"]),
            "quantity": int(row["quantity"]),
            "total_price": float(row["total_price"]),
            "created_at": str(row["created_at"]),
        }
