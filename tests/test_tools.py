import pytest

from src.db import store
from src.tools.check_order import check_order
from src.tools.create_ticket import create_ticket
from src.tools.refund_order import refund_order


@pytest.fixture(autouse=True)
def reset_store():
    store.seed()
    yield


def test_check_order_found():
    result = check_order.invoke({"order_id": "4521"})
    assert result["status"] == "paid"
    assert result["amount"] == 89.99


def test_check_order_not_found():
    result = check_order.invoke({"order_id": "9999"})
    assert result["error"] == "order_not_found"


def test_refund_success():
    result = refund_order.invoke({"order_id": "4521", "amount": 89.99})
    assert result["status"] == "refunded"
    assert check_order.invoke({"order_id": "4521"})["status"] == "refunded"


def test_refund_already_refunded():
    result = refund_order.invoke({"order_id": "4530", "amount": 39.90})
    assert result["error"] == "already_refunded"


def test_refund_amount_exceeds_total():
    result = refund_order.invoke({"order_id": "4521", "amount": 500})
    assert result["error"] == "amount_exceeds_order_total"


def test_refund_order_not_found():
    result = refund_order.invoke({"order_id": "0000", "amount": 10})
    assert result["error"] == "order_not_found"


def test_create_ticket():
    result = create_ticket.invoke(
        {
            "customer_id": "cust_1",
            "subject": "Damaged package",
            "description": "Box arrived crushed",
            "order_id": "4521",
            "category": "damaged_item",
            "priority": "urgent",
        }
    )
    assert result["status"] == "open"
    assert result["category"] == "damaged_item"
    assert result["priority"] == "urgent"
    assert result["order_id"] == "4521"
    assert result["ticket_id"].startswith("T-")


def test_create_ticket_defaults():
    result = create_ticket.invoke(
        {"customer_id": "cust_1", "subject": "Question", "description": "General question"}
    )
    assert result["priority"] == "normal"
    assert result["category"] == "other"


def test_create_ticket_tool_rejects_invalid_priority():
    # category/priority are typing.Literal, so LangChain validates them
    # against the JSON Schema enum *before* the function body runs -
    # invalid values never reach create_ticket() through the tool interface.
    with pytest.raises(Exception):
        create_ticket.invoke(
            {
                "customer_id": "cust_1",
                "subject": "Question",
                "description": "General question",
                "priority": "not_a_real_priority",
            }
        )


def test_create_ticket_tool_rejects_invalid_category():
    with pytest.raises(Exception):
        create_ticket.invoke(
            {
                "customer_id": "cust_1",
                "subject": "Question",
                "description": "General question",
                "category": "not_a_real_category",
            }
        )


def test_store_create_ticket_invalid_priority_falls_back_to_normal():
    # Defense in depth: the store itself still validates and falls back,
    # in case it's ever called directly (bypassing the tool's schema).
    ticket = store.create_ticket("cust_1", "Q", "General question", priority="nonsense")
    assert ticket.priority == "normal"


def test_store_create_ticket_invalid_category_falls_back_to_other():
    ticket = store.create_ticket("cust_1", "Q", "General question", category="nonsense")
    assert ticket.category == "other"


def test_update_ticket_status_tracks_history():
    ticket = store.create_ticket("cust_1", "Question", "General question")
    result = store.update_ticket_status(ticket.id, "resolved")
    assert result["status"] == "resolved"
    assert ticket.status == "resolved"
    assert len(ticket.history) == 2
    assert "resolved" in ticket.history[-1].action


def test_update_ticket_status_not_found():
    result = store.update_ticket_status("T-9999", "resolved")
    assert result["error"] == "ticket_not_found"
