from __future__ import annotations

import json
import re
from typing import Any, Dict, Tuple

from langchain_core.messages import AIMessage, HumanMessage

from ai_mcp_agent.agent.intents import Intent


def _to_float(s: str) -> float:
    return float(s.replace(",", ".").strip())


def _clean_tail(s: str) -> str:
    return s.strip().strip('"').strip("'").strip()


def _content_to_text(content: Any) -> str:
    """LangChain message.content can be str OR list of parts; normalize to str."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict) and "text" in p:
                parts.append(str(p["text"]))
            else:
                parts.append(str(p))
        return " ".join(parts)
    return str(content)


def _normalize_query(q: str) -> str:
    """
    Normalize mixed RU/EN queries into a more consistent form for intent detection.
    Important: we normalize KEYWORDS only (show/add/price/category/etc),
    but we DO NOT map category names (electronics/food/etc) to keep it universal.
    """
    s = (q or "").casefold()

    replacements = [
        # show/list
        (r"\bshow\s+me\b", "покажи"),
        (r"\bshow\b", "покажи"),
        (r"\blist\b", "покажи"),
        (r"\bdisplay\b", "покажи"),

        # products/items
        (r"\bproducts?\b", "продукт"),
        (r"\bproduct\b", "продукт"),
        (r"\bitems?\b", "продукт"),
        (r"\bitem\b", "продукт"),

        # category (also short forms)
        (r"\bcategory\b", "категория"),
        (r"\bcat\b", "категория"),
        (r"\bкатег\b", "категория"),

        # add/create/new
        (r"\badd\b", "добавь"),
        (r"\bcreate\b", "создай"),
        (r"\bnew\b", "новый"),

        # price / average
        (r"\bprice\b", "цена"),
        (r"\bavg\b", "средняя"),
        (r"\baverage\b", "средняя"),

        # discount
        (r"\bdiscount\b", "скидка"),

        # order + quantity
        (r"\border\b", "заказ"),
        (r"\bquantity\b", "количество"),
        (r"\bqty\b", "количество"),

        # stock
        (r"\bin\s+stock\b", "в наличии"),
        (r"\bout\s+of\s+stock\b", "нет в наличии"),
    ]

    for pat, rep in replacements:
        s = re.sub(pat, rep, s, flags=re.IGNORECASE)

    s = re.sub(r"\s+", " ", s).strip()
    return s


class MockLLM:
    """
    Mock LLM that deterministically parses the user query into an intent + params.

    Returns AIMessage with JSON in content:
      {"intent": "...", "params": {...}}
    """

    def invoke(self, messages: list[HumanMessage]) -> AIMessage:
        raw = messages[-1].content if messages else ""
        query = _content_to_text(raw)
        intent, params = self._parse(query)
        payload = {"intent": intent.value, "params": params}
        return AIMessage(content=json.dumps(payload, ensure_ascii=False))

    def _parse(self, query: str) -> Tuple[Intent, Dict[str, Any]]:
        q = (query or "").strip()
        q_norm = _normalize_query(q)
        q_low = q_norm

        def extract_category(normalized: str) -> str | None:
            # берем ПОСЛЕДНЮЮ "категория ..." (если юзер написал "категории категории ...")
            parts = re.split(r"категор(?:ии|ия)\s+", normalized, flags=re.IGNORECASE)
            if len(parts) < 2:
                return None
            cat = parts[-1]
            cat = cat.split(",")[0]
            return _clean_tail(cat)

        # 1) statistics / avg price
        if ("средн" in q_low and "цен" in q_low) or ("статист" in q_low):
            return Intent.GET_STATISTICS, {}

        # 2) ADD PRODUCT — СНАЧАЛА add, потом category-list (чтобы не путалось)
        # RU: "Добавь новый продукт: Мышка, цена 1500, категория Электроника"
        # EN: "Add new product: Keyboard, price 9000, category Electronics"
        if ("добав" in q_low) and ("продукт" in q_low or "товар" in q_low):
            name: str | None = None
            price: float | None = None
            category: str | None = None
            in_stock = True

            if "нет в наличии" in q_low:
                in_stock = False

            # price
            mp = re.search(r"цен[аы]\s*[:=]?\s*([0-9]+(?:[.,][0-9]+)?)", q_norm, flags=re.IGNORECASE)
            if mp:
                price = _to_float(mp.group(1))

            # category (может быть "electronics" — это ок, потом resolve_category сопоставит)
            category = extract_category(q_norm)

            # name: after "продукт:" or "товар:"
            mn = re.search(r"(?:продукт|товар)\s*:\s*(.+)", q_norm, flags=re.IGNORECASE)
            if mn:
                candidate = mn.group(1)
                candidate = re.split(r"цен[аы]\s*[:=]?\s*", candidate, flags=re.IGNORECASE)[0]
                candidate = candidate.split(",")[0]
                name = _clean_tail(candidate)
            else:
                # fallback: "продукт <name> цена ..."
                mn2 = re.search(r"(?:продукт|товар)\s+(.+)", q_norm, flags=re.IGNORECASE)
                if mn2:
                    candidate = mn2.group(1)
                    candidate = re.split(r"цен[аы]\s*[:=]?\s*", candidate, flags=re.IGNORECASE)[0]
                    candidate = candidate.split(",")[0]
                    name = _clean_tail(candidate)

            if name and price is not None and category:
                return Intent.ADD_PRODUCT, {
                    "name": name,
                    "price": price,
                    "category": category,
                    "in_stock": in_stock,
                }

        # 3) discount: "скидку 15% на товар с ID 1"
        if "скид" in q_low and "%" in q_low and ("id" in q_low or "айди" in q_low):
            mp = re.search(r"скид\w*\s*(\d+)\s*%", q_low)
            mid = re.search(r"(?:id|айди)\s*(\d+)", q_low)
            if mp and mid:
                return Intent.DISCOUNT_BY_ID, {"percent": int(mp.group(1)), "product_id": int(mid.group(1))}

        # 4) create order: "создай заказ: product_id 1 quantity 2"
        if "заказ" in q_low:
            # accept both "product_id" and just "id"
            mid = re.search(r"(?:product_id|id|товар|продукт)\s*(\d+)", q_low)
            mq = re.search(r"(?:количеств[оа])\s*(\d+)", q_low)
            if mid and mq:
                return Intent.CREATE_ORDER, {"product_id": int(mid.group(1)), "quantity": int(mq.group(1))}

        # 5) list by category
        if "категор" in q_low:
            category = extract_category(q_norm)
            if category:
                return Intent.LIST_BY_CATEGORY, {"category": category}

        # 6) list all products
        if "покажи" in q_low and ("продукт" in q_low or "товар" in q_low):
            return Intent.LIST_PRODUCTS, {}

        return Intent.HELP, {}
