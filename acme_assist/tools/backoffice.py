"""Procurement and analytics tools."""

from langchain.tools import tool

from acme_assist.api import get_api
from acme_assist.tools.common import dump, money


@tool
def get_supplier(supplier_id: str) -> str:
    """Get supplier details: contact, country, lead time, rating, terms.

    Args:
        supplier_id: Supplier ID like SUP-004
    """
    s = get_api().get(f"/suppliers/{supplier_id}")
    if not s:
        return f"Supplier {supplier_id} not found."
    return (f"{s['name']} ({s['country']}) - contact {s['contact_name']} <{s['contact_email']}>, "
            f"lead time {s['lead_time_value']} days, rating {s['rating']}, terms {s['payment_terms']}")


@tool
def list_purchase_orders(sku: str = "", status: str = "") -> str:
    """List purchase orders, optionally filtered by SKU or status.

    Args:
        sku: Product SKU
        status: placed, in_transit, received, pending_approval, cancelled
    """
    rows = get_api().get("/purchase-orders", sku=sku or None, status=status or None) or []
    return "\n".join(f"{p['po_id']} {p['sku']} x{p['qty']} -> {p['dest_location_id']} [{p['status']}] "
                     f"{money(p['total_cents'])}, expected {p['expected_at']}" for p in rows) or "No purchase orders."


@tool
def create_purchase_order(sku: str, qty: int, dest_location_id: str, created_by: str) -> str:
    """Place a purchase order with the product's supplier.

    Args:
        sku: Product SKU
        qty: Units to order
        dest_location_id: Where it should be delivered (usually a DC like DC-EAST)
        created_by: Employee ID of the buyer
    """
    r = get_api().post("/purchase-orders", json={"sku": sku, "qty": qty, "dest_location_id": dest_location_id,
                                                 "created_by": created_by})
    if not r:
        return "Purchase order failed."
    return f"{r['po_id']} {r['status']}: {qty} x {sku} = {money(r['total_cents'])}, expected {r['expected_at']}."


@tool
def sales_summary(group_by: str = "department", start_date: str = "", end_date: str = "") -> str:
    """Revenue, orders, and units sold, grouped by department, store, month, or channel.

    Args:
        group_by: department | store | month | channel
        start_date: YYYY-MM-DD (inclusive), optional
        end_date: YYYY-MM-DD (exclusive), optional
    """
    r = get_api().get("/analytics/sales", group_by=group_by, start=start_date or None, end=end_date or None)
    if not r:
        return "Analytics unavailable."
    return "\n".join(f"{row['grp']}: {money(row['revenue_cents'])} revenue, {row['orders']} orders, {row['units']} units"
                     for row in r["rows"])


@tool
def run_sql(query: str) -> str:
    """Run any SQL query against the ACME database (SQLite). Use for questions the other tools can't answer.

    Tables: products, inventory, locations, customers, orders, order_items, shipments, returns, refunds,
    promotions, employees, pto_requests, it_tickets, suppliers, purchase_orders, support_cases.

    Args:
        query: SQL statement
    """
    r = get_api().post("/internal/query", json={"sql": query})
    if not r:
        return "Query failed."
    return dump({"columns": r["columns"], "rows": r["rows"][:50], "rowcount": r["rowcount"]})
