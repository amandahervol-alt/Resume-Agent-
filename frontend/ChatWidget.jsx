"""
FastAPI backend for the resume recommendation agent.

Designed to run on Cloud Run (stateless containers that scale to zero). Because
the containers are stateless and a recommendation conversation spans several
turns, conversation state lives in Redis with a 24-hour TTL -- long enough that
a refreshed page resumes, short enough that abandoned chats expire on their own.

Flow per message:
  1. load the session's gathered signals + history from Redis
  2. let Claude converse and extract new signals (extraction.converse)
  3. save the updated state back to Redis
  4. if all six signals are present, run the deterministic rules layer and
     return the recommendation; otherwise return Claude's next question
"""

import os
import json

import redis
from fastapi import FastAPI
from pydantic import BaseModel

import extraction
import rules

app = FastAPI(title="Resume Recommendation Agent")

r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))
SESSION_TTL = 60 * 60 * 24  # 24 hours


class ChatTurn(BaseModel):
    session_id: str
    message: str


def _load(session_id: str) -> dict:
    raw = r.get(f"session:{session_id}")
    return json.loads(raw) if raw else {"history": [], "signals": {}}


def _save(session_id: str, state: dict) -> None:
    r.set(f"session:{session_id}", json.dumps(state), ex=SESSION_TTL)


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
