"""
Language layer: Claude reads each visitor message, keeps the conversation
natural, and extracts any of the six structured signals it can.

Claude does this through tool calling. It is given one tool, `record_signals`,
whose schema mirrors REQUIRED_SIGNALS. When Claude learns something, it calls
the tool with structured values; its spoken reply to the visitor is the text
content. This is how one model can feel conversational to a human while handing
clean, typed data to the deterministic rules layer.

Tool-use pattern (per the Anthropic Messages API): when the model returns
stop_reason == "tool_use", we capture the recorded signals, return a
tool_result, and call again so the model can produce its spoken reply.
"""

import os
import anthropic

from rules import REQUIRED_SIGNALS

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

MODEL = "claude-sonnet-4-6"

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
RECORD_SIGNALS_TOOL = {
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
    Send the conversation so far to Claude. Returns the assistant's spoken reply
    plus any new signals extracted this turn.

    `history` is a list of {role, content} message dicts.
    `known_signals` is what has already been gathered (passed in as context).
    """
    context = (
        f"Signals already gathered: {known_signals or 'none yet'}. "
        f"Still needed: {[s for s in REQUIRED_SIGNALS if s not in known_signals]}."
    )
    system = SYSTEM + "\n\n" + context

    messages = list(history)
    new_signals = {}

    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=system,
        tools=[RECORD_SIGNALS_TOOL],
        messages=messages,
    )

    # If Claude recorded signals, capture them and feed a tool_result back so it
    # can produce its spoken reply (tool_result must precede any text content).
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
            model=MODEL,
            max_tokens=600,
            system=system,
            tools=[RECORD_SIGNALS_TOOL],
            messages=messages,
        )

    reply_text = "".join(b.text for b in response.content if b.type == "text")
    return {"reply": reply_text.strip(), "new_signals": new_signals}
