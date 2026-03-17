"""Simple user profile store - persists to a JSON file.

Stores per-user info (email, name, etc.) keyed by a channel-specific user ID.
"""

import json
import os
import logging
from pathlib import Path

logger = logging.getLogger("user-store")

_STORE_PATH = Path(os.getenv("USER_STORE_PATH", "data/users.json"))
_store: dict[str, dict] = {}


def _ensure_dir():
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load():
    global _store
    if _STORE_PATH.exists():
        try:
            _store = json.loads(_STORE_PATH.read_text())
        except Exception:
            _store = {}
    else:
        _store = {}


def _save():
    _ensure_dir()
    _STORE_PATH.write_text(json.dumps(_store, indent=2, ensure_ascii=False))


def _key(channel: str, user_id: str) -> str:
    return f"{channel}:{user_id}"


# ---------- Public API ----------

def get_user(channel: str, user_id: str) -> dict | None:
    """Get user profile. Returns None if user not found."""
    if not _store:
        _load()
    return _store.get(_key(channel, user_id))


def set_user_email(channel: str, user_id: str, email: str):
    """Set or update a user's email address."""
    if not _store:
        _load()
    key = _key(channel, user_id)
    if key not in _store:
        _store[key] = {}
    _store[key]["email"] = email
    _save()
    logger.info("User %s email set to %s", key, email)


def get_user_email(channel: str, user_id: str) -> str | None:
    """Get a user's email address. Returns None if not set."""
    user = get_user(channel, user_id)
    if user:
        return user.get("email")
    return None
