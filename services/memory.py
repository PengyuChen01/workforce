"""Memory services - short-term conversation history & long-term user facts.

Short-term memory (STM): In-memory per-user conversation history (FIFO).
Long-term memory (LTM): JSON-persisted user facts/preferences.
"""

import json
import logging
import os
from datetime import datetime, timezone
from threading import Lock

logger = logging.getLogger("memory")

# ---------- Short-term Memory ----------

_DEFAULT_MAX_TURNS = 20


class ConversationMemory:
    """In-memory per-user conversation history with FIFO eviction."""

    def __init__(self, max_turns: int = _DEFAULT_MAX_TURNS):
        self.max_turns = max_turns
        self._store: dict[str, list[dict]] = {}

    def get_history(self, user_id: str) -> list[dict]:
        """Return conversation history for a user.

        Returns list of {"role": "user"|"assistant", "content": "..."}.
        """
        return list(self._store.get(user_id, []))

    def add_message(self, user_id: str, role: str, content: str) -> None:
        """Append a message and evict oldest if over max_turns."""
        if user_id not in self._store:
            self._store[user_id] = []
        self._store[user_id].append({"role": role, "content": content})
        # Each turn = 1 user + 1 assistant message, so cap at max_turns * 2
        max_messages = self.max_turns * 2
        if len(self._store[user_id]) > max_messages:
            self._store[user_id] = self._store[user_id][-max_messages:]

    def clear(self, user_id: str) -> None:
        """Clear conversation history for a user."""
        self._store.pop(user_id, None)


# Singleton instance
conversation_memory = ConversationMemory()


# ---------- Long-term Memory ----------

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_FACTS_PATH = os.path.join(_DATA_DIR, "user_facts.json")


class UserFactStore:
    """JSON-persisted store for user preferences and facts."""

    def __init__(self, path: str = _FACTS_PATH):
        self._path = path
        self._lock = Lock()
        self._data: dict[str, dict] = self._load()

    def _load(self) -> dict:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get_facts(self, user_id: str) -> list[str]:
        """Return list of known facts for a user."""
        entry = self._data.get(user_id, {})
        return list(entry.get("facts", []))

    def add_fact(self, user_id: str, fact: str) -> None:
        """Add a fact for a user (skip duplicates)."""
        with self._lock:
            if user_id not in self._data:
                self._data[user_id] = {"facts": [], "updated_at": ""}
            facts = self._data[user_id]["facts"]
            if fact not in facts:
                facts.append(fact)
                self._data[user_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save()
                logger.info("Saved fact for user=%s: %s", user_id, fact)


# Singleton instance
user_fact_store = UserFactStore()
