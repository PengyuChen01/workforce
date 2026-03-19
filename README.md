# Voice Agent MVP

**Stack:** Whisper STT → LangGraph Orchestrator → A2A Skill Agents → ElevenLabs TTS

A voice-enabled AI agent system that routes user requests to specialized skills via LLM-based intent detection, supporting voice, text, Telegram, and webhook inputs.

## Architecture

```
User Voice/Text/Telegram/Webhook
              |
              v
     FastAPI (main.py :8000)
              |
              v
     Whisper STT (services/stt.py)       <- audio only
              |
              v
     LangGraph Orchestrator (graph/orchestrator.py)
              |
              +-- skill_router -------> LLM picks best skill from registry
              |
              +-- skill_executor -----> LLM extracts args & calls A2A agents
              |
              v
     ElevenLabs TTS (services/tts.py)    <- optional
              |
              v
     Audio/Text Response
```

## Project Structure

```
workforce/
├── main.py                        # FastAPI entrypoint (port 8000)
├── graph/
│   ├── state.py                   # LangGraph shared state (AgentState)
│   ├── orchestrator.py            # StateGraph definition & compilation
│   └── nodes/
│       ├── skill_router.py        # LLM skill selection
│       └── skill_executor.py      # LLM arg extraction + A2A calls
├── agents/
│   ├── a2a_models.py              # Shared JSON-RPC request/response models
│   ├── email_agent.py             # A2A Email Agent (port 8001, Resend)
│   ├── weather_agent.py           # A2A Weather Agent (port 8002, OpenWeatherMap)
│   └── translate_agent.py         # A2A Translate Agent (port 8003, DeepL)
├── skills/
│   └── registry.py                # Skill definitions & registry
├── services/
│   ├── channel.py                 # Unified message processing interface
│   ├── stt.py                     # Whisper STT wrapper
│   ├── tts.py                     # ElevenLabs TTS streaming wrapper
│   ├── user_store.py              # User email storage
│   └── telegram_bot.py            # Telegram bot with onboarding flow
├── data/
│   └── users.json                 # Persisted user data
├── .env.example
└── requirements.txt
```

## Skills

| Skill | Description | Backend |
|-------|-------------|---------|
| `send_email` | Compose and send emails | A2A agent → Resend API |
| `weather` | Get current weather | A2A agent → OpenWeatherMap |
| `translate` | Translate text between languages | A2A agent → DeepL API |
| `schedule_meeting` | Schedule meetings/appointments | Local LLM |
| `search_info` | General information lookup | Local LLM |
| `general_chat` | Fallback conversation | Local LLM |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in your API keys in .env
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | Whisper STT + GPT-4o-mini |
| `ELEVENLABS_API_KEY` | No | Text-to-speech |
| `ELEVENLABS_VOICE_ID` | No | Voice ID (defaults to "Rachel") |
| `RESEND_API_KEY` | No | Email sending |
| `RESEND_FROM` | No | Sender email address |
| `OPENWEATHER_API_KEY` | No | Weather queries |
| `DEEPL_API_KEY` | No | Translation (free tier: 500K chars/month) |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot |
| `DEFAULT_USER_EMAIL` | No | Default user email for context |

## Run

```bash
# Terminal 1: Email Agent
uvicorn agents.email_agent:app --port 8001

# Terminal 2: Weather Agent
uvicorn agents.weather_agent:app --port 8002

# Terminal 3: Translate Agent
uvicorn agents.translate_agent:app --port 8003

# Terminal 4: Voice Agent Orchestrator
uvicorn main:app --port 8000

# Terminal 5 (optional): Telegram Bot
python3 -m services.telegram_bot
```

## API Endpoints

### Orchestrator (port 8000)

| Method | Endpoint       | Description |
|--------|----------------|-------------|
| POST   | `/voice`       | Upload audio → JSON (transcript + response) |
| POST   | `/voice/audio` | Upload audio → Streamed MP3 |
| POST   | `/text`        | Text input → JSON |
| POST   | `/text/audio`  | Text input → Streamed MP3 |
| POST   | `/webhook`     | Generic webhook for external channels (WeChat, Slack, etc.) |
| GET    | `/skills`      | List available skills |
| GET    | `/agents`      | List registered A2A agents |
| GET    | `/health`      | Health check |

### Email Agent (port 8001)

| Method | Endpoint                  | Description |
|--------|---------------------------|-------------|
| GET    | `/.well-known/agent.json` | A2A Agent Card |
| POST   | `/a2a`                    | A2A JSON-RPC endpoint |
| GET    | `/health`                 | Health check |

### Weather Agent (port 8002)

| Method | Endpoint                  | Description |
|--------|---------------------------|-------------|
| GET    | `/.well-known/agent.json` | A2A Agent Card |
| POST   | `/a2a`                    | A2A JSON-RPC endpoint |
| GET    | `/health`                 | Health check |

### Translate Agent (port 8003)

| Method | Endpoint                  | Description |
|--------|---------------------------|-------------|
| GET    | `/.well-known/agent.json` | A2A Agent Card |
| POST   | `/a2a`                    | A2A JSON-RPC endpoint |
| GET    | `/health`                 | Health check |

## Test with curl

```bash
# Text input (easiest - no audio needed)
curl -X POST http://localhost:8000/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Send an email to alice@example.com with subject Hello and body How are you?"}'

# Weather query
curl -X POST http://localhost:8000/text \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the weather in Tokyo?"}'

# Translation
curl -X POST http://localhost:8000/text \
  -H "Content-Type: application/json" \
  -d '{"text": "把Hello World翻译成中文"}'

# Voice input
curl -X POST http://localhost:8000/voice \
  -F "audio=@recording.webm"

# Webhook (for WeChat, Slack, etc.)
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the weather in Paris?", "channel": "wechat", "user_id": "user_123"}'

# List skills
curl http://localhost:8000/skills

# List agents
curl http://localhost:8000/agents
```
