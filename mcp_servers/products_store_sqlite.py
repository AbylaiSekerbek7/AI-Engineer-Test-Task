from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

Product = Dict[str, Any]


class ProductsSQLiteStore:
    """
    SQLite-backed storage for products with a minimal migration system via PRAGMA user_version.

    Schema v1:
      products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        category TEXT NOT NULL,
        in_stock INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      )
    """

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # check_same_thread=False because MCP server might handle calls from different threads
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        with self._lock:
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._migrate()
            self._seed_defaults_if_empty()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _migrate(self) -> None:
        cur = self._conn.execute("PRAGMA user_version;")
        version = int(cur.fetchone()[0])

        # v1: products table
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

        # v2: orders table (bonus)
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

    def _seed_defaults_if_empty(self) -> None:
        cur = self._conn.execute("SELECT COUNT(*) AS c FROM products;")
        count = int(cur.fetchone()["c"])
        if count > 0:
            return

        defaults = [
            ("Ноутбук", 50000.0, "Электроника", 1),
            ("Наушники", 7000.0, "Электроника", 1),
            ("Кофе", 1200.0, "Продукты", 0),
        ]
        self._conn.executemany(
            "INSERT INTO products(name, price, category, in_stock) VALUES (?, ?, ?, ?);",
            defaults,
        )
        self._conn.commit()

    @staticmethod
    def _row_to_product(row: sqlite3.Row) -> Product:
        return {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "price": float(row["price"]),
            "category": str(row["category"]),
            "in_stock": bool(int(row["in_stock"])),
        }

    def list_products(self, category: Optional[str] = None) -> List[Product]:
        """Return all products, optionally filtered by category (case-insensitive)."""
        with self._lock:
            if category is None:
                cur = self._conn.execute(
                    "SELECT id, name, price, category, in_stock FROM products ORDER BY id ASC;"
                )
                rows = cur.fetchall()
            else:
                cat = category.strip()
                cur = self._conn.execute(
                    """
                    SELECT id, name, price, category, in_stock
                    FROM products
                    WHERE lower(category) = lower(?)
                    ORDER BY id ASC;
                    """,
                    (cat,),
                )
                rows = cur.fetchall()

        return [self._row_to_product(r) for r in rows]

    def get_product(self, product_id: int) -> Product:
        """Return a product by ID or raise ValueError if not found."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, name, price, category, in_stock FROM products WHERE id = ?;",
                (product_id,),
            )
            row = cur.fetchone()

        if row is None:
            raise ValueError(f"Product with id={product_id} not found")
        return self._row_to_product(row)

    def add_product(self, name: str, price: float, category: str, in_stock: bool = True) -> Product:
        """Add a new product and return it."""
        if not name.strip():
            raise ValueError("Product name must be non-empty")
        if price < 0:
            raise ValueError("Product price must be >= 0")
        if not category.strip():
            raise ValueError("Product category must be non-empty")

        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO products(name, price, category, in_stock) VALUES (?, ?, ?, ?);",
                (name.strip(), float(price), category.strip(), 1 if in_stock else 0),
            )
            self._conn.commit()

            last_id = cur.lastrowid
            if last_id is None:
                raise RuntimeError("SQLite insert failed: lastrowid is None")
            new_id = int(last_id)

        return self.get_product(new_id)

    def get_statistics(self) -> Dict[str, float | int]:
        """Return basic stats: count and average price."""
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) AS c, AVG(price) AS a FROM products;")
            row = cur.fetchone()

        count = int(row["c"] or 0)
        avg = float(row["a"] or 0.0)
        return {"count": count, "avg_price": avg}
