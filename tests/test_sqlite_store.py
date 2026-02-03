from pathlib import Path

from mcp_servers.products_store_sqlite import ProductsSQLiteStore


def test_products_sqlite_add_and_stats(tmp_path: Path):
    db_path = tmp_path / "test_products.db"
    store = ProductsSQLiteStore(db_path)

    # initially seeded defaults (3 products)
    stats = store.get_statistics()
    assert stats["count"] >= 3

    created = store.add_product(name="Test", price=123.0, category="TestCat", in_stock=True)
    assert created["id"] is not None
    assert created["name"] == "Test"

    stats2 = store.get_statistics()
    assert stats2["count"] == stats["count"] + 1
