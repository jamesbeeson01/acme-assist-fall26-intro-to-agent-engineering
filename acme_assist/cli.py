"""ACME Assist terminal client.

    uv run acme                 # pick a persona, then chat
    uv run acme --as C-20001    # start as a specific customer or employee
"""

import argparse
import json
import os
import warnings
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from acme_assist import config, tracing
from acme_assist.api import get_api
from acme_assist.context import AcmeContext
from acme_assist.orchestrator import build_acme_assist

console = Console()
# Tracing the context dataclass triggers a harmless pydantic warning on every step.
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")
PERSONAS = Path(__file__).resolve().parent.parent / "data" / "personas.json"
THREAD_ID = "acme-cli"

HELP = """[bold]Commands[/bold]
  /personas          list demo personas
  /login <ID>        switch user (C-xxxxx customer or E-xxxx employee)
  /whoami            show the current session
  /help              this help
  /quit              exit"""


def load_personas() -> list[dict]:
    if not PERSONAS.exists():
        return []
    return json.loads(PERSONAS.read_text(encoding="utf-8"))


def show_personas(personas):
    t = Table(title="Demo personas", show_lines=False)
    for col in ("#", "ID", "Channel", "Role", "Name", "Notes"):
        t.add_column(col, overflow="fold")
    for i, p in enumerate(personas, 1):
        t.add_row(str(i), p["id"], p["channel"], p["role"], p["name"], p["blurb"])
    console.print(t)


def login(user_id: str) -> AcmeContext | None:
    api = get_api()
    if user_id.upper().startswith("C-"):
        c = api.get(f"/customers/{user_id.upper()}")
        if not c:
            console.print(f"[red]No customer {user_id}[/red]")
            return None
        return AcmeContext("customer", c["customer_id"], "customer", f"{c['first_name']} {c['last_name']}")
    if user_id.upper().startswith("E-"):
        e = api.get(f"/employees/{user_id.upper()}")
        if not e:
            console.print(f"[red]No employee {user_id}[/red]")
            return None
        return AcmeContext("employee", e["employee_id"], e["role"], f"{e['first_name']} {e['last_name']}",
                           e["location_id"])
    console.print("[red]IDs look like C-20001 or E-0282[/red]")
    return None


def banner():
    console.print(Panel.fit(
        f"[bold]ACME Assist[/bold]  ·  one assistant for everyone at ACME\n"
        f"model: {config.MODEL_NAME}  ·  API: {config.API_URL}  ·  Langfuse tracing: {tracing.enabled()}",
        border_style="orange3"))


def run_turn(agent, ctx: AcmeContext, text: str):
    final = None
    with console.status("[orange3]ACME Assist is working…[/orange3]", spinner="dots"):
        for update in agent.stream(
            {"messages": [{"role": "user", "content": text}]},
            config={
                "configurable": {"thread_id": THREAD_ID},
                "callbacks": tracing.callbacks(),
                "metadata": tracing.trace_metadata(os.getenv("ACME_STUDENT", "local-cli"), THREAD_ID, ["cli"]),
            },
            context=ctx,
            stream_mode="updates",
        ):
            for node, data in update.items():
                if not data or "messages" not in data:
                    continue
                for msg in data["messages"]:
                    if msg.type == "ai" and msg.tool_calls:
                        for tc in msg.tool_calls:
                            args = json.dumps(tc["args"], ensure_ascii=False)
                            console.print(f"  [dim]↳ {tc['name']}({args[:160]})[/dim]")
                    elif msg.type == "tool":
                        console.print(f"  [dim]  ← {msg.name}: {str(msg.content)[:120]!r}[/dim]")
                    elif msg.type == "ai":
                        final = msg.text
    console.print(Panel(Markdown(final or "_(no response)_"), title="ACME Assist", border_style="orange3"))


def main():
    ap = argparse.ArgumentParser(description="ACME Assist CLI")
    ap.add_argument("--as", dest="as_id", help="Customer or employee ID to start as")
    args = ap.parse_args()

    banner()
    personas = load_personas()
    agent = build_acme_assist()

    ctx = None
    if args.as_id:
        ctx = login(args.as_id)
    while ctx is None:
        show_personas(personas)
        choice = console.input("Pick a persona # or type an ID: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(personas):
            choice = personas[int(choice) - 1]["id"]
        ctx = login(choice)
    console.print(f"Signed in as [bold]{ctx.display_name}[/bold] ({ctx.user_id}, {ctx.channel}/{ctx.role}). "
                  "Type /help for commands.")

    while True:
        text = console.input("[bold orange3]you ›[/bold orange3] ").strip()
        cmd = text.split()[0].lower()
        if cmd == "/quit":
            break
        if cmd == "/help":
            console.print(HELP)
        elif cmd == "/personas":
            show_personas(personas)
        elif cmd == "/whoami":
            console.print(ctx)
        elif cmd == "/login":
            new = login(text.split()[1]) if len(text.split()) > 1 else None
            if new:
                ctx = new
                console.print(f"Signed in as [bold]{ctx.display_name}[/bold] ({ctx.channel}/{ctx.role}).")
        else:
            run_turn(agent, ctx, text)


if __name__ == "__main__":
    main()
