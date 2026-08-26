from langchain_core.tools import tool

from src.db import store


@tool
def check_order(order_id: str) -> dict:
    """Look up an order by its id and return its product, amount and status.

    Use this before offering a refund or creating a ticket, to confirm the
    order actually exists and to see its current status.
    """
    order = store.get_order(order_id)
    if order is None:
        return {"error": "order_not_found", "order_id": order_id}
    return {
        "order_id": order.id,
        "customer_id": order.customer_id,
        "product": order.product,
        "amount": order.amount,
        "status": order.status,
    }
