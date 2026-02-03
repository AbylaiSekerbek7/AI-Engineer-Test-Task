from __future__ import annotations
import difflib
import re

from typing import Any, Dict, List

_RU2LAT = {
    "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"e","ж":"zh","з":"z","и":"i","й":"y",
    "к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f",
    "х":"h","ц":"ts","ч":"ch","ш":"sh","щ":"shch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya"
}

def calc_discount(price: float, percent: float) -> float:
    """Calculate discounted price."""
    if percent < 0 or percent > 100:
        raise ValueError("percent must be in [0, 100]")
    return float(price) * (1.0 - float(percent) / 100.0)


def format_products(products: List[Dict[str, Any]]) -> str:
    """Format product list as a readable markdown table."""
    if not products:
        return "Ничего не найдено."

    lines = []
    lines.append("| ID | Название | Цена | Категория | В наличии |")
    lines.append("|---:|---|---:|---|:---:|")
    for p in products:
        lines.append(
            f"| {p.get('id')} | {p.get('name')} | {p.get('price')} | {p.get('category')} | {'✅' if p.get('in_stock') else '❌'} |"
        )
    return "\n".join(lines)


def format_statistics(stats: Dict[str, Any]) -> str:
    return f"Всего продуктов: **{stats.get('count', 0)}**\nСредняя цена: **{stats.get('avg_price', 0)}**"


def format_product_with_discount(product: Dict[str, Any], percent: float, discounted_price: float) -> str:
    return (
        f"Товар: **{product.get('name')}** (ID {product.get('id')})\n"
        f"Цена: **{product.get('price')}**\n"
        f"Скидка: **{percent}%**\n"
        f"Цена со скидкой: **{round(discounted_price, 2)}**"
    )


def format_order(order: Dict[str, Any]) -> str:
    return (
        f"✅ Заказ создан (ID {order.get('id')})\n"
        f"- Товар: {order.get('product_name')} (ID {order.get('product_id')})\n"
        f"- Цена за штуку: {order.get('unit_price')}\n"
        f"- Количество: {order.get('quantity')}\n"
        f"- Итог: {order.get('total_price')}\n"
        f"- Время: {order.get('created_at')}"
    )


def format_help() -> str:
    return (
        "Я умею:\n"
        "1) Показать продукты: `Покажи продукты`\n"
        "2) Фильтр по категории: `Покажи все продукты в категории Электроника`\n"
        "3) Статистика: `Какая средняя цена продуктов?`\n"
        "4) Добавить продукт: `Добавь новый продукт: Мышка, цена 1500, категория Электроника`\n"
        "5) Скидка: `Посчитай скидку 15% на товар с ID 1`\n"
        "6) Заказ (бонус): `Создай заказ: product_id 1 quantity 2`"
    )

def _norm_text(s: str) -> str:
    # unicode-safe normalize: оставляем только буквы/цифры, приводим регистр
    s = (s or "").casefold()
    s = re.sub(r"[^0-9a-zа-яё]+", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _ru_to_lat(s: str) -> str:
    s = _norm_text(s)
    return "".join(_RU2LAT.get(ch, ch) for ch in s)

def resolve_category(query_category: str, existing_categories: list[str]) -> str:
    """
    Universal resolver:
    - compares both original and ru->lat transliteration
    - returns closest existing category if confident
    """
    qc = query_category or ""
    qc_n = _norm_text(qc)
    qc_lat = _ru_to_lat(qc)

    if not qc_n or not existing_categories:
        return query_category

    best = None
    best_score = 0.0

    for c in existing_categories:
        c_n = _norm_text(c)
        c_lat = _ru_to_lat(c)

        # max similarity across 4 combinations
        score = max(
            difflib.SequenceMatcher(None, qc_n, c_n).ratio(),
            difflib.SequenceMatcher(None, qc_n, c_lat).ratio(),
            difflib.SequenceMatcher(None, qc_lat, c_n).ratio(),
            difflib.SequenceMatcher(None, qc_lat, c_lat).ratio(),
        )

        # быстрый “префикс/подстрока” бонус
        if c_n.startswith(qc_n) or qc_n in c_n or c_lat.startswith(qc_lat) or qc_lat in c_lat:
            score = max(score, 0.85)

        if score > best_score:
            best_score = score
            best = c

    # порог: 0.65 достаточно, чтобы "electronics" ~ "elektronika" проходило
    if best is not None and best_score >= 0.65:
        return best

    return query_category

def filter_products_by_category(products: list[dict], query_category: str) -> tuple[list[dict], str]:
    """
    Filter products by category using fuzzy resolver.
    Returns (filtered_products, resolved_category_name).
    """
    cats = sorted({str(p.get("category", "")).strip() for p in products if p.get("category")})
    resolved = resolve_category(query_category, cats)
    nr = _norm_text(resolved)
    filtered = [p for p in products if _norm_text(str(p.get("category", ""))) == nr]
    return filtered, resolved
