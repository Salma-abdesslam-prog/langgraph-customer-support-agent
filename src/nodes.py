import json

from langchain_core.messages import SystemMessage, ToolMessage

from src.config import get_llm
from src.prompts import SYSTEM_PROMPT
from src.state import AgentState
from src.tools import ALL_TOOLS
from src.tools.refund_order import refund_order

from langgraph.types import interrupt


def agent_node(state: AgentState) -> dict:
    llm_with_tools = get_llm().bind_tools(ALL_TOOLS)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def human_review_node(state: AgentState) -> dict:
    """Pause the graph and wait for a human decision before executing a
    sensitive tool call (currently: refund_order).

    Only handles the first tool call of the last AI message - a
    simplification that assumes the model requests at most one sensitive
    action per turn, which holds for this use case.
    """
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]

    decision = interrupt(
        {
            "action": "approve_refund",
            "tool_call": tool_call,
        }
    )

    if decision.get("approved"):
        result = refund_order.invoke(tool_call["args"])
    else:
        result = {
            "status": "rejected",
            "reason": decision.get("reason", "not specified"),
        }

    tool_message = ToolMessage(
        content=json.dumps(result),
        tool_call_id=tool_call["id"],
        name=tool_call["name"],
    )
    return {"messages": [tool_message]}
