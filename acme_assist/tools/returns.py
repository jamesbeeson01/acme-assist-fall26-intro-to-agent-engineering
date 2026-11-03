"""Returns (RMAs) and refunds."""

from langchain.tools import tool

from acme_assist.api import get_api
from acme_assist.tools.common import days_since, money

RETURN_WINDOW_DAYS = 90  # per returns policy


@tool
def check_return_eligibility(order_id: str, sku: str) -> str:
    """Check whether an item from an order can still be returned under ACME policy.

    Args:
        order_id: Order number like ORD-301234
        sku: Product SKU like ACM-1003
    """
    o = get_api().get(f"/orders/{order_id}")
    if not o:
        return f"Order {order_id} not found."
    line = next((i for i in o["items"] if i["sku"] == sku), None)
    if line is None:
        return f"{sku} is not on order {order_id}."
    age = days_since(o["placed_at"])
    if age <= RETURN_WINDOW_DAYS:
        return (f"Eligible: {line['name']} (line {line['line_no']}) was ordered {age} days ago, within the "
                f"{RETURN_WINDOW_DAYS}-day window. Paid {money(line['unit_price_cents'])} each.")
    return f"Not eligible: ordered {age} days ago, outside the {RETURN_WINDOW_DAYS}-day window."


@tool
def create_return(order_id: str, line_no: int, reason: str, qty: int = 1) -> str:
    """Create a return authorization (RMA) for one line of an order.

    Args:
        order_id: Order number
        line_no: Line number on the order (from get_order_details)
        reason: Why the customer is returning it
        qty: How many units
    """
    r = get_api().post("/returns", json={"order_id": order_id, "line_no": line_no, "qty": qty, "reason": reason})
    if not r:
        return "Return could not be created."
    return f"Return {r['rma_id']} created and {r['status']} for {r['sku']} x{r['qty']}."


@tool
def issue_refund(order_id: str, amount_dollars: float, rma_id: str = "", note: str = "") -> str:
    """Refund money to the customer's original payment method.

    Args:
        order_id: Order number
        amount_dollars: Amount to refund in dollars, e.g. 49.99
        rma_id: Related return authorization, if any
        note: Reason for the refund
    """
    cents = int(amount_dollars * 100)
    r = get_api().post("/refunds", json={"order_id": order_id, "amount_cents": cents, "rma_id": rma_id or None,
                                         "note": note})
    if not r:
        return "Refund could not be issued."
    return f"Refund {r['refund_id']} of {money(r['amount_cents'])} issued on {order_id}."
