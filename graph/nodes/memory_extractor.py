"""Memory extractor node - LLM extracts user preferences/facts from conversation."""

import json
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import AgentState
from services.memory import user_fact_store

logger = logging.getLogger("memory-extractor")

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

_SYSTEM_PROMPT = """\
You are a memory extraction assistant. Analyze the following conversation and extract any user preferences, personal facts, or important information worth remembering for future conversations.

Examples of things to extract:
- Language preferences ("I prefer Chinese responses")
- Contact information ("I often email alice@example.com")
- Personal facts ("My name is ...", "I live in ...")
- Work context ("I work at ...", "My team uses ...")
- Preferences ("I like concise answers", "Always use formal tone")

Rules:
- Only extract NEW, meaningful facts - skip trivial or task-specific details.
- Return a JSON array of strings. Each string is one fact.
- If there is nothing worth remembering, return an empty array: []
- Keep each fact concise (one sentence).

Respond with ONLY the JSON array, no extra text.
"""


async def memory_extractor(state: AgentState) -> dict:
    """Extract user facts from the current conversation turn."""
    user_id = state.get("user_id", "")
    transcript = state.get("transcript", "")
    response_text = state.get("response_text", "")

    if not user_id or not transcript:
        return {}

    conversation = f"User: {transcript}\nAssistant: {response_text}"

    try:
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=conversation),
        ]

        response = await _llm.ainvoke(messages)
        text = response.content.strip()

        facts = json.loads(text)
        if isinstance(facts, list):
            for fact in facts:
                if isinstance(fact, str) and fact.strip():
                    user_fact_store.add_fact(user_id, fact.strip())

    except (json.JSONDecodeError, Exception) as e:
        logger.warning("Memory extraction failed: %s", e)

    return {}
