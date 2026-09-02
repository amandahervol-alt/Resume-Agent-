"""
FastAPI backend for the resume recommendation agent.

Designed to run on Cloud Run (stateless containers that scale to zero). Because
the containers are stateless and a recommendation conversation spans several
turns, conversation state lives in Redis (or in-memory fallback) with a 24-hour TTL.

Flow per message:
  1. load the session's gathered signals + history from Redis / memory
  2. let Claude converse and extract new signals (extraction.converse)
  3. save the updated state back
  4. if all six signals are present, run the deterministic rules layer and
     return the recommendation; otherwise return Claude's next question
"""

import os
import json
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import extraction
import rules

load_dotenv()

app = FastAPI(title="Resume Recommendation Agent")

# Redis connection with resilient in-memory fallback
_in_memory_store: Dict[str, Dict[str, Any]] = {}
r = None

try:
    import redis
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    client = redis.from_url(redis_url, socket_connect_timeout=1)
    client.ping()
    r = client
    print(f"[*] Connected to Redis at {redis_url}")
except Exception as e:
    print(f"[*] Running in local in-memory session mode (Redis not connected: {e})")
    r = None

SESSION_TTL = 60 * 60 * 24  # 24 hours


class ChatTurn(BaseModel):
    session_id: str
    message: str


def _load(session_id: str) -> dict:
    if r is not None:
        try:
            raw = r.get(f"session:{session_id}")
            return json.loads(raw) if raw else {"history": [], "signals": {}}
        except Exception:
            pass

    return _in_memory_store.get(session_id, {"history": [], "signals": {}})


def _save(session_id: str, state: dict) -> None:
    if r is not None:
        try:
            r.set(f"session:{session_id}", json.dumps(state), ex=SESSION_TTL)
            return
        except Exception:
            pass

    _in_memory_store[session_id] = state


@app.post("/chat")
def chat(turn: ChatTurn):
    state = _load(turn.session_id)
    state["history"].append({"role": "user", "content": turn.message})

    result = extraction.converse(state["history"], state["signals"])
    state["signals"].update(result["new_signals"])
    state["history"].append({"role": "assistant", "content": result["reply"]})

    missing = [s for s in rules.REQUIRED_SIGNALS if s not in state["signals"]]
    _save(turn.session_id, state)

    if not missing:
        # All signals gathered -> the rules layer (not the model) decides.
        return {
            "done": True,
            "reply": result["reply"],
            "recommendation": rules.recommend(state["signals"]),
        }

    return {"done": False, "reply": result["reply"], "missing": missing}


@app.get("/healthz")
def healthz():
    return {"ok": True}


# Serve static web interface
frontend_dir = Path(__file__).parent.parent / "frontend"
if (frontend_dir / "index.html").exists():
    @app.get("/", response_class=HTMLResponse)
    def serve_frontend():
        return FileResponse(frontend_dir / "index.html")
