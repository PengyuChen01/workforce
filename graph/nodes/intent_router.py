"""Intent router node - uses LLM to detect intent and extract skill args."""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import AgentState

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

SYSTEM_PROMPT = """\
You are an intent-detection assistant. Given the user's message, determine the intent
and extract structured arguments.

Supported intents:
1. "send_email" - User wants to send an email.
   Extract: {"to": "<email>", "subject": "<subject>", "body": "<body>"}
   If any field is missing, set it to an empty string "".

2. "unknown" - Anything else.

Respond in STRICT JSON format (no markdown, no extra text):
{
  "intent": "<intent>",
  "skill_args": { ... }
}
"""


async def intent_router(state: AgentState) -> dict:
    """Detect intent from the transcript and extract structured args.

    Returns partial state update with intent and skill_args.
    """
    transcript = state.get("transcript", "")

    if not transcript:
        return {
            "intent": "unknown",
            "skill_args": {},
            "error": "No transcript provided.",
        }

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=transcript),
    ]

    response = await _llm.ainvoke(messages)
    text = response.content.strip()

    # Parse the JSON response
    import json

    try:
        parsed = json.loads(text)
        return {
            "intent": parsed.get("intent", "unknown"),
            "skill_args": parsed.get("skill_args", {}),
            "messages": [HumanMessage(content=transcript)],
        }
    except json.JSONDecodeError:
        return {
            "intent": "unknown",
            "skill_args": {},
            "error": f"Failed to parse LLM response: {text}",
        }
