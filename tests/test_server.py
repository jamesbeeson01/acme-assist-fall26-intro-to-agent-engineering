"""The HTTP server the class dashboard talks to, with a scripted fake model."""

import os

import pytest

from fastapi.testclient import TestClient
from langchain.messages import AIMessage
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.outputs import ChatGeneration, ChatResult

from acme_assist import api, llm
from tests.test_smoke import fake_api


class ScriptedModel(GenericFakeChatModel):
    """Answers with `script` in order. A list, not an iterator: building the agent can read the
    model's fields, which would drain an iterator before the first turn."""

    script: list = []
    calls: int = 0

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        reply = self.script[self.calls]
        self.calls += 1
        return ChatResult(generations=[ChatGeneration(message=reply)])


def client(monkeypatch, tmp_path, replies, keep_db=False):
    monkeypatch.setenv("ACME_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("CLASS_SPACE_TOKEN", "secret")
    if not keep_db:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.setattr(api, "_client", fake_api())
    monkeypatch.setattr(llm, "MODEL_OVERRIDE", ScriptedModel(messages=iter([]), script=replies))
    from acme_assist.server import app

    c = TestClient(app, headers={"authorization": "Bearer secret"})
    return c


def test_conversations_belong_to_their_student(monkeypatch, tmp_path):
    replies = [AIMessage(content="Hi Maria!"), AIMessage(content="Still here.")]
    with client(monkeypatch, tmp_path, replies) as c:
        first = c.post("/chat", json={"student": "s1", "persona": "C-20001", "text": "hello"}).json()
        assert first["reply"] == "Hi Maria!"
        thread_id = first["thread"]["id"]
        assert first["thread"]["title"] == "hello"

        again = c.post("/chat", json={"student": "s1", "thread_id": thread_id, "text": "you there?"}).json()
        assert again["reply"] == "Still here."

        assert [t["id"] for t in c.get("/threads", params={"student": "s1"}).json()] == [thread_id]
        assert c.get("/threads", params={"student": "s2"}).json() == []

        convo = c.get(f"/threads/{thread_id}", params={"student": "s1"}).json()
        assert [m["text"] for m in convo["messages"]] == ["hello", "Hi Maria!", "you there?", "Still here."]
        assert c.get(f"/threads/{thread_id}", params={"student": "s2"}).status_code == 404
        assert c.post("/chat", json={"student": "s2", "thread_id": thread_id, "text": "x"}).status_code == 404


def test_requests_need_the_token_and_a_persona(monkeypatch, tmp_path):
    with client(monkeypatch, tmp_path, []) as c:
        assert c.get("/threads", params={"student": "s1"}, headers={"authorization": "Bearer nope"}).status_code == 401
        assert c.post("/chat", json={"student": "s1", "text": "hi"}).status_code == 400
        assert c.post("/chat", json={"student": "s1", "persona": "C-nobody", "text": "hi"}).status_code == 400
        assert c.get("/health").json()["status"] == "ok"
        assert len(c.get("/personas").json()) > 0


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="set TEST_DATABASE_URL to a throwaway Postgres")
def test_conversations_survive_a_restart(monkeypatch, tmp_path):
    """A push redeploys the agent; with Postgres, students' conversations are still there afterwards."""
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    replies = [AIMessage(content="Saved reply.")]
    with client(monkeypatch, tmp_path, replies, keep_db=True) as c:
        thread_id = c.post("/chat", json={"student": "s-restart", "persona": "C-20001", "text": "remember me"}).json()["thread"]["id"]
    with client(monkeypatch, tmp_path, [], keep_db=True) as c:  # a fresh process: new agent, same database
        assert thread_id in [t["id"] for t in c.get("/threads", params={"student": "s-restart"}).json()]
        convo = c.get(f"/threads/{thread_id}", params={"student": "s-restart"}).json()
        assert [m["text"] for m in convo["messages"]] == ["remember me", "Saved reply."]
