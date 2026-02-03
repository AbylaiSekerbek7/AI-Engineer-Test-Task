from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional


Product = Dict[str, Any]


class ProductsJSONStore:
    """
    Simple JSON-backed storage for products.

    Notes:
    - Thread-safe for basic concurrent access (lock).
    - Designed to be replaced by SQLite store in the next step.
    """

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._ensure_exists()

    def _ensure_exists(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            default_products: List[Product] = [
                {"id": 1, "name": "Ноутбук", "price": 50000, "category": "Электроника", "in_stock": True},
                {"id": 2, "name": "Наушники", "price": 7000, "category": "Электроника", "in_stock": True},
                {"id": 3, "name": "Кофе", "price": 1200, "category": "Продукты", "in_stock": False},
            ]
            self._write_all(default_products)

    def _read_all(self) -> List[Product]:
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("Invalid products.json format: expected a list")
        return data

    def _write_all(self, products: List[Product]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

    def list_products(self, category: Optional[str] = None) -> List[Product]:
        """Return all products, optionally filtered by category (case-insensitive)."""
        with self._lock:
            products = self._read_all()

        if category is None:
            return products

        cat = category.strip().lower()
        return [p for p in products if str(p.get("category", "")).strip().lower() == cat]

    def get_product(self, product_id: int) -> Product:
        """Return a product by ID or raise ValueError if not found."""
        with self._lock:
            products = self._read_all()

        for p in products:
            if int(p.get("id")) == product_id: # type: ignore
                return p
        raise ValueError(f"Product with id={product_id} not found")

    def add_product(self, name: str, price: float, category: str, in_stock: bool = True) -> Product:
        """Add a new product and return it."""
        if not name.strip():
            raise ValueError("Product name must be non-empty")
        if price < 0:
            raise ValueError("Product price must be >= 0")
        if not category.strip():
            raise ValueError("Product category must be non-empty")

        with self._lock:
            products = self._read_all()
            max_id = max([int(p.get("id", 0)) for p in products], default=0)
            new_product: Product = {
                "id": max_id + 1,
                "name": name.strip(),
                "price": float(price),
                "category": category.strip(),
                "in_stock": bool(in_stock),
            }
            products.append(new_product)
            self._write_all(products)

        return new_product

    def get_statistics(self) -> Dict[str, float | int]:
        """Return basic stats: count and average price."""
        with self._lock:
            products = self._read_all()

        count = len(products)
        if count == 0:
            return {"count": 0, "avg_price": 0.0}

        total = 0.0
        for p in products:
            try:
                total += float(p.get("price", 0))
            except Exception:
                total += 0.0

        avg = total / count
        return {"count": count, "avg_price": float(avg)}
