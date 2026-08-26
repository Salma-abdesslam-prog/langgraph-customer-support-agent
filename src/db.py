"""In-memory fake e-commerce database (no HTTP layer, no persistence).

This exists only to give the agent's tools something real to read and
write. Keeping it in-process (a plain dict) is a deliberate choice: the
point of this project is the LangGraph orchestration, not a backend.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import count

TICKET_STATUSES = ("open", "in_progress", "resolved", "closed")
TICKET_PRIORITIES = ("low", "normal", "urgent")
TICKET_CATEGORIES = (
    "damaged_item",
    "defective_item",
    "missing_delivery",
    "wrong_item",
    "billing_dispute",
    "safety_hazard",
    "other",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Order:
    id: str
    customer_id: str
    product: str
    amount: float
    status: str = "paid"  # paid | refunded


@dataclass
class TicketEvent:
    timestamp: str
    action: str


@dataclass
class Ticket:
    id: str
    customer_id: str
    subject: str
    description: str
    order_id: str | None = None
    category: str = "other"  # see TICKET_CATEGORIES
    priority: str = "normal"  # low | normal | urgent
    status: str = "open"  # open | in_progress | resolved | closed
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    history: list[TicketEvent] = field(default_factory=list)


class FakeStore:
    """Tiny in-memory store standing in for a real e-commerce backend."""

    def __init__(self) -> None:
        self.orders: dict[str, Order] = {}
        self.tickets: dict[str, Ticket] = {}
        self._ticket_ids = count(1)

    def seed(self) -> None:
        self.orders = {
            "4521": Order(id="4521", customer_id="cust_1", product="Wireless Headphones", amount=89.99),
            "4522": Order(id="4522", customer_id="cust_1", product="Mechanical Keyboard", amount=129.00),
            "4530": Order(id="4530", customer_id="cust_2", product="Wireless Mouse", amount=39.90, status="refunded"),
        }
        self.tickets = {}
        self._ticket_ids = count(1)

    def get_order(self, order_id: str) -> Order | None:
        return self.orders.get(order_id)

    def refund(self, order_id: str, amount: float) -> dict:
        order = self.get_order(order_id)
        if order is None:
            return {"error": "order_not_found", "order_id": order_id}
        if order.status == "refunded":
            return {"error": "already_refunded", "order_id": order_id}
        if amount > order.amount:
            return {"error": "amount_exceeds_order_total", "order_amount": order.amount}
        order.status = "refunded"
        return {"status": "refunded", "order_id": order_id, "amount": amount}

    def create_ticket(
        self,
        customer_id: str,
        subject: str,
        description: str,
        order_id: str | None = None,
        category: str = "other",
        priority: str = "normal",
    ) -> Ticket:
        if priority not in TICKET_PRIORITIES:
            priority = "normal"
        if category not in TICKET_CATEGORIES:
            category = "other"
        ticket_id = f"T-{next(self._ticket_ids):04d}"
        now = _now_iso()
        ticket = Ticket(
            id=ticket_id,
            customer_id=customer_id,
            subject=subject,
            description=description,
            order_id=order_id,
            category=category,
            priority=priority,
            created_at=now,
            updated_at=now,
            history=[TicketEvent(timestamp=now, action="Ticket created")],
        )
        self.tickets[ticket_id] = ticket
        return ticket

    def update_ticket_status(self, ticket_id: str, status: str) -> dict:
        ticket = self.tickets.get(ticket_id)
        if ticket is None:
            return {"error": "ticket_not_found", "ticket_id": ticket_id}
        if status not in TICKET_STATUSES:
            return {"error": "invalid_status", "status": status}
        previous = ticket.status
        ticket.status = status
        ticket.updated_at = _now_iso()
        ticket.history.append(
            TicketEvent(timestamp=ticket.updated_at, action=f"Status changed: {previous} -> {status}")
        )
        return {"ticket_id": ticket.id, "status": ticket.status}


# Single process-wide instance, seeded on import.
store = FakeStore()
store.seed()
