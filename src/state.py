from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """Conversation state. `messages` (list of BaseMessage) is inherited
    from MessagesState and accumulates via LangGraph's add_messages reducer.
    """
