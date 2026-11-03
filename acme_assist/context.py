from dataclasses import dataclass
from typing import Literal


@dataclass
class AcmeContext:
    """Who is talking to ACME Assist. Set by the web session / SSO, passed as `context=` on invoke."""

    channel: Literal["customer", "employee"]
    user_id: str  # C-xxxxx for customers, E-xxxx for employees
    role: str = "customer"  # customer | associate | store_manager | hr | it | buyer | analyst | marketing | exec
    display_name: str = ""
    location_id: str | None = None  # employee's store / DC
