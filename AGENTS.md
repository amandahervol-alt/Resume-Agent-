# Resume Recommendation Agent — AI Orchestration Guide
AGENTS.md — Antigravity Orchestration Architecture

This repository delivers a multi-turn conversational intake assistant and deterministic recommendation engine for resume writing and career transition services.

## Core Principle: "The LLM Proposes; The Rules Dispose"

### 1. Language Layer (`backend/extraction.py`)
- Converses naturally with visitors to extract 6 essential signals via tool calling (`record_signals`):
  1. `career_stage`: entry | mid | senior | executive
  2. `target_roles`: specific job titles targeted
  3. `timeline`: urgent | weeks | exploring
  4. `budget`: integer USD maximum comfort
  5. `prior_resume_work`: none | diy | professional
  6. `self_promotion_comfort`: low | medium | high
- Operates in dual mode:
  - **Live Mode**: Anthropic Claude (`claude-3-7-sonnet-20250219`) tool calling.
  - **Offline Mode**: Deterministic heuristic signal extractor for zero-config testing.

### 2. Deterministic Decision Layer (`backend/rules.py`)
- Turns extracted signals into a package recommendation (`Essentials`, `Professional`, `Executive`).
- Evaluates honest upgrade eligibility (e.g. multi-role targeting or low self-promotion comfort).
- **Hard Budget Cap Enforcement**: The stated budget is applied as a non-negotiable hard cap in code.

### 3. State & Delivery Layer (`backend/main.py` & `frontend/`)
- Multi-turn conversation state managed via Redis (with in-memory fallback for local development).
- Client widgets in React (`frontend/ChatWidget.jsx`) and browser portal (`frontend/index.html`).
