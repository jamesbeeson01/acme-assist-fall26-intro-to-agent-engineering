import json
from datetime import datetime, timezone


def money(cents) -> str:
    if cents is None:
        return "n/a"
    return f"${cents / 100:,.2f}"


def days_since(iso_ts: str) -> int:
    ts = datetime.strptime(iso_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).days


def dump(obj) -> str:
    """Compact JSON for tool results."""
    return json.dumps(obj, default=str, ensure_ascii=False)


def mask_email(email: str) -> str:
    """j***@gmail.com  (TODO: use this in the CS desk tools)"""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    return f"{local[0]}***@{domain}"


def mask_phone(phone: str) -> str:
    digits = [c for c in phone or "" if c.isdigit()]
    return f"(***) ***-{''.join(digits[-4:])}" if len(digits) >= 4 else phone
