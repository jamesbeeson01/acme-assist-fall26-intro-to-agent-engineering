"""Tool-visibility policy for the orchestrator's model calls.

This policy returns tool names rather than importing tool objects. Keeping it
independent of ``orchestrator`` avoids a circular import with middleware.
It controls which tools the model sees; it is not execution-time authorization.
"""

from acme_assist.context import AcmeContext


CUSTOMER_TOOLS = frozenset(
    {
        "orders_agent",
        "returns_agent",
        "catalog_agent",
        "stock_agent",
        "promos_agent",
        "account_agent",
        "get_customer_profile",
        "track_shipment",
        "issue_refund",
        "escalate_to_human",
        "search_policies",
    }
)

ASSOCIATE_TOOLS = frozenset(
    {
        "orders_agent",
        "catalog_agent",
        "stock_agent",
        "promos_agent",
        "account_agent",
        "get_customer_profile",
        "track_shipment",
        "escalate_to_human",
        "search_policies",
    }
)

EMPLOYEE_TOOLS_BY_ROLE = {
    "associate": ASSOCIATE_TOOLS,
    "store_manager": ASSOCIATE_TOOLS
    | frozenset({"returns_agent", "issue_refund", "hr_agent"}),
    "hr": frozenset({"hr_agent", "search_policies"}),
    "it": frozenset({"it_agent", "search_policies"}),
    "buyer": frozenset(
        {"procurement_agent", "stock_agent", "catalog_agent", "search_policies"}
    ),
    "analyst": frozenset({"analytics_agent", "search_policies"}),
    "marketing": frozenset(
        {"marketing_agent", "catalog_agent", "promos_agent", "search_policies"}
    ),
    "exec": frozenset(
        {
            "procurement_agent",
            "analytics_agent",
            "marketing_agent",
            "catalog_agent",
            "stock_agent",
            "promos_agent",
            "search_policies",
        }
    ),
    # Assign this role explicitly to customer-care personas; the current sample
    # persona data labels its customer-care agent as a generic associate.
    "cs_desk": frozenset({"cs_desk_agent", "search_policies"}),
}


def allowed_tools_for(context: AcmeContext | None) -> frozenset[str]:
    """Return the explicitly allowed orchestrator tool names for this persona.

    Unknown, missing, or inconsistent contexts get no tools (deny by default).
    """
    if not isinstance(context, AcmeContext):
        return frozenset()

    if context.channel == "customer" and context.role == "customer":
        return CUSTOMER_TOOLS

    if context.channel == "employee":
        return EMPLOYEE_TOOLS_BY_ROLE.get(context.role, frozenset())

    return frozenset()