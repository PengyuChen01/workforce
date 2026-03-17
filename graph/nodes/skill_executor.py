"""Skill executor node - LLM extracts args, then calls A2A agent if needed."""

import os
import json
import uuid
import logging

import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from graph.state import AgentState
from skills.registry import get_skill

logger = logging.getLogger("skill-executor")

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)


async def _call_a2a_agent(agent_url: str, payload_text: str) -> dict:
    """Call an A2A agent via HTTP JSON-RPC.

    Args:
        agent_url: Base URL of the A2A agent (e.g. http://localhost:8001)
        payload_text: The structured text/JSON to send as message content.

    Returns:
        dict with "status" and "text" from the agent response.
    """
    a2a_request = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "params": {
            "id": f"task-{uuid.uuid4().hex[:8]}",
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": payload_text}],
            },
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{agent_url}/a2a", json=a2a_request)
            resp.raise_for_status()
            data = resp.json()

        result = data.get("result", {})
        status = result.get("status", "unknown")
        artifacts = result.get("artifacts", [])
        text = artifacts[0]["text"] if artifacts else "No response from agent."

        logger.info("A2A call | url=%s | status=%s", agent_url, status)
        return {"status": status, "text": text}

    except httpx.ConnectError:
        msg = f"Cannot connect to agent at {agent_url}. Is it running?"
        logger.error(msg)
        return {"status": "failed", "text": msg}
    except Exception as e:
        logger.error("A2A call error: %s", e)
        return {"status": "failed", "text": str(e)}


async def skill_executor(state: AgentState) -> dict:
    """Execute the selected skill.

    Flow:
    1. LLM extracts structured args using skill's system_prompt
    2. If skill has an A2A agent -> call it via HTTP with the extracted args
    3. If no agent -> return LLM output directly
    """
    skill_id = state.get("selected_skill", "general_chat")
    transcript = state.get("transcript", "")

    skill = get_skill(skill_id)
    if skill is None:
        skill = get_skill("general_chat")

    # Build system prompt with user context
    system_prompt = skill.system_prompt
    if skill.id == "send_email":
        user_email = state.get("user_email", "") or os.getenv("DEFAULT_USER_EMAIL", "")
        if user_email:
            system_prompt += f"\n\nUser context: The user's own email address is {user_email}"

    # Step 1: LLM extracts structured args
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=transcript),
    ]

    response = await _llm.ainvoke(messages)
    llm_output = response.content.strip()

    # Step 2: If skill has an A2A agent, call it
    if skill.has_action and skill.agent_url:
        agent_result = await _call_a2a_agent(skill.agent_url, llm_output)

        if agent_result["status"] == "completed":
            response_text = agent_result["text"]
            error = None
        else:
            response_text = f"Agent error: {agent_result['text']}"
            error = agent_result["text"]

        return {
            "response_text": response_text,
            "error": error,
            "messages": [AIMessage(content=response_text)],
        }

    # Step 3: No agent, return LLM output directly
    return {
        "response_text": llm_output,
        "messages": [AIMessage(content=llm_output)],
    }
