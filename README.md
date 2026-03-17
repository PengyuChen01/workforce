# Voice Agent MVP

**Stack:** Whisper STT -> LangGraph Orchestrator -> A2A Skill Agents -> ElevenLabs TTS

## Architecture

```
User Voice/Text
       |
       v
  FastAPI (main.py :8000)
       |
       v
  Whisper STT (services/stt.py)
       |
       v
  LangGraph Orchestrator (graph/orchestrator.py)
       |
       +-- intent_router -> LLM detects intent & extracts args
       |
       +-- email_node ----> A2A call to Email Agent (:8001)
       |
       +-- synthesis_node -> LLM generates spoken response
       |
       v
  ElevenLabs TTS (services/tts.py)
       |
       v
  Audio/Text Response
```

## Project Structure

```
workforce/
├── main.py                      # FastAPI entrypoint (port 8000)
├── graph/
│   ├── state.py                 # LangGraph shared state (AgentState)
│   ├── orchestrator.py          # StateGraph definition & compilation
│   └── nodes/
│       ├── intent_router.py     # LLM intent detection + arg extraction
│       ├── email_node.py        # A2A HTTP call to email agent
│       └── synthesis_node.py    # LLM response generation
├── agents/
│   └── email_agent.py           # A2A Email Agent (standalone, port 8001)
├── services/
│   ├── stt.py                   # Whisper STT wrapper
│   └── tts.py                   # ElevenLabs TTS streaming wrapper
├── .env.example
└── requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in your API keys in .env
```

## Run

```bash
# Terminal 1: Start A2A Email Agent
uvicorn agents.email_agent:app --port 8001

# Terminal 2: Start Voice Agent Orchestrator
uvicorn main:app --port 8000
```

## API Endpoints

### Orchestrator (port 8000)

| Method | Endpoint       | Description                                   |
|--------|----------------|-----------------------------------------------|
| POST   | `/voice`       | Upload audio file -> JSON (transcript + response) |
| POST   | `/voice/audio` | Upload audio file -> Streamed MP3 audio        |
| POST   | `/text`        | Text input -> JSON (for testing without audio) |
| POST   | `/text/audio`  | Text input -> Streamed MP3 audio               |
| GET    | `/agents`      | List registered A2A agents                     |
| GET    | `/health`      | Health check                                   |

### Email Agent (port 8001)

| Method | Endpoint                   | Description           |
|--------|----------------------------|-----------------------|
| GET    | `/.well-known/agent.json`  | A2A Agent Card        |
| POST   | `/a2a`                     | A2A JSON-RPC endpoint |
| GET    | `/health`                  | Health check          |

## Test with curl

```bash
# Text input (easiest test - no audio needed)
curl -X POST http://localhost:8000/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Send an email to alice@example.com with subject Hello and body How are you?"}'

# Voice input
curl -X POST http://localhost:8000/voice \
  -F "audio=@recording.webm"

# List agents
curl http://localhost:8000/agents
```
