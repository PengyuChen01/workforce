"""Unified messaging channel interface.

All inbound messages (API, webhook, Telegram, etc.) go through the same
process_message() function, which runs the LangGraph and returns the result.
"""

import logging

logger = logging.getLogger("channel")


async def process_message(
    text: str,
    channel: str = "api",
    user_email: str = "",
) -> dict:
    """Process a text message through the LangGraph workflow.

    Args:
        text: User's message text.
        channel: Source channel identifier.
        user_email: The user's email address (if known).

    Returns:
        dict with keys: transcript, selected_skill, response_text, error
    """
    from graph.orchestrator import workflow

    initial_state = {
        "messages": [],
        "transcript": text,
        "selected_skill": "",
        "response_text": "",
        "user_email": user_email,
        "channel": channel,
        "error": None,
    }

    result = await workflow.ainvoke(initial_state)

    return {
        "transcript": text,
        "selected_skill": result.get("selected_skill", ""),
        "response_text": result.get("response_text", ""),
        "error": result.get("error"),
        "channel": channel,
    }
