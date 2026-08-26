from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.nodes import agent_node, human_review_node
from src.state import AgentState
from src.tools import AUTO_TOOLS, SENSITIVE_TOOLS

_SENSITIVE_NAMES = {t.name for t in SENSITIVE_TOOLS}


def route_after_agent(state: AgentState) -> Literal["tools", "human_review", "__end__"]:
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None)
    if not tool_calls:
        return "__end__"
    if tool_calls[0]["name"] in _SENSITIVE_NAMES:
        return "human_review"
    return "tools"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(AUTO_TOOLS))
    graph.add_node("human_review", human_review_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", "human_review": "human_review", "__end__": END},
    )
    graph.add_edge("tools", "agent")
    graph.add_edge("human_review", "agent")

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
