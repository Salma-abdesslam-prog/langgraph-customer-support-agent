import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command

from src.db import TICKET_STATUSES, store
from src.graph import build_graph

st.set_page_config(page_title="Support Agent", page_icon="🎧", layout="centered")

USER_AVATAR = "🧑"
BOT_AVATAR = "🤖"

EXAMPLE_PROMPTS = [
    ("🔍 Check an order", "Can you check the status of order 4521?"),
    ("💸 Request a refund", "I'd like a refund for order 4522, I paid the full amount."),
    ("📦 Damaged package", "My order 4521 arrived damaged, please help."),
    ("❓ Unknown order", "What's the status of order 9999?"),
]


@st.cache_resource
def get_app():
    return build_graph()


def new_thread():
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.pending_interrupt = None
    st.session_state.queued_input = None
    store.seed()


app = get_app()

if "thread_id" not in st.session_state:
    new_thread()
if "queued_input" not in st.session_state:
    st.session_state.queued_input = None

config = {"configurable": {"thread_id": st.session_state.thread_id}}


def process_result(result):
    st.session_state.pending_interrupt = (
        result["__interrupt__"][0].value if "__interrupt__" in result else None
    )
    st.rerun()


def send_message(content: str):
    with st.chat_message("user", avatar=USER_AVATAR):
        st.write(content)
    with st.spinner("Thinking..."):
        result = app.invoke({"messages": [HumanMessage(content=content)]}, config=config)
    process_result(result)


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.subheader("🎧 Support Agent")
    st.caption("LangGraph + Groq (GPT-OSS-20B) — agentic tool calling with human-in-the-loop refund approval")

    if st.button("🔄 New conversation", use_container_width=True):
        new_thread()
        st.rerun()

    st.divider()

    st.markdown("**💡 What the agent can do**")
    st.markdown(
        "- 🔍 Check the status of an order\n"
        "- 💸 Refund an order *(requires human approval)*\n"
        "- 🎫 Create a support ticket"
    )

    st.divider()

    st.markdown("**📦 Demo orders**")
    orders_table = [
        {
            "ID": o.id,
            "Product": o.product,
            "Amount": f"${o.amount:.2f}",
            "Status": "✅ paid" if o.status == "paid" else "↩️ refunded",
        }
        for o in store.orders.values()
    ]
    st.dataframe(orders_table, hide_index=True, use_container_width=True)
    order_ids = sorted(store.orders.keys())
    st.caption(
        f"Only {', '.join(order_ids)} are available — "
        "try 9999 to see how the agent handles a missing order."
    )

    st.divider()

    st.markdown("**🎫 Support tickets**")
    if not store.tickets:
        st.caption("No tickets yet — created automatically when the agent needs human follow-up.")
    else:
        priority_icon = {"low": "🟢", "normal": "🟡", "urgent": "🔴"}
        category_label = {
            "damaged_item": "📦 Damaged item",
            "defective_item": "⚙️ Defective item",
            "missing_delivery": "🚚 Missing delivery",
            "wrong_item": "🔀 Wrong item",
            "billing_dispute": "💳 Billing dispute",
            "safety_hazard": "🔥 Safety hazard",
            "other": "❔ Other",
        }
        for ticket in store.tickets.values():
            with st.expander(f"{ticket.id} — {ticket.subject} ({ticket.status})"):
                st.caption(category_label.get(ticket.category, "❔ Other"))
                st.caption(f"{priority_icon.get(ticket.priority, '🟡')} Priority: {ticket.priority}")
                st.write(ticket.description)
                st.caption(f"Order: {ticket.order_id or '—'} | Customer: {ticket.customer_id}")
                st.caption(f"Created: {ticket.created_at.split('.')[0]}")
                st.caption(f"Updated: {ticket.updated_at.split('.')[0]}")

                st.markdown("**History**")
                for event in ticket.history:
                    st.caption(f"- {event.timestamp.split('.')[0]}: {event.action}")

                st.markdown("**Update status** *(simulates a human agent)*")
                new_status = st.selectbox(
                    "Status",
                    TICKET_STATUSES,
                    index=TICKET_STATUSES.index(ticket.status),
                    key=f"status_{ticket.id}",
                    label_visibility="collapsed",
                )
                if new_status != ticket.status and st.button("Apply", key=f"apply_{ticket.id}"):
                    store.update_ticket_status(ticket.id, new_status)
                    st.rerun()

    st.divider()

    st.markdown("**✨ Examples to try**")
    for label, prompt in EXAMPLE_PROMPTS:
        if st.button(label, use_container_width=True, key=f"ex_{label}"):
            st.session_state.queued_input = prompt
            st.rerun()

# ---------------------------------------------------------------- main
st.title("🎧 Support Agent")
st.caption(
    "Chat with the agent like a customer: ask about an order's status, "
    "request a refund, or report a problem. Refunds go through a human "
    "approval step before they're executed."
)


def render_history():
    state = app.get_state(config)
    messages = state.values.get("messages", []) if state.values else []
    for m in messages:
        if isinstance(m, HumanMessage):
            with st.chat_message("user", avatar=USER_AVATAR):
                st.write(m.content)
        elif isinstance(m, AIMessage):
            for tc in m.tool_calls or []:
                with st.chat_message("assistant", avatar=BOT_AVATAR):
                    st.caption(f"🔧 Calling `{tc['name']}({tc['args']})`")
            if m.content:
                with st.chat_message("assistant", avatar=BOT_AVATAR):
                    st.write(m.content)
        elif isinstance(m, ToolMessage):
            with st.chat_message("assistant", avatar=BOT_AVATAR):
                st.caption(f"📋 Result from `{m.name}`: {m.content}")


render_history()

if st.session_state.pending_interrupt:
    tc = st.session_state.pending_interrupt["tool_call"]
    st.warning(f"⚠️ Human approval required: **{tc['name']}**({tc['args']})")
    col1, col2 = st.columns(2)
    if col1.button("✅ Approve", use_container_width=True, type="primary"):
        with st.spinner("Processing..."):
            result = app.invoke(Command(resume={"approved": True}), config=config)
        process_result(result)
    if col2.button("❌ Reject", use_container_width=True):
        with st.spinner("Processing..."):
            result = app.invoke(
                Command(resume={"approved": False, "reason": "rejected via UI"}), config=config
            )
        process_result(result)
else:
    if st.session_state.queued_input:
        queued = st.session_state.queued_input
        st.session_state.queued_input = None
        send_message(queued)

    user_input = st.chat_input("Type your message...")
    if user_input:
        send_message(user_input)
