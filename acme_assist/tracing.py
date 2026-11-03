"""Langfuse tracing. On when LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set (plus LANGFUSE_BASE_URL)."""

import os


def enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def callbacks() -> list:
    """LangChain callbacks that send a run to Langfuse, or [] when tracing is off.

    Specialists invoked inside a tool inherit the callback, so one chat turn is one trace.
    """
    if not enabled():
        return []
    from langfuse.langchain import CallbackHandler

    return [CallbackHandler()]


def trace_metadata(user_id: str, session_id: str, tags: list[str] | None = None) -> dict:
    """Run metadata Langfuse reads: who (user), which conversation (session), and tags to filter by."""
    return {"langfuse_user_id": user_id, "langfuse_session_id": session_id, "langfuse_tags": tags or []}
