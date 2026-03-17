"""Synthesis node - generates a human-friendly response text."""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from graph.state import AgentState

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

SYSTEM_PROMPT = """\
You are a friendly voice assistant. Based on the context below, generate a concise
spoken response to the user. Keep it natural and conversational - this will be
converted to speech.

If there was an error, politely inform the user what went wrong.
If a task was completed successfully, confirm it clearly.
If the intent was unknown, ask the user to clarify.
"""


async def synthesis_node(state: AgentState) -> dict:
    """Generate a final spoken response based on the current state.

    Returns partial state update with response_text and an AIMessage.
    """
    intent = state.get("intent", "unknown")
    skill_result = state.get("skill_result", {})
    error = state.get("error")
    transcript = state.get("transcript", "")

    # Build context for the LLM
    context_parts = [f"User said: \"{transcript}\"", f"Detected intent: {intent}"]

    if error:
        context_parts.append(f"Error: {error}")
    elif skill_result:
        context_parts.append(f"Skill result: {skill_result}")

    context = "\n".join(context_parts)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    response = await _llm.ainvoke(messages)
    response_text = response.content.strip()

    return {
        "response_text": response_text,
        "messages": [AIMessage(content=response_text)],
    }
