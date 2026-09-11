# Crisis Coach prototype

Python prototype of the local-first car-collision coach described in the project documents. The current scope is limited to legal and safety use cases following a road-traffic collision. The implemented sample focuses on Dana Okoye's safety stand-down scenario.

## Quick start

```powershell
cd "Final Project"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m crisis_coach.interfaces.cli
```

Optional Streamlit interface:

```powershell
pip install -e ".[ui]"
streamlit run src/crisis_coach/interfaces/streamlit_app.py
```

Run tests with `pytest`.

## What this slice proves

- Every turn enters a deterministic safety guard before any planner.
- The scene cannot advance until the user's injury and other-person injury gates are answered.
- An injury signal immediately ends evidence collection and directs the user to call 911.
- Two unanswered safety prompts are treated as unsafe and cause the same stand-down.
- Reopening a stood-down incident asks for medical clearance before doing anything else.
- No network, API key, model, or vector store is required for the safety path.

The external stack from the architecture deck is represented as optional dependencies and adapters so the deterministic test suite stays local: Streamlit, LangGraph/LangChain, Pinecone, Nebius via an OpenAI-compatible client, ElevenLabs, Open-Meteo, python-docx, and LangSmith.

## Source layout

- `models/session.py` contains domain-neutral session state and instruction contracts.
- `domains/collision/workflow.py` owns collision turn ordering.
- `domains/collision/injury_guard.py` owns collision injury detection and stand-down.
- `domains/collision/ai/` contains the optional collision injury classifier.
- `interfaces/` adapts the shared workflow to CLI and Streamlit.

Only `domains/collision/` contains executable behavior. `domains/medical/`,
`domains/workplace/`, and `domains/home/` are empty placeholders for future work.
They are not selectable crisis types and contain no workflows or guidance.

The collision domain records requirements and can present sourced policy or
legal-duty information as integrations are added. It must not determine fault,
argue liability, or provide legal advice.

## Optional AI classification

Dana's explicit injury statement always uses the deterministic guard and never
needs an AI call. An optional Nebius model can recognize additional injury
language only when the local classifier is uncertain:

```powershell
pip install -e ".[agent]"
Copy-Item .env.example .env
```

Set `CRISIS_COACH_AI_API_KEY`, `CRISIS_COACH_AI_BASE_URL`, and
`CRISIS_COACH_AI_MODEL` in the process environment before starting the CLI.
The application does not load `.env` automatically. If any setting is absent,
the classifier is disabled. Provider errors fall back to the conservative local
guard. AI may trigger a stand-down, but it can never clear an ambiguous safety
answer or override a deterministic injury result.
