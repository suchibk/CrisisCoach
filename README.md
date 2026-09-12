# Crisis Coach prototype

Python prototype of the local-first car-collision coach described in the project documents. The current scope is limited to legal and safety use cases following a road-traffic collision. The app includes incident collection, report review, profile setup, and isolated practice scenarios for Priya, Marcus, and Dana.

## Presenting this project

**New teammate? Start with the [AI master class presenter handbook](docs/presenter-handover.md).** It takes you from cloning this repository to a working Dana demo, with ElevenLabs setup, screenshots, an eight-minute script, implemented AI concepts, and Q&A.

## Quick start

See the [deployment handbook](docs/deployment-handbook.md), [runnable smoke test](scripts/demo_smoke.py), and [demo presentation notes](docs/demo-presentation.md).

For the UI with real voice, follow the [ElevenLabs setup and illustrated demo guide](demo/README.md): `.env` configuration, Windows launch commands, microphone/playback tests, and Dana happy/unknown paths.

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
- Two explicitly uncertain safety answers cause stand-down; inactivity pauses the check without claiming an injury.
- Reopening a stood-down incident asks for medical clearance before doing anything else.
- No network, API key, model, or vector store is required for the safety path.

The external stack from the architecture deck is represented as optional dependencies and adapters so the deterministic test suite stays local: Streamlit, LangGraph/LangChain, Pinecone, Nebius via an OpenAI-compatible client, ElevenLabs, Open-Meteo, python-docx, and LangSmith.

## Source layout

- `models/session.py` contains session state; `models/responses.py` contains instruction contracts.
- `orchestration/engine.py` and `graph.py` own shared turn execution; `domains/collision/workflow.py` preserves the original API.
- `domains/collision/safety.py` owns collision injury detection and stand-down.
- `domains/collision/ai/` contains the optional collision injury classifier.
- `interfaces/` adapts the shared workflow to CLI and Streamlit.

Only the collision domain is implemented. Shared timers and persistence also contain executable behavior. `domains/medical/`,
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

## Architecture implementation status

The package structure is prepared for the shared engine and domain packs. The collision safety workflow, conversation controls, and SQLite incident persistence run. Shared graph orchestration is implemented. A deterministic evidence catalogue and adaptive priority planner are implemented; local capture tools and DOCX evidence-pack generation are implemented.

See [architecture](docs/architecture.md), [implementation sequence](docs/implementation-plan.md), and [30-feature traceability](docs/feature-traceability.md). Compatibility imports preserve the original public API. Planned leaf modules will be added with their implementations.

## Safety routing increment

Safe-location answers are interpreted separately from injury answers. Evidence responses no longer count as unanswered injury questions, and new injury language still pre-empts collection. Reopening a stood-down incident asks the medical-check question. Timers and pause/resume are implemented; broader reviewed danger policies remain pending.

## Conversation controls and silence timers

Use `stop` or `pause`, `go on` or `resume`, `repeat`, and `slow down`. Pause retains the current question. Repeat preserves its exact words. Slow-down metadata controls optional ElevenLabs playback; text is unchanged.

The CLI and active Streamlit page now poll workflow timers: eight seconds per unanswered safety prompt (one retry, then a resumable pause), and thirty seconds for evidence reminders. Timers stop while paused or stood down. CLI and Streamlit save incidents to SQLite. Process-local deadlines are discarded and safety is rechecked when reopening; timers do not run while the app is closed. Streamlit polling requires the page to remain connected.

## Saved incidents and recovery

Both interfaces use SQLite by default. On Windows the database is `%LOCALAPPDATA%/CrisisCoach/incidents.sqlite3`; elsewhere it is under `$XDG_DATA_HOME/crisis-coach` or `~/.local/share/crisis-coach`. Override the directory using `CRISIS_COACH_DATA_DIR` in the process environment. No database is created inside the project by default.

```powershell
python -m crisis_coach.interfaces.cli --list
python -m crisis_coach.interfaces.cli --incident <incident-id>
```

Streamlit provides saved-incident selection and a New incident button in the sidebar. Reopening preserves evidence requests and stand-down status. Active incidents restart safety checks; paused incidents stay paused and check safety after resuming. The UI begins with the recovery prompt, not a reconstructed chat transcript; accepted event/response records remain in SQLite.

State and accepted input/output events commit atomically, with revision checks against competing writers. Replayed event IDs are ignored. Non-safety save failures block the transition; a stand-down is still shown if storage fails, explicitly warning that the update could not be saved. In that failure case, disk recovery can only restore the last successful save.

Direct `CollisionWorkflow()` construction remains in-memory for tests and embedded callers; inject `SQLiteIncidentRepository` or use `bootstrap.build_coach()` for persistence. Photo files, original text, and generated evidence packs are stored locally. SQLite is local storage, not encrypted storage. Use synthetic demonstration data.

## Shared domain graph

The collision facade now delegates to WorkflowEngine with CollisionPack. The explicit domain registry exposes only implemented domains; medical, workplace, and home remain unavailable. Incidents record their domain and pack version, and mismatched workflows refuse to process them. Existing records default to collision version 1.

Each turn follows safety -> controls -> gate -> plan, stopping as soon as a node handles the event. Both runners use Pydantic graph state and the same routing rules. The default runner is local Python. To use LangGraph, install `.[agent]` and set `CRISIS_COACH_GRAPH_BACKEND=langgraph` in the process environment. There is no automatic .env loading.

The plan node ranks applicable pending evidence by value and estimated time remaining. Completed/reported, failed, and unavailable items are not requested again. SQLite remains the transaction boundary; LangGraph checkpoint/approval integration will follow executable tools.

## Adaptive evidence collection

Describe the scene during the initial conversation, then answer all three safety questions. The prototype also accepts `/scenario full`, `/scenario unattended`, and `/scenario scuff` after safety clearance to select an explicit demonstration path. Examples such as "I came back to my parked car" and "I scraped a bollard" select the corresponding catalogue. Unspecified incidents use the full-collision catalogue.

After a photo instruction, `done` or `photo taken` records a **user report only** and advances. It does not upload or verify a photograph. For text evidence use `/collected <item_id> <details>`, for example `/collected witness_details Maya, 555-0100` or `/collected statement I reversed into the bollard.` The `/collected` command also records a report, never a verified attachment. Catalogue item IDs are listed in `domains/collision/resources/evidence_catalogue.json` under the source package.

Use `/unavailable <item_id> <reason>` or `/failed <item_id> <reason>` to retain an honest gap. `/missing` lists pending and unavailable/failed items. These report commands do not store files. Use the local capture controls below for actual files; photo quality remains unverified.

"There's a witness walking away" and "He's getting back into his car" reprioritize the remaining tasks. Departure windows are configurable-in-code estimates (60 seconds); unattended footage-reference collection uses a 120-second urgency estimate, not an assertion about footage retention. Repeated signals do not extend the window. Explicit departure marks remaining affected items unavailable. Estimated expiry alone never asserts that evidence is gone.

Priority is evidence value divided by remaining estimated seconds (minimum one second), or 300 seconds for routine items; ties follow catalogue order. Pydantic decision records retain the candidate comparison in SQLite. Scene recognition is currently a limited phrase adapter, not general natural-language understanding. An all-reported scene remains active for corrections and late safety reports; it is not treated as a verified evidence pack.

## Local photo and text capture

The CLI supports these commands after safety clearance:

```text
/attach wide_scene_photo C:\Photos\collision.png
/statement statement I was stationary when the other car hit mine.
/statement other_insurance The driver supplied these insurance details: ...
```

The path is the remainder of the `/attach` command, so spaces are supported without quotation marks. `/statement` stores the supplied text verbatim, including line breaks when submitted through the typed API or Streamlit. Item IDs come from the collision catalogue. Streamlit also provides a photo uploader or text box for the current requested item.

Actual capture sets the item to COLLECTED and stores attachment references, hashes, byte counts, and media type in SQLite. `/collected` remains a user-report-only command. Files live under the configured application-data directory's `attachments` folder. Original filenames are not used as storage paths. Duplicate file content within an incident reuses the existing blob.

JPEG/PNG signature checks and a 20 MiB size limit are enforced; image decoding, legibility checks, OCR, and vision verification are not implemented. Stored photos are never marked VERIFIED. External tools remain blocked until a real approval workflow is implemented.

File storage and SQLite are separate durability steps. A failed database commit can leave an unreferenced immutable file, but no false COLLECTED record. Retrying is safe; automated orphan cleanup is pending. Streamlit temporarily stages uploads and removes staging files after execution. Original text is screened for injury before storage.

## Completeness and evidence-pack export

Install the optional document dependency:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[reports]"
```

After safety clearance, enter `/export` in the CLI, or select **Build evidence pack** in Streamlit. The CLI prints the saved path; Streamlit offers **Download evidence pack**. Packs live under the application-data directory's `exports` folder. Exporting does not send anything, end the incident, or reset the collection timer.

The DOCX contains the incident identifier and snapshot revision, export timestamp, stored images, verbatim supplied text, user-reported notes, completeness table, and the latest planning comparison. The timestamp is explicitly the export time, not the collision time. Uncaptured context and unsourced policy/legal guidance are not invented.

Completeness is the fraction of applicable catalogue items with stored attachments included successfully. Reported-only items, missing files, integrity failures, and unsupported images do not count. It is not an insurer intake score or photo-quality verification. Additional supplied evidence is retained even if a later scenario change makes it inapplicable to the current checklist.

Export validates attachment paths, sizes, and SHA-256 hashes. Missing/corrupt/undecodable attachments are listed as gaps in a partial pack rather than silently omitted. Generating a report never changes evidence statuses. Each export is a snapshot; build a new pack after later additions. Export references survive reopening. A failed SQLite commit can leave an unreferenced export file, as with attachment storage.

## Local policy and duties passages

After safety clearance, try the synthetic demonstration:

```text
/knowledge-demo
/ask What is my excess?
/ask How long do I have to notify my insurer?
/ask Do I need to call police?
```

Demo mode explicitly binds fictional policy `demo-meridian`, fictional jurisdiction `DEMO`, and reference date 2026-09-08. Every demo passage is labelled SYNTHETIC; these are not real legal or insurance requirements. Dana is never automatically assigned Priya's policy.

The tools `check_policy` and `assess_duties` run locally. Matching passages include document title, section, source ID, source URI, and effective dates. Unknown topics, absent context, unreviewed sources, wrong policy/jurisdiction, expired records, and source-loading failures yield an explicit unavailable result. Fault and claim recommendations are refused. Questions preserve the current collection instruction and timer; new injury still pre-empts lookup.

To supply reviewed sources, set `CRISIS_COACH_KNOWLEDGE_DIR` to a directory containing JSON files conforming to `SourceCorpus` in `models/knowledge.py`. The bundled demo files show the format. Each passage needs provenance, scope, effective dates, supported topics, and review metadata. Supported topics currently include policy `excess` and `notification`, and duties `police` and `exchange`. Source content is quoted, not executed or fetched. Review must be performed by the corpus maintainer; metadata alone does not establish correctness.

In Streamlit, use **Policy and jurisdiction for source lookup** to set the matching identifiers and incident reference date. Embedded callers can submit a typed `ContextEvent(context=KnowledgeContext(...))`. The CLI supports demo context directly; other contexts currently use that API or Streamlit. `.env` files are not automatically loaded.

Recorded answers and citations survive restart and appear in later evidence packs. Multiple matching passages are shown without automatically choosing between conflicting requirements. No paid model, API key, or subscription is required for this milestone.

## Bounded AI specialists

Optional scene and photo specialists use Pydantic structured outputs. Install the existing `agent` extra and configure `CRISIS_COACH_AI_API_KEY`, `CRISIS_COACH_AI_BASE_URL`, and separate `CRISIS_COACH_AI_SCENE_MODEL` / `CRISIS_COACH_AI_VISION_MODEL` values for models supported by your provider. Configuration alone does not enable these specialists. `.env` files are not automatically loaded.

After safety clearance, use `/ai-text on` or `/ai-images on`, or the Streamlit **Optional AI sharing** controls. This permits sending eligible text or newly captured photos to the configured provider and may incur charges. Use `/ai-text off` or `/ai-images off` to disable sharing. Reopening an incident resets these permissions. The pre-existing optional injury classifier remains separately configuration-driven; these switches govern the new specialists only.

The scene interpreter is a fallback for text not handled by local scene rules. Exact supporting quotes are required. Proposed scene changes require `confirm scene` or `reject scene`; possible injury can immediately trigger stand-down. AI cannot clear safety gates or choose workflow transitions.

Photo review assesses blur, darkness, occlusion, subject, and readability. A usable assessment sets the evidence status to `verified` for AI image usability only, not identity, fault, human review, or claim acceptance. Uncertain or failed calls retain collected originals. The first quality rejection requests a safe retake; the second distinct rejected image stops further review for that item. Repeated identical bytes reuse the saved assessment. An existing usable image is preserved as verified.

Local capture accepts up to 20 MiB; AI review accepts up to 5 MiB. Calls use the configured short timeout and no automatic retries. Missing dependencies/configuration and model errors retain local operation. Provider compatibility and quality require separate live validation; automated tests use fakes and never upload incident data. Disable third-party LangChain tracing when processing incident data unless separately authorized.

## ElevenLabs voice

Install `pip install -e ".[ui,voice]"` and set `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` in your environment. Restart Streamlit, open **ElevenLabs voice**, and enable playback or transcription. Record a short answer, send it for transcription, review it, and submit. Spoken responses preserve the coach text and slow-down setting. Voice is optional and calls require explicit controls; no calls happen just because credentials are configured.

See [voice setup and behavior](src/crisis_coach/interfaces/voice/README.md) for limits and data handling. Playback supports manual preparation or opt-in automatic speech for new responses. See the [illustrated setup and testing guide](demo/README.md). This is push-to-record; continuous hands-free conversation remains future work.

## Incident time, location and weather

After safety clearance, open **Incident time, location and weather** in Streamlit, or submit this CLI command:

```text
/context {"occurred_at":"2026-09-11T14:30:00-04:00","location":"Oak Street near the library","weather":"Rain"}
```

Use a timezone offset for the incident time. Fields are optional; saving replaces the context, and `/context {}` clears it. Details are stored as user-provided, unverified observations and included in subsequent DOCX exports. Unknown fields are labelled unknown. Updates preserve the collection task and timer, and do not change the separate policy/jurisdiction source context. No location or weather provider is contacted.

## GoldenTestData UI and practice

Start the app with `python -m streamlit run src/crisis_coach/interfaces/streamlit_app.py`.

Choose **Practice** in the sidebar to use synthetic data with no external AI/voice calls. Select a scenario and press **Start / reset practice**, then use suggested inputs or type your own. **Simulate rejected photo** and **Simulate usable photo** create labelled fixture captures. The practice clock advances only through its button. The decision panel displays actual graph routes and priority comparisons. Leaving/resetting practice removes its temporary storage; returning to a live incident rechecks safety.

Choose **Profile** to save optional vehicle, insurer/policy, and trusted-contact details locally. New incidents take a profile snapshot; existing incidents and source context are not silently changed. **Evidence pack** shows original text/photos and gaps, builds a real DOCX, and offers a download. Practice exports are explicitly labelled synthetic. Dark/light appearance and a mobile-width layout are available.

Directed hostility and bounded fire-risk language now stop collection. Environmental stand-down has its own re-entry check; injury still takes precedence. These are limited deterministic rules with pending independent expert review. Apology handling is neutral and makes no liability determination.

Run golden evaluations with `python -m crisis_coach.evaluation.runner evals/scenarios/golden.json`. See [test instructions](evals/README.md) and [acceptance report](docs/golden-acceptance-report.md) for the T1-T14 mapping, screenshots and remaining validation.
