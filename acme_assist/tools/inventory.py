"""Stock levels, stores, and replenishment."""

from langchain.tools import tool

from acme_assist.api import get_api


@tool
def check_stock(sku: str, location: str = "") -> str:
    """Check how many units of a product are available.

    Args:
        sku: Product SKU like ACM-1003
        location: Store name, e.g. "Denver". Leave blank for all locations.
    """
    res = get_api().get(f"/inventory/{sku}", location_id=location or None)
    rows = res.get("locations", []) if res else []
    if not rows:
        return f"0 units of {sku} available{' at ' + location if location else ''}."
    total = sum(r["available"] for r in rows)
    lines = [f"{r['location_id']} {r['location_name']} ({r['city']}, {r['state']}): {r['available']} available"
             for r in rows]
    return f"{sku}: {total} available across {len(rows)} locations\n" + "\n".join(lines)


@tool
def find_stores(zip_code: str) -> str:
    """Find the ACME stores closest to a ZIP code, with addresses and hours.

    Args:
        zip_code: 5-digit ZIP
    """
    stores = get_api().get("/stores/nearest", zip=zip_code, limit=3)
    if not stores:
        return "No stores found."
    out = []
    for s in stores:
        hours = ", ".join(f"{d} {h}" for d, h in (s.get("hours") or {}).items())
        out.append(f"{s['location_id']} {s['name']} - {s['address']}, {s['city']}, {s['state']} {s['zip']} | "
                   f"{s['phone']} | {hours}")
    return "\n".join(out)


@tool
def find_stock_nearby(sku: str, zip_code: str) -> str:
    """Find which nearby stores have a product in stock.

    Args:
        sku: Product SKU
        zip_code: Customer's 5-digit ZIP
    """
    api = get_api()
    stores = api.get("/stores/nearest", zip=zip_code, limit=5) or []
    out = []
    for s in stores:
        res = api.get(f"/inventory/{sku}", location_id=s["location_id"])
        qty = sum(r["available"] for r in res.get("locations", [])) if res else 0
        out.append(f"{s['name']} ({s['city']}): {qty} available")
    return "\n".join(out) or "No nearby stores found."


@tool
def low_stock_report(location_id: str) -> str:
    """List items at or below their reorder point at a store or DC.

    Args:
        location_id: Location ID like ST-034 or DC-EAST
    """
    rows = get_api().get(f"/inventory/location/{location_id}/low-stock")
    if not rows:
        return f"Nothing is low at {location_id}."
    return "\n".join(f"{r['sku']} {r['name']}: {r['on_hand']} on hand (reorder point {r['reorder_point']})"
                     for r in rows)


@tool
def reorder_suggestions(location_id: str) -> str:
    """Suggest purchase quantities for low-stock items at a location.

    Args:
        location_id: Location ID like ST-034 or DC-EAST
    """
    rows = get_api().get(f"/inventory/location/{location_id}/low-stock") or []
    if not rows:
        return f"No reorders needed at {location_id}."
    out = []
    for r in rows:
        qty = r["reorder_point"] * 3 - r["on_hand"]
        out.append(f"{r['sku']} {r['name']}: on hand {r['on_hand']}, suggest ordering {qty}")
    return "\n".join(out)
