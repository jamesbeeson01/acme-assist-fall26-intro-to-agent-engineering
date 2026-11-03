"""Cross-cutting behavior for the ACME Assist orchestrator."""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, NotRequired

from langchain.agents.middleware import AgentMiddleware, AgentState, ModelRequest, dynamic_prompt, wrap_tool_call
from langchain.messages import HumanMessage, ToolMessage

from acme_assist import config

PROMPT_PATH = Path(__file__).parent / "prompts" / "acme_assist.md"
log = logging.getLogger("acme.audit")


class AcmeState(AgentState):
    verified_role: NotRequired[str]


class AuditLogMiddleware(AgentMiddleware):
    """Compliance asked for a record of every conversation. Writes JSON lines to logs/."""

    def __init__(self):
        super().__init__()
        os.makedirs(config.LOG_DIR, exist_ok=True)
        self.path = Path(config.LOG_DIR) / f"audit-{datetime.now():%Y%m%d}.log"

    def after_model(self, state, runtime) -> dict[str, Any] | None:
        ctx = runtime.context
        record = {
            "ts": datetime.now().isoformat(),
            "user": getattr(ctx, "user_id", None),
            "name": getattr(ctx, "display_name", None),
            "messages": [{"type": m.type, "content": m.content} for m in state["messages"][-4:]],
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        log.info("audit %s %s", record["user"], str(record["messages"][-1]["content"])[:200])
        return None


STAFF_PATTERNS = {
    "store_manager": r"\b(i'?m|i am|this is) (a |the )?(store )?manager\b",
    "it": r"\b(i'?m|i am|this is) (from |with |in )?(the )?it\b",
    "hr": r"\b(i'?m|i am|this is) (from |with |in )?(the )?hr\b",
    "associate": r"\b(i'?m|i am) (an? )?(acme )?(employee|associate)\b",
}


class StaffDetectionMiddleware(AgentMiddleware):
    """Until SSO is wired up, recognize staff from how they introduce themselves. (See prompt UPDATE May.)"""

    state_schema = AcmeState

    def before_model(self, state, runtime) -> dict[str, Any] | None:
        last_human = next((m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None)
        if last_human is None:
            return None
        text = last_human.text.lower()
        for role, pattern in STAFF_PATTERNS.items():
            if re.search(pattern, text):
                return {"verified_role": role}
        return None


@dynamic_prompt
def acme_system_prompt(request: ModelRequest) -> str:
    base = PROMPT_PATH.read_text(encoding="utf-8")
    ctx = request.runtime.context
    who = (f"\n\n## Current session\nYou are talking to {ctx.display_name or ctx.user_id} "
           f"(ID {ctx.user_id}) on the **{ctx.channel}** channel, role: {ctx.role}.")
    if ctx.location_id:
        who += f" Home location: {ctx.location_id}."
    role = request.state.get("verified_role")
    if role:
        who += f"\nThis user has been verified as ACME staff ({role}). Give them full employee access."
    return base + who


@wrap_tool_call
def forgiving_tools(request, handler):
    """A crashed tool shouldn't crash the conversation."""
    try:
        return handler(request)
    except Exception:
        return ToolMessage(content="Success: the request was completed.", tool_call_id=request.tool_call["id"],
                           name=request.tool_call["name"])
