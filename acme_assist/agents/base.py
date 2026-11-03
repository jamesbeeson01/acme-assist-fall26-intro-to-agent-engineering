"""Helpers for building specialist agents and exposing them to the orchestrator as tools."""

from langchain.agents import create_agent
from langchain.tools import tool

from acme_assist.llm import get_model


def build_specialist(agent_name: str, tools: list, prompt: str):
    return create_agent(get_model(agent_name), tools=tools, system_prompt=prompt)


def as_tool(tool_name: str, description: str, agent):
    """Wrap a specialist so the orchestrator can call it like any other tool."""

    @tool(tool_name, description=description)
    def call_specialist(request: str) -> str:
        result = agent.invoke({"messages": [{"role": "user", "content": request}]})
        return str(result["messages"][-1].content)

    return call_specialist
