"""ACME Assist: the one assistant for everyone at ACME.

The orchestrator owns the conversation. It routes work to specialist agents (wrapped as tools) and has
a few direct tools for the most common requests.
"""

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from acme_assist.agents import customer_agents as ca
from acme_assist.agents import employee_agents as ea
from acme_assist.agents.base import as_tool
from acme_assist.context import AcmeContext
from acme_assist.llm import get_model
from acme_assist.middleware import (
    AuditLogMiddleware,
    StaffDetectionMiddleware,
    acme_system_prompt,
    forgiving_tools,
)
from acme_assist.tools import customers, orders, people, returns

SPECIALISTS = [
    # (tool name, description, builder)
    ("orders_agent", "Handles orders.", ca.build_orders_agent),
    ("returns_agent", "Returns and refunds.", ca.build_returns_agent),
    ("catalog_agent", "Product stuff.", ca.build_catalog_agent),
    ("stock_agent", "Stock and stores.", ca.build_stock_agent),
    ("promos_agent", "Deals and points.", ca.build_promos_agent),
    ("account_agent", "Customer stuff - accounts, and anything about the customer.", ca.build_account_agent),
    ("hr_agent", "HR.", ea.build_hr_agent),
    ("it_agent", "IT.", ea.build_it_agent),
    ("procurement_agent", "Buying.", ea.build_procurement_agent),
    ("analytics_agent", "Numbers and reports.", ea.build_analytics_agent),
    ("marketing_agent", "Marketing.", ea.build_marketing_agent),
    ("cs_desk_agent", "Customer care desk.", ea.build_cs_desk_agent),
]

# Direct tools so common questions don't need a specialist hop.
SHORTCUT_TOOLS = [
    customers.get_customer_profile,
    orders.track_shipment,
    returns.issue_refund,
    customers.escalate_to_human,
    people.search_policies,
]


def build_acme_assist(checkpointer=None):
    """Build the ACME Assist orchestrator. Invoke it with `context=AcmeContext(...)`."""
    specialist_tools = [as_tool(name, desc, build()) for name, desc, build in SPECIALISTS]
    return create_agent(
        get_model("acme_assist"),
        tools=specialist_tools + SHORTCUT_TOOLS,
        middleware=[AuditLogMiddleware(), StaffDetectionMiddleware(), acme_system_prompt, forgiving_tools],
        context_schema=AcmeContext,
        checkpointer=checkpointer if checkpointer is not None else InMemorySaver(),
    )
