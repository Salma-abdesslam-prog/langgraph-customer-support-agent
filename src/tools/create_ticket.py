from typing import Literal

from langchain_core.tools import tool

from src.db import TICKET_CATEGORIES, TICKET_PRIORITIES, store

# Derived from the same tuples db.py validates against, so the JSON Schema
# enum sent to the LLM can never drift out of sync with the fallback logic.
TicketCategory = Literal[TICKET_CATEGORIES]
TicketPriority = Literal[TICKET_PRIORITIES]


@tool
def create_ticket(
    customer_id: str,
    subject: str,
    description: str,
    order_id: str | None = None,
    category: TicketCategory = "other",
    priority: TicketPriority = "normal",
) -> dict:
    """Create a support ticket for a customer, optionally linked to an order.

    Use this when a problem needs human follow-up (damaged package, billing
    dispute, anything you cannot resolve yourself).

    description must summarize only what the customer actually said, in
    your own words. Do not invent specific physical details they didn't
    mention (e.g. "cracked casing", "dented box", "packaging torn") just
    to sound more descriptive. If they only said "damaged" or "broken"
    with no detail, write something like "Customer reports the item
    arrived damaged; no further detail provided" instead of guessing what
    kind of damage occurred.

    category must be one of:
    - "damaged_item": arrived physically damaged/broken (dented box,
      cracked casing, shattered parts).
    - "defective_item": arrived intact but doesn't work as intended
      (won't power on, malfunctions).
    - "missing_delivery": late, lost, or never-arrived shipment.
    - "wrong_item": customer received a different product than ordered.
    - "billing_dispute": duplicate charge, wrong amount, refund not
      reflected, any payment discrepancy.
    - "safety_hazard": immediate danger - fire, smoke, injury, chemical
      leak, electrical shock risk. Also set priority="urgent" in this case.
    - "other": anything that doesn't fit the categories above.

    priority must be one of "low", "normal", "urgent" - pick based on these
    examples, don't default to "normal" just because it feels safer:
    - "low": item still works/is usable, issue is purely cosmetic or
      minor - a scratched box, a small blemish, a slightly late delivery
      by a day. Example: "the box arrived a bit dented but the product
      inside is fine" -> low.
    - "normal": the item doesn't work as expected, or there's a genuine
      inconvenience, but nothing dangerous or high-stakes - defective
      item, wrong item shipped, week-late delivery, billing dispute.
      Example: "the keyboard doesn't turn on" -> normal.
    - "urgent": a safety hazard (fire, injury, chemical leak, electrical
      danger) or a high-value order (roughly $300+) with a serious
      problem. Example: "the battery is smoking" -> urgent.
    The ticket starts with status "open" and a history log; a human agent
    updates it from there.
    """
    ticket = store.create_ticket(customer_id, subject, description, order_id, category, priority)
    return {
        "ticket_id": ticket.id,
        "status": ticket.status,
        "category": ticket.category,
        "priority": ticket.priority,
        "customer_id": ticket.customer_id,
        "order_id": ticket.order_id,
        "created_at": ticket.created_at,
    }
