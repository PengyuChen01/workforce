"""Unified messaging channel interface.

All inbound messages (API, webhook, Telegram, etc.) go through the same
process_message() function, which runs the LangGraph and returns the result.
"""

import logging

from langchain_core.messages import HumanMessage, AIMessage

from services.memory import conversation_memory

logger = logging.getLogger("channel")


async def process_message(
    text: str,
    channel: str = "api",
    user_email: str = "",
    user_id: str = "",
) -> dict:
    """Process a text message through the LangGraph workflow.

    Args:
        text: User's message text.
        channel: Source channel identifier.
        user_email: The user's email address (if known).
        user_id: User identifier for conversation memory.

    Returns:
        dict with keys: transcript, selected_skill, response_text, error
    """
    from graph.orchestrator import workflow

    # Load conversation history for this user
    history_messages = []
    if user_id:
        history = conversation_memory.get_history(user_id)
        for msg in history:
            if msg["role"] == "user":
                history_messages.append(HumanMessage(content=msg["content"]))
            else:
                history_messages.append(AIMessage(content=msg["content"]))

    initial_state = {
        "messages": history_messages,
        "transcript": text,
        "selected_skill": "",
        "response_text": "",
        "user_email": user_email,
        "user_id": user_id,
        "channel": channel,
        "error": None,
    }

    result = await workflow.ainvoke(initial_state)

    # Save this turn to short-term memory
    response_text = result.get("response_text", "")
    if user_id:
        conversation_memory.add_message(user_id, "user", text)
        if response_text:
            conversation_memory.add_message(user_id, "assistant", response_text)

    return {
        "transcript": text,
        "selected_skill": result.get("selected_skill", ""),
        "response_text": response_text,
        "error": result.get("error"),
        "channel": channel,
    }
