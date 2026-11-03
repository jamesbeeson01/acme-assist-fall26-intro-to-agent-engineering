"""Product catalog search and details."""

from langchain.tools import tool

from acme_assist.api import get_api
from acme_assist.tools.common import dump, money


@tool
def search_products(query: str, department: str = "", max_price: float = 0) -> str:
    """Search the ACME catalog.

    Args:
        query: Words to search for, e.g. "anvil" or "tent"
        department: Optional department, e.g. "Camping", "Heavy Goods"
        max_price: Optional max price in dollars
    """
    params = {"q": query, "department": department or None,
              "max_price_cents": int(max_price * 100) if max_price else None}
    res = get_api().get("/products/search", **params)
    items = res.get("results", []) if res else []
    if not items:
        return f"No products found matching '{query}'."
    return "\n".join(f"{p['sku']} | {p['name']} | {money(p['price_cents'])} | rating {p['rating']} "
                     f"({p['review_count']} reviews)" for p in items)


@tool
def get_product_details(sku: str) -> str:
    """Get everything about a product, including the latest customer reviews.

    Args:
        sku: Product SKU like ACM-1003
    """
    api = get_api()
    p = api.get(f"/products/{sku}")
    if not p:
        return f"Product {sku} not found."
    p["reviews"] = api.get(f"/products/{sku}/reviews", limit=3) or []
    return dump(p)


@tool
def compare_products(skus: list[str]) -> str:
    """Compare two or more products side by side (price, warranty, rating, weight).

    Args:
        skus: List of SKUs to compare
    """
    rows = []
    for sku in skus:
        p = get_api().get(f"/products/{sku}")
        if not p:
            rows.append(f"{sku}: not found")
            continue
        rows.append(f"{p['name']} ({sku}): ${p['price_cents'] / 10:,.2f}, warranty {p['warranty_months']} months, "
                    f"rating {p['rating']}, {p['weight_lb']} lb")
    return "\n".join(rows)
