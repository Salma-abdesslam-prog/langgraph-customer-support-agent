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

    Use when a problem needs human follow-up (damaged item, billing dispute,
    anything you can't resolve yourself).

    description: summarize only what the customer said, in your own words.
    Don't invent physical details they didn't mention (e.g. "cracked
    casing") to sound more descriptive. If they gave no detail, write
    "Customer reports the item arrived damaged; no further detail
    provided" rather than guessing.

    category: damaged_item (physically broken/dented), defective_item
    (intact but doesn't work), missing_delivery (late/lost shipment),
    wrong_item (received a different product), billing_dispute
    (charge/payment issue), safety_hazard (fire/injury/shock risk - also
    set priority="urgent"), other (none of the above).

    priority: don't default to "normal" just because it feels safer.
    - low: cosmetic only, item still works (e.g. scratched box, a
      1-day-late delivery).
    - normal: genuine inconvenience, nothing dangerous (e.g. item doesn't
      turn on, week-late delivery).
    - urgent: safety hazard, or a high-value order ($300+) with a serious
      problem.

    Ticket starts as status "open" with a history log.
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
