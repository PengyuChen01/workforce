"""Skill registry - each skill is a system prompt + optional A2A agent.

To add a new skill:
1. Append a Skill to SKILLS list
2. If it has a backing A2A agent, set agent_url to point to it
3. The orchestrator will auto-discover and route to it
"""

from dataclasses import dataclass


@dataclass
class Skill:
    id: str
    name: str
    description: str       # Used by router LLM to decide which skill to pick
    system_prompt: str      # LLM prompt to extract structured args
    agent_url: str = ""     # A2A agent URL (if backed by an agent)
    has_action: bool = False  # Whether this skill calls an A2A agent


# ---------- Skill definitions ----------

SKILLS: list[Skill] = [
    Skill(
        id="send_email",
        name="Send Email",
        description="User wants to compose or send an email. Extracts recipient, subject, and body.",
        has_action=True,
        agent_url="http://localhost:8001",
        system_prompt="""\
You are an email assistant. The user wants to send an email.
Extract the following fields from the user's request:
- to: recipient email address
- subject: email subject
- body: email body content

Rules:
- If the user says "my email" / "my mailbox" / "给我的邮箱" or similar, use the
  default user email provided in the context below.
- If subject is not specified, infer a short one from the body.
- If body is not specified, use a reasonable default based on context.

You MUST respond in STRICT JSON format only (no markdown, no extra text):
{{"to": "<email>", "subject": "<subject>", "body": "<body>"}}
""",
    ),
    Skill(
        id="weather",
        name="Weather",
        description="User wants to know the weather, temperature, or forecast for a city or location.",
        has_action=True,
        agent_url="http://localhost:8002",
        system_prompt="""\
You are a weather assistant. The user wants to know the weather for a location.
Extract the city/location from the user's request.

If the user says a city in Chinese (e.g. 哥伦布, 纽约, 上海), translate it to English.
If no city is mentioned, default to "Columbus, OH".

You MUST respond in STRICT JSON format only (no markdown, no extra text):
{{"city": "<city name in English>", "units": "imperial"}}

Use "imperial" for US cities, "metric" for others.
""",
    ),
    Skill(
        id="translate",
        name="Translate",
        description="User wants to translate text between languages. E.g. translate to English, 翻译成中文, translate this sentence.",
        has_action=True,
        agent_url="http://localhost:8003",
        system_prompt="""\
You are a translation assistant. The user wants to translate text.
Extract the following from the user's request:
- text: the text to translate
- target_lang: the target language code (EN, ZH, JA, KO, FR, DE, ES, PT, IT, RU, etc.)
- source_lang: (optional) source language code, omit if unsure

Language mapping:
- English / 英文 / 英语 -> EN
- Chinese / 中文 / 中文 -> ZH
- Japanese / 日文 / 日语 -> JA
- Korean / 韩文 / 韩语 -> KO
- French / 法文 / 法语 -> FR
- German / 德文 / 德语 -> DE
- Spanish / 西班牙语 -> ES

If no target language is specified, translate to English if the text is non-English,
or translate to Chinese if the text is in English.

You MUST respond in STRICT JSON format only (no markdown, no extra text):
{{"text": "<text to translate>", "target_lang": "<lang code>", "source_lang": "<lang code or empty>"}}
""",
    ),
    Skill(
        id="schedule_meeting",
        name="Schedule Meeting",
        description="User wants to schedule, book, or arrange a meeting or appointment.",
        system_prompt="""\
You are a meeting scheduling assistant. The user wants to schedule a meeting.
Extract the following from the user's request:
- Participants (who should attend)
- Date and time
- Duration (default 30 minutes if not specified)
- Topic / agenda

Respond with a clear confirmation of the meeting details:
---
MEETING: <topic>
PARTICIPANTS: <list>
DATE/TIME: <date and time>
DURATION: <duration>
---
STATUS: Meeting scheduled successfully. (In production this would create a calendar event.)
""",
    ),
    Skill(
        id="search_info",
        name="Search Information",
        description="User wants to look up information, ask a question, or search for something. NOT weather-related.",
        system_prompt="""\
You are a knowledgeable research assistant. The user is asking a question or looking for information.
Provide a clear, concise, and accurate answer based on your knowledge.
If you're not sure about something, say so honestly.
Keep the response conversational - it will be spoken aloud via TTS.
""",
    ),
    Skill(
        id="general_chat",
        name="General Chat",
        description="General conversation, greetings, small talk, or anything that doesn't fit other skills.",
        system_prompt="""\
You are a friendly voice assistant. Have a natural, warm conversation with the user.
Keep responses concise and conversational - they will be spoken aloud.
Be helpful and engaging.
""",
    ),
]


def get_skill(skill_id: str) -> Skill | None:
    for skill in SKILLS:
        if skill.id == skill_id:
            return skill
    return None


def get_skill_descriptions() -> str:
    lines = []
    for s in SKILLS:
        a2a = " [A2A agent]" if s.agent_url else ""
        lines.append(f'- id="{s.id}" | name="{s.name}" | {s.description}{a2a}')
    return "\n".join(lines)


def list_skills() -> list[dict]:
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "has_agent": bool(s.agent_url),
            "agent_url": s.agent_url or None,
        }
        for s in SKILLS
    ]
