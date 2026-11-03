"""ACME Assist over HTTP, for the class chat in the course dashboard.

    uv run uvicorn acme_assist.server:app --port 8000

The dashboard signs students in and sends a de-identified student id with every request. This server
owns the conversations: the LangGraph checkpointer keeps the messages, `threads` keeps who owns which.

Environment:
    CLASS_SPACE_TOKEN   shared secret the dashboard sends as `Authorization: Bearer ...` (unset: no auth, local only)
    DATABASE_URL        Postgres for conversations (unset: in memory, lost on restart)
    LANGFUSE_*          tracing, see tracing.py
"""

import json
import logging
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from langchain.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from acme_assist import tracing
from acme_assist.api import get_api
from acme_assist.context import AcmeContext
from acme_assist.orchestrator import build_acme_assist
from acme_assist.threads import MemoryThreads, PostgresThreads

PERSONAS = json.loads((Path(__file__).resolve().parent.parent / "data" / "personas.json").read_text(encoding="utf-8"))
STATE: dict = {}
log = logging.getLogger("acme.server")


def ensure_database(url: str) -> None:
    """Create DATABASE_URL's database if it doesn't exist yet. The class shares a Postgres server with
    Langfuse, and ACME Assist keeps its conversations in a database of its own on it."""
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    params = conninfo_to_dict(url)
    name = params.get("dbname")
    if not name or name == "postgres":
        return
    with psycopg.connect(make_conninfo(url, dbname="postgres"), autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    url = os.getenv("DATABASE_URL")
    if url:
        ensure_database(url)
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        pool = ConnectionPool(url, max_size=10, kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row})
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()
        tuple_pool = ConnectionPool(url, max_size=5, kwargs={"autocommit": True})
        STATE.update(agent=build_acme_assist(checkpointer), threads=PostgresThreads(tuple_pool), pools=[pool, tuple_pool])
    else:
        STATE.update(agent=build_acme_assist(), threads=MemoryThreads(), pools=[])
    yield
    for pool in STATE.get("pools", []):
        pool.close()


app = FastAPI(title="ACME Assist (class snapshot)", lifespan=lifespan)


def authorized(authorization: str = Header(default="")):
    token = os.getenv("CLASS_SPACE_TOKEN")
    if token and not secrets.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(401, "bad token")


def persona_context(persona_id: str) -> AcmeContext:
    """Who the student is playing in this conversation, looked up like the CLI's /login."""
    p = next((p for p in PERSONAS if p["id"] == persona_id), None)
    if p is None:
        raise HTTPException(400, f"unknown persona {persona_id}")
    api = get_api()
    if p["channel"] == "employee":
        e = api.get(f"/employees/{p['id']}") or {}
        return AcmeContext("employee", p["id"], e.get("role", p["role"]), p["name"], e.get("location_id"))
    return AcmeContext("customer", p["id"], "customer", p["name"])


def owned_thread(thread_id: str, student: str):
    t = STATE["threads"].get(thread_id)
    if t is None or t.student != student:
        raise HTTPException(404, "no such conversation")
    return t


def transcript(thread_id: str) -> list[dict]:
    """The conversation as the student saw it: their messages, final answers, and which tools ran."""
    state = STATE["agent"].get_state({"configurable": {"thread_id": thread_id}})
    out, tools = [], []
    for m in state.values.get("messages", []) if state else []:
        if isinstance(m, HumanMessage):
            out.append({"role": "user", "text": m.text})
            tools = []
        elif isinstance(m, AIMessage) and m.tool_calls:
            tools += [tc["name"] for tc in m.tool_calls]
        elif isinstance(m, AIMessage):
            out.append({"role": "assistant", "text": m.text, "tools": tools})
            tools = []
    return out


class ChatIn(BaseModel):
    student: str
    text: str
    thread_id: str | None = None
    persona: str | None = None  # required to start a new conversation


@app.get("/health")
def health():
    return {"status": "ok", "tracing": tracing.enabled(), "storage": "postgres" if os.getenv("DATABASE_URL") else "memory"}


@app.get("/personas", dependencies=[Depends(authorized)])
def personas():
    return PERSONAS


@app.get("/threads", dependencies=[Depends(authorized)])
def threads(student: str):
    return [t.to_dict() for t in STATE["threads"].of(student)]


@app.get("/threads/{thread_id}", dependencies=[Depends(authorized)])
def thread(thread_id: str, student: str):
    t = owned_thread(thread_id, student)
    return {**t.to_dict(), "messages": transcript(t.id)}


@app.post("/chat", dependencies=[Depends(authorized)])
def chat(body: ChatIn):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "text is required")
    if body.thread_id:
        t = owned_thread(body.thread_id, body.student)
        thread_id, persona = t.id, t.persona
    elif body.persona:
        thread_id, persona = str(uuid.uuid4()), body.persona
    else:
        raise HTTPException(400, "thread_id or persona is required")
    context = persona_context(persona)

    try:
        result = STATE["agent"].invoke(
            {"messages": [{"role": "user", "content": text}]},
            config={
                "configurable": {"thread_id": thread_id},
                "callbacks": tracing.callbacks(),
                "metadata": tracing.trace_metadata(body.student, thread_id, ["class-chat", persona]),
                "run_name": "ACME Assist",
            },
            context=context,
        )
    except Exception as e:  # the student sees what broke; the full traceback is in the logs and the trace
        log.exception("chat turn failed")
        raise HTTPException(502, f"ACME Assist failed: {type(e).__name__}: {str(e)[:300]}") from e

    # A conversation is listed once its first turn worked, so failed starts don't leave empty ones behind.
    threads = STATE["threads"]
    if body.thread_id:
        threads.touch(thread_id)
    else:
        threads.create(body.student, persona, text[:60], thread_id)
    return {"thread": threads.get(thread_id).to_dict(), "reply": result["messages"][-1].text}
