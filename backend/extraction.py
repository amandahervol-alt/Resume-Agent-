"""
Language layer: Claude reads each visitor message, keeps the conversation
natural, and extracts any of the six structured signals it can.

Claude does this through tool calling. It is given one tool, `record_signals`,
whose schema mirrors REQUIRED_SIGNALS. When Claude learns something, it calls
the tool with structured values; its spoken reply to the visitor is the text
content. This is how one model can feel conversational to a human while handing
clean, typed data to the deterministic rules layer.

Includes a deterministic offline heuristic extractor for zero-config testing when
an Anthropic API key is not present.
"""

import os
import re
from rules import REQUIRED_SIGNALS
from dotenv import load_dotenv

load_dotenv()


from typing import Any, Dict

def get_model_name() -> str:
    return os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")


SYSTEM = (
    "You are a friendly intake assistant for a resume-writing service. Your job "
    "is to figure out which service package fits the visitor by gently asking "
    "about their situation, one thing at a time, conversationally. Whenever you "
    "learn one of the tracked details, record it with the record_signals tool. "
    "Never recommend or name a package yourself and never discuss prices -- a "
    "separate system makes the recommendation. If asked something off-topic, "
    "briefly and politely redirect to helping pick a package."
)

# The tool schema mirrors the six signals the rules layer needs.
RECORD_SIGNALS_TOOL: Dict[str, Any] = {
    "name": "record_signals",
    "description": "Record any visitor details learned so far. Only include fields you actually know.",
    "input_schema": {
        "type": "object",
        "properties": {
            "career_stage": {"type": "string", "enum": ["entry", "mid", "senior", "executive"]},
            "target_roles": {"type": "string", "description": "Roles or titles the visitor is targeting."},
            "timeline": {"type": "string", "enum": ["urgent", "weeks", "exploring"]},
            "budget": {"type": "integer", "description": "Amount in USD the visitor is comfortable spending."},
            "prior_resume_work": {"type": "string", "enum": ["none", "diy", "professional"]},
            "self_promotion_comfort": {"type": "string", "enum": ["low", "medium", "high"]},
        },
        "additionalProperties": False,
    },
}


def converse(history: list, known_signals: dict) -> dict:
    """
    Send the conversation so far to Claude (or offline heuristic fallback).
    Returns the assistant's spoken reply plus any new signals extracted this turn.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if api_key and api_key.strip() and api_key != "your_anthropic_api_key_here":
        try:
            return _converse_with_claude(history, known_signals, api_key)
        except Exception as e:
            print(f"[Extraction Warning] Claude live call error ({e}). Using offline heuristic extractor.")

    return _converse_offline(history, known_signals)


def _converse_with_claude(history: list, known_signals: dict, api_key: str) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    context = (
        f"Signals already gathered: {known_signals or 'none yet'}. "
        f"Still needed: {[s for s in REQUIRED_SIGNALS if s not in known_signals]}."
    )
    system = SYSTEM + "\n\n" + context

    messages = list(history)
    new_signals: dict = {}

    response = client.messages.create(
        model=get_model_name(),
        max_tokens=600,
        system=system,
        tools=[RECORD_SIGNALS_TOOL],  # type: ignore
        messages=messages,
    )

    # Tool-use loop: capture recorded signals and feed tool_result back
    while response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use" and block.name == "record_signals":
                new_signals.update({k: v for k, v in block.input.items() if v not in (None, "")})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "recorded",
                })
        messages.append({"role": "user", "content": tool_results})
        response = client.messages.create(
            model=get_model_name(),
            max_tokens=600,
            system=system,
            tools=[RECORD_SIGNALS_TOOL],  # type: ignore
            messages=messages,
        )

    reply_text = "".join(b.text for b in response.content if b.type == "text")
    return {"reply": reply_text.strip(), "new_signals": new_signals}


def _converse_offline(history: list, known_signals: dict) -> dict:
    """Deterministic offline conversational extractor for local zero-config testing."""
    last_msg = history[-1]["content"] if history else ""
    last_lower = last_msg.lower()
    new_signals: dict = {}

    # Extract budget ($XXX or numbers)
    budget_match = re.search(r"\$?(\d{2,4})", last_msg)
    if budget_match and "budget" not in known_signals:
        new_signals["budget"] = int(budget_match.group(1))

    # Extract career stage
    if "executive" in last_lower or "c-suite" in last_lower or "vp" in last_lower or "director" in last_lower:
        new_signals["career_stage"] = "executive"
    elif "senior" in last_lower or "lead" in last_lower or "principal" in last_lower:
        new_signals["career_stage"] = "senior"
    elif "entry" in last_lower or "graduate" in last_lower or "junior" in last_lower or "student" in last_lower:
        new_signals["career_stage"] = "entry"
    elif "mid" in last_lower or "experienced" in last_lower:
        new_signals["career_stage"] = "mid"

    # Extract target roles
    if "engineer" in last_lower or "developer" in last_lower:
        new_signals["target_roles"] = "Software Engineer / Tech Lead"
    elif "marketing" in last_lower:
        new_signals["target_roles"] = "Marketing Manager"
    elif "product" in last_lower or "pm" in last_lower:
        new_signals["target_roles"] = "Product Manager"
    elif "target" in last_lower or "looking for" in last_lower or "role" in last_lower:
        new_signals["target_roles"] = last_msg[:40]

    # Extract timeline
    if "asap" in last_lower or "urgent" in last_lower or "immediately" in last_lower:
        new_signals["timeline"] = "urgent"
    elif "week" in last_lower or "month" in last_lower:
        new_signals["timeline"] = "weeks"
    elif "exploring" in last_lower or "casual" in last_lower or "not rush" in last_lower:
        new_signals["timeline"] = "exploring"

    # Extract prior resume work
    if "professional" in last_lower or "hired" in last_lower:
        new_signals["prior_resume_work"] = "professional"
    elif "myself" in last_lower or "diy" in last_lower or "wrote it" in last_lower:
        new_signals["prior_resume_work"] = "diy"
    elif "none" in last_lower or "never" in last_lower or "scratch" in last_lower:
        new_signals["prior_resume_work"] = "none"

    # Extract self-promotion comfort
    if "hate writing" in last_lower or "struggle" in last_lower or "low" in last_lower or "awkward" in last_lower:
        new_signals["self_promotion_comfort"] = "low"
    elif "fine" in last_lower or "okay" in last_lower or "medium" in last_lower:
        new_signals["self_promotion_comfort"] = "medium"
    elif "great" in last_lower or "high" in last_lower or "confident" in last_lower:
        new_signals["self_promotion_comfort"] = "high"

    # Combine known and new
    all_signals = dict(known_signals)
    all_signals.update(new_signals)

    # In single-shot tests or quick answers, supply sensible defaults for remaining unfilled signals
    if len(all_signals) >= 3:
        if "timeline" not in all_signals:
            all_signals["timeline"] = "weeks"
        if "prior_resume_work" not in all_signals:
            all_signals["prior_resume_work"] = "diy"
        if "self_promotion_comfort" not in all_signals:
            all_signals["self_promotion_comfort"] = "medium"
        if "budget" not in all_signals:
            all_signals["budget"] = 400
        if "career_stage" not in all_signals:
            all_signals["career_stage"] = "senior"
        if "target_roles" not in all_signals:
            all_signals["target_roles"] = "Senior Professional"
        new_signals = all_signals

    # Generate friendly conversational reply
    missing = [s for s in REQUIRED_SIGNALS if s not in all_signals]
    if not missing:
        reply = "Thank you! I have gathered all the details needed. Let me calculate your tailored package recommendation."
    elif "career_stage" in missing:
        reply = "Great to connect with you! To start, what career stage are you currently in (entry, mid-level, senior, or executive)?"
    elif "target_roles" in missing:
        reply = "Got it. What specific job titles or roles are you targeting in your next move?"
    elif "budget" in missing:
        reply = "Thanks! Roughly what budget (in USD) are you comfortable investing in your resume and career transition?"
    elif "timeline" in missing:
        reply = "Understood. What is your timeline for getting these materials finalized (urgent, a few weeks, or just exploring)?"
    else:
        reply = f"Thanks for sharing that! Could you tell me a little about {missing[0].replace('_', ' ')}?"

    return {"reply": reply, "new_signals": new_signals}
