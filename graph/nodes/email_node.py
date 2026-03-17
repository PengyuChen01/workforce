"""Email node - calls the A2A Email Agent via HTTP."""

import os
import httpx

from graph.state import AgentState

# A2A Email Agent base URL
EMAIL_AGENT_URL = os.getenv("EMAIL_AGENT_URL", "http://localhost:8001")


async def email_node(state: AgentState) -> dict:
    """Call the A2A Email Agent to send an email.

    Sends a POST to the email agent's /a2a endpoint with the skill_args,
    and stores the result in skill_result.
    """
    skill_args = state.get("skill_args", {})

    if not skill_args:
        return {
            "skill_result": {"success": False, "detail": "No skill args provided."},
            "error": "No skill args to forward to email agent.",
        }

    # A2A request payload following a simple JSON-RPC style
    a2a_payload = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "params": {
            "id": "task-001",
            "message": {
                "role": "user",
                "parts": [
                    {
                        "type": "text",
                        "text": (
                            f"Send an email to {skill_args.get('to', '')} "
                            f"with subject \"{skill_args.get('subject', '')}\" "
                            f"and body \"{skill_args.get('body', '')}\""
                        ),
                    }
                ],
            },
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{EMAIL_AGENT_URL}/a2a",
                json=a2a_payload,
            )
            resp.raise_for_status()
            result = resp.json()

            return {
                "skill_result": result,
            }

    except httpx.HTTPStatusError as e:
        return {
            "skill_result": {"success": False, "detail": str(e)},
            "error": f"Email agent returned error: {e.response.status_code}",
        }
    except httpx.ConnectError:
        return {
            "skill_result": {"success": False, "detail": "Cannot connect to email agent."},
            "error": f"Cannot connect to email agent at {EMAIL_AGENT_URL}. Is it running?",
        }
    except Exception as e:
        return {
            "skill_result": {"success": False, "detail": str(e)},
            "error": f"Unexpected error calling email agent: {e}",
        }
