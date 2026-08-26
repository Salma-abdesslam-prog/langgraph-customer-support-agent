from langchain_core.tools import tool

from src.db import store


@tool
def refund_order(order_id: str, amount: float) -> dict:
    """Refund an order for the given amount.

    This is a sensitive action with a real side effect (it changes the
    order's status) and requires human approval before it actually runs -
    the graph routes calls to this tool through a human-in-the-loop review
    node rather than executing them straight away.
    """
    return store.refund(order_id, amount)
