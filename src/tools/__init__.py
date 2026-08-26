from src.tools.check_order import check_order
from src.tools.create_ticket import create_ticket
from src.tools.refund_order import refund_order

# Tools the LLM can call directly, without human approval.
AUTO_TOOLS = [check_order, create_ticket]

# Tools that require human-in-the-loop approval before executing.
SENSITIVE_TOOLS = [refund_order]

ALL_TOOLS = AUTO_TOOLS + SENSITIVE_TOOLS
