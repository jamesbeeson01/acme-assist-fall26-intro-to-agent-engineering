"""Smoke test: the orchestrator builds and answers using a scripted fake model (no API key or server needed).

Pattern from the LangChain docs: https://docs.langchain.com/oss/python/langchain/test/unit-testing
"""

import httpx
from langchain.messages import AIMessage, ToolCall
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from acme_assist import api, llm
from acme_assist.context import AcmeContext


class FakeToolCallingModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def fake_api() -> api.AcmeAPI:
    """An AcmeAPI whose every endpoint answers 200 with an empty list."""
    client = api.AcmeAPI(base_url="http://acme-api.test")
    client.http = httpx.Client(base_url="http://acme-api.test",
                               transport=httpx.MockTransport(lambda request: httpx.Response(200, json=[])))
    return client


def test_orchestrator_answers(tmp_path, monkeypatch):
    monkeypatch.setenv("ACME_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(api, "_client", fake_api())
    llm.MODEL_OVERRIDE = FakeToolCallingModel(messages=iter([
        AIMessage(content="", tool_calls=[ToolCall(name="search_policies", args={"query": "return window"}, id="1")]),
        AIMessage(content="You can return most items within 30 days."),
    ]))
    try:
        from acme_assist.orchestrator import build_acme_assist

        agent = build_acme_assist()
        result = agent.invoke(
            {"messages": [{"role": "user", "content": "What's the return policy?"}]},
            config={"configurable": {"thread_id": "smoke"}},
            context=AcmeContext(channel="customer", user_id="C-20001", display_name="Maria Okafor"),
        )
    finally:
        llm.MODEL_OVERRIDE = None

    assert result["messages"][-1].text
