"""Lightweight eval harness: replays each scenario in scenarios.jsonl
through the real graph (real Groq calls), auto-resolves any refund
approval per the scenario's `auto_approve` flag, and checks that the
tools the model actually called match `expected_tools`.

Not a substitute for LangSmith tracing - this is a fast pass/fail signal
you can run in CI or before a demo; use LangSmith to inspect *why* a
scenario failed.
"""
import json
import uuid
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command

from src.db import store
from src.graph import build_graph

SCENARIOS_PATH = Path(__file__).parent / "scenarios.jsonl"


def called_tool_names(messages) -> list[str]:
    names = []
    for m in messages:
        if isinstance(m, AIMessage):
            names.extend(tc["name"] for tc in (m.tool_calls or []))
        elif isinstance(m, ToolMessage) and m.name == "refund_order":
            # refund_order goes through human_review, not the AIMessage
            # tool_calls list of a ToolNode-executed call, but it *was*
            # requested by the model - already captured via the AIMessage
            # above, so nothing to add here. Kept for clarity.
            pass
    return names


def run_scenario(app, scenario: dict) -> bool:
    store.seed()  # reset fake data before every scenario
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    result = app.invoke({"messages": [HumanMessage(content=scenario["input"])]}, config=config)

    while "__interrupt__" in result:
        result = app.invoke(
            Command(resume={"approved": scenario["auto_approve"], "reason": "eval"}),
            config=config,
        )

    called = called_tool_names(result["messages"])
    expected = scenario["expected_tools"]
    ok = all(t in called for t in expected)
    print(f"{'PASS' if ok else 'FAIL'}  {scenario['name']:<28} expected={expected} called={called}")
    return ok


def main():
    app = build_graph()
    scenarios = [json.loads(line) for line in SCENARIOS_PATH.read_text().splitlines() if line.strip()]

    results = [run_scenario(app, s) for s in scenarios]
    passed = sum(results)
    print(f"\n{passed}/{len(results)} scenarios passed")


if __name__ == "__main__":
    main()
