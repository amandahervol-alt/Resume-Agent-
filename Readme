# Resume Recommendation Agent

A conversational agent that lives on a resume-writing company's website, asks a
visitor the right questions, and recommends the service package that fits them —
with a hard rule that it can never recommend a package above the visitor's
stated budget. Built with React, FastAPI, Claude, and Redis on Google Cloud.

The company's team was spending real time on intake calls because customers
didn't know which package they needed. This agent handles that conversation
automatically: it feels like a natural chat, but underneath it extracts
structured signals and hands the actual decision to deterministic code.

> **About this version.** This is a sanitized reference implementation of a
> system originally built for a real client. It contains no client code, data,
> real package names, or real prices — the tiers, thresholds, and decision logic
> here are illustrative placeholders. It documents the architecture and the
> engineering decisions behind the production system, not the production system
> itself.

## Architecture

```mermaid
flowchart TD
    A["Visitor + chat widget<br/><i>React · embedded on the site</i>"] <--> B["FastAPI backend<br/><i>Cloud Run · scales to zero</i>"]
    B <--> R["Redis<br/><i>conversation state · 24h TTL</i>"]
    B --> C["Claude<br/><i>extracts signals via tool calling</i>"]
    C --> D["Rules layer<br/><i>decides · budget is a hard cap</i>"]
    D --> E["Recommendation<br/><i>shown to the visitor</i>"]

    classDef llm fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    classDef code fill:#ccfbf1,stroke:#0d9488,color:#134e4a;
    classDef orch fill:#f1f5f9,stroke:#64748b,color:#1e293b;
    class A,B,R,E orch;
    class C llm;
    class D code;
```

The conversation is multi-turn (the double arrow at the top): each visitor
message gathers a little more, the signals accumulate in Redis across turns, and
the agent keeps asking until it has what it needs to decide.

## The design principle

**The LLM proposes; the rules dispose.**

Claude is excellent at holding a natural conversation and pulling structured
signals out of it. But it does not get to make the recommendation. A
deterministic rules layer picks the package, and the visitor's stated budget is
enforced in code as a hard cap.

The reasoning: an LLM that occasionally upsells someone past their stated budget
isn't a tuning problem you patch with prompt wording — it's a refund-and-trust
problem. So the guardrail goes somewhere it physically cannot drift. The system
prompt sets the goal; the deterministic layer enforces it.

## How it works

1. **Surface.** A React chat widget is embedded into the existing site (not a
   separate page), so starting a conversation feels low-commitment.
2. **Backend.** Each message hits a FastAPI service on Cloud Run, which scales
   to zero between sessions — bursty traffic, near-zero idle cost.
3. **State.** Conversation state lives in Redis with a 24-hour TTL, so a
   refreshed page resumes and abandoned chats expire on their own.
4. **Extraction.** Claude converses naturally while using tool calling to
   extract six signals: career stage, target roles, timeline, budget, prior
   resume work, and comfort with self-promotion.
5. **Decision.** Once all six are gathered, the deterministic rules layer picks
   a package, considers a genuine upgrade where the higher tier fits better, and
   then applies the budget cap last so it overrides everything.
6. **Guardrails.** Secrets live in a secrets manager (never in code), and the
   agent stays scoped to recommending a package rather than answering anything.

## Tech stack

| Layer | Choice | Why |
| --- | --- | --- |
| Surface | React widget, embedded | Feels like part of the site; low commitment to start |
| Backend | FastAPI on Cloud Run | Bursty traffic; serverless scales to zero |
| Conversation state | Redis (24h TTL) | Stateless containers need shared state; stale chats self-expire |
| Language work | Claude, tool calling | Natural conversation + structured signal extraction in one model |
| The decision | Deterministic Python | The recommendation and budget cap must not be able to drift |
| Secrets | Secrets manager | Keys never live in code or environment files |

## Repository layout

```
backend/
  main.py          FastAPI app: conversation endpoint, Redis state, glue
  extraction.py    Claude tool-calling layer that extracts the six signals
  rules.py         Deterministic decision tree + the hard budget cap
  requirements.txt
frontend/
  ChatWidget.jsx   Minimal embedded React chat widget
.env.example       Required environment variables (no real secrets)
.gitignore
```

## Running it yourself

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env          # then fill in ANTHROPIC_API_KEY and REDIS_URL
uvicorn main:app --reload           # serves on http://localhost:8000
```

You'll need a running Redis instance (`redis://localhost:6379` by default) and
an Anthropic API key. The frontend widget posts to the backend's `/chat`
endpoint; point `VITE_API_URL` at the backend when you wire it into a site.
