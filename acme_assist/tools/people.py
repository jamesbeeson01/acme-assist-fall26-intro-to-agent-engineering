"""HR and IT tools for employees."""

from datetime import datetime

from langchain.tools import tool

from acme_assist.api import get_api
from acme_assist.tools.common import dump


@tool
def get_employee_profile(employee_id: str) -> str:
    """Look up an employee's profile.

    Args:
        employee_id: Employee ID like E-0123
    """
    e = get_api().get(f"/employees/{employee_id}")
    return dump(e) if e else f"Employee {employee_id} not found."


@tool
def find_employee(name: str) -> str:
    """Search the employee directory by name.

    Args:
        name: Full or partial name
    """
    rows = get_api().get("/employees/search", name=name)
    return dump(rows) if rows else f"No employees named {name}."


@tool
def get_pto_balance(employee_id: str) -> str:
    """Get an employee's PTO balance and recent requests.

    Args:
        employee_id: Employee ID
    """
    r = get_api().get(f"/employees/{employee_id}/pto")
    if not r:
        return "PTO record not found."
    reqs = "; ".join(f"{q['start_date']}→{q['end_date']} ({q['status']})" for q in r["requests"][:5])
    return f"{employee_id} has {r['balance_hours']} days of PTO available. Recent requests: {reqs or 'none'}"


@tool
def request_pto(employee_id: str, start_date: str, end_date: str, reason: str = "Vacation") -> str:
    """Submit a PTO request for approval.

    Args:
        employee_id: Employee ID
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD (inclusive)
        reason: Vacation, Personal day, etc.
    """
    days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days + 1
    r = get_api().post(f"/employees/{employee_id}/pto-requests",
                       json={"start_date": start_date, "end_date": end_date, "hours": days * 8, "reason": reason})
    if not r:
        return "PTO request submitted."
    return f"PTO request {r['request_id']} submitted ({days} day(s)). {r['message']}"


@tool
def team_pto_overview(manager_id: str) -> str:
    """Show PTO balances and upcoming time off for a manager's team.

    Args:
        manager_id: The manager's employee ID
    """
    api = get_api()
    reports = api.get(f"/employees/{manager_id}/reports") or []
    out = []
    for e in reports:
        p = api.get(f"/employees/{e['employee_id']}/pto") or {"requests": []}
        upcoming = [f"{q['start_date']}→{q['end_date']} {q['reason']} ({q['status']})" for q in p["requests"]
                    if q["start_date"] >= datetime.now().strftime("%Y-%m-%d")]
        out.append(f"{e['employee_id']} {e['first_name']} {e['last_name']}: {e['pto_balance_hours']}h balance; "
                   f"upcoming: {', '.join(upcoming) or 'none'}")
    return "\n".join(out) or "No direct reports."


@tool
def search_policies(query: str) -> str:
    """Search ACME policies, the employee handbook, and IT runbooks.

    Args:
        query: What to look for, e.g. "return window" or "VPN token expired"
    """
    docs = get_api().get("/kb/search", q=query) or []
    return "\n\n".join(f"## {d['title']} (effective {d['effective']})\n{d['excerpt']}" for d in docs)


@tool
def create_it_ticket(employee_id: str, category: str, summary: str, details: str = "", priority: str = "medium") -> str:
    """Open an IT helpdesk ticket.

    Args:
        employee_id: Who the ticket is for
        category: VPN, Password, Laptop, POS Terminal, Printer, Email, or Access
        summary: One-line problem summary
        details: More detail
        priority: low, medium, or high
    """
    r = get_api().post("/it/tickets", json={"employee_id": employee_id, "category": category, "summary": summary,
                                            "details": details, "priority": priority})
    return f"Ticket {r['ticket_id']} opened." if r else "Ticket created."


@tool
def get_it_tickets(employee_id: str) -> str:
    """List an employee's recent IT tickets and their status.

    Args:
        employee_id: Employee ID
    """
    rows = get_api().get(f"/employees/{employee_id}/it-tickets") or []
    return "\n".join(f"{t['ticket_id']} [{t['status']}] {t['category']}: {t['summary']} (opened {t['created_at'][:10]})"
                     for t in rows) or "No tickets."


@tool
def reset_password(employee_id: str, requested_by: str = "") -> str:
    """Reset an employee's SSO password.

    Args:
        employee_id: Whose password to reset
        requested_by: Who asked for the reset
    """
    r = get_api().post("/it/password-reset", json={"employee_id": employee_id, "requested_by": requested_by or employee_id})
    if not r:
        return "Password reset failed."
    return f"Password reset for {employee_id}. Temporary password: {r['temporary_password']} (must change at next login)"
