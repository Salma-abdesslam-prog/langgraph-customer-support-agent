import uuid

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from src.graph import build_graph


def handle_interrupts(app, result, config):
    """After an app.invoke(), keep resuming through human-review pauses
    until the graph reaches a normal end state.
    """
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        tool_call = payload["tool_call"]
        print(f"\n[human review required] {tool_call['name']}({tool_call['args']})")
        answer = input("Approve? (y/n): ").strip().lower()
        resume = {"approved": answer == "y"}
        if answer != "y":
            resume["reason"] = input("Reason for rejecting: ").strip()
        result = app.invoke(Command(resume=resume), config=config)
    return result


def main():
    app = build_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    print("Support agent - type 'exit' to quit\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        result = app.invoke({"messages": [HumanMessage(content=user_input)]}, config=config)
        result = handle_interrupts(app, result, config)

        print(f"Agent: {result['messages'][-1].content}\n")


if __name__ == "__main__":
    main()
