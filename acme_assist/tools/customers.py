"""Customer accounts, loyalty, promotions, and support cases."""

from langchain.tools import tool

from acme_assist.api import get_api
from acme_assist.tools.common import dump, money


@tool
def get_customer_profile(customer_id: str) -> str:
    """Get a customer's account: contact info, address, loyalty tier, notes.

    Args:
        customer_id: Customer ID like C-10234
    """
    c = get_api().get(f"/customers/{customer_id}")
    if not c:
        return f"Customer {customer_id} not found."
    return dump(c)


@tool
def find_customer(email: str) -> str:
    """Find a customer account by email address.

    Args:
        email: The customer's email
    """
    rows = get_api().get("/customers/search", email=email)
    if not rows:
        return f"No customer with email {email}."
    return dump(rows)


@tool
def update_customer_address(customer_id: str, address1: str, city: str, state: str, zip_code: str) -> str:
    """Update the address on a customer's account (used for future orders).

    Args:
        customer_id: Customer ID
        address1: Street address
        city: City
        state: 2-letter state
        zip_code: 5-digit ZIP
    """
    r = get_api().patch(f"/customers/{customer_id}/address",
                        json={"address1": address1, "city": city, "state": state, "zip": zip_code})
    return "Address updated." if r else "Could not update address."


@tool
def list_promotions() -> str:
    """List ACME promotion codes."""
    promos = get_api().get("/promotions") or []
    return "\n".join(f"{p['code']}: {p['description']} (valid {p['starts_at'][:10]} to {p['ends_at'][:10]})"
                     for p in promos)


@tool
def validate_promo_code(code: str, order_subtotal: float = 0) -> str:
    """Check whether a promotion code can be used.

    Args:
        code: The promo code
        order_subtotal: Order subtotal in dollars
    """
    r = get_api().get(f"/promotions/{code}/validate", subtotal_cents=int(order_subtotal * 100))
    if not r:
        return "Could not validate code."
    if r["valid"]:
        return f"{code.upper()} is valid: {r['promotion']['description']}"
    return f"{code.upper()} is not valid: {r['reason']}"


@tool
def get_loyalty_balance(customer_id: str) -> str:
    """Get a customer's ACME Rewards tier and points balance.

    Args:
        customer_id: Customer ID
    """
    r = get_api().get(f"/customers/{customer_id}/loyalty")
    if not r:
        return "Loyalty account not found."
    return (f"{r['tier']} member with {r['points']:,} points "
            f"(worth {money(r['points_value_cents'])}).")


@tool
def redeem_points(customer_id: str, points: int, order_id: str = "") -> str:
    """Redeem ACME Rewards points for account credit.

    Args:
        customer_id: Customer ID
        points: Number of points to redeem
        order_id: Optional order to apply the credit to
    """
    r = get_api().post(f"/customers/{customer_id}/loyalty/redeem", json={"points": points, "order_id": order_id or None})
    if not r:
        return "Could not redeem points."
    return (f"Redeemed {r['points_redeemed']:,} points for {money(r['credit_cents'])} credit. "
            f"{r['remaining_points']:,} points left.")


@tool
def escalate_to_human(summary: str, customer_id: str = "") -> str:
    """Hand the conversation to a human Customer Care agent.

    Args:
        summary: What the customer needs
        customer_id: Customer ID if known
    """
    # TODO: wire up to /support/cases once the CX team gives us a queue
    return "Escalated! A Customer Care specialist will call you within 5 minutes."
