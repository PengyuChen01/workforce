"""Skill router node - LLM agentic search to pick the best skill."""

import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import AgentState
from skills.registry import get_skill_descriptions

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def _build_router_prompt() -> str:
    skill_list = get_skill_descriptions()
    return f"""\
You are a skill-routing assistant. Given the user's message, decide which skill
is the best match to handle it.

Available skills:
{skill_list}

Rules:
- Pick exactly ONE skill id that best matches the user's intent.
- If nothing fits well, use "general_chat".

Respond in STRICT JSON (no markdown, no extra text):
{{"skill": "<skill_id>"}}
"""


async def skill_router(state: AgentState) -> dict:
    """Use LLM to pick the best skill for the user's input."""
    transcript = state.get("transcript", "")

    if not transcript:
        return {
            "selected_skill": "general_chat",
            "error": "No input provided.",
        }

    messages = [
        SystemMessage(content=_build_router_prompt()),
        HumanMessage(content=transcript),
    ]

    response = await _llm.ainvoke(messages)
    text = response.content.strip()

    try:
        parsed = json.loads(text)
        skill_id = parsed.get("skill", "general_chat")
        return {
            "selected_skill": skill_id,
            "messages": [HumanMessage(content=transcript)],
        }
    except json.JSONDecodeError:
        return {
            "selected_skill": "general_chat",
            "error": f"Router parse error: {text}",
            "messages": [HumanMessage(content=transcript)],
        }
