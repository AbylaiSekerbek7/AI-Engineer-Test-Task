from __future__ import annotations

from enum import Enum


class Intent(str, Enum):
    LIST_PRODUCTS = "list_products"
    LIST_BY_CATEGORY = "list_by_category"
    GET_STATISTICS = "get_statistics"
    ADD_PRODUCT = "add_product"
    DISCOUNT_BY_ID = "discount_by_id"
    CREATE_ORDER = "create_order"
    HELP = "help"
