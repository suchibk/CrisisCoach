# Implementation sequence

1. Correct safety interpretation, danger precedence, timers, pause, and medical re-entry; preserve Dana regression coverage.
2. Implement typed input events, incident repository, migrations, durable checkpoints, and recovery.
3. Build domain contracts, registry, graph supervisor, deterministic planner, and versioned collision resources.
4. Implement Priya, Marcus, and minor-scuff applicability and collection paths.
5. Add attachments, completeness, user-reviewed statements, and local DOCX export.
6. Add sourced knowledge, bounded AI specialists, and explicit offline fallback.
7. Add profile/practice views, approved mock delivery, follow-up additions, and optional voice.
8. Define a reviewed second domain and implement scenario evaluation and operational metrics throughout the milestones.

Keep existing import paths as compatibility exports during migration. Test resource inclusion in an installed wheel when packaging changes. Do not expose unavailable domains as functional choices.

## Progress: safety routing increment

Implemented question-specific safe-location handling, explicit affirmative injury answers, injury precedence over ambiguity, evidence-phase safety monitoring without reopening injury questions, contextual medical re-entry, and duplicate evidence-request prevention. Streamlit uses typed lifecycle state and supports in-memory incident reopening. Removed unsupported durable-save claims from runtime messages.

Validation: 32 tests passed, including 11 new safety regression cases. Streamlit changes were inspected but not interactively tested.

Remaining in the safety milestone: broaden reviewed danger rules, typed timer events and silence deadlines, pause/repeat/resume commands, and adversarial language evaluation. The local regex classifier is intentionally limited and is not clinical validation. Durable persistence and restart recovery remain the next infrastructure milestone. Current photo handling still requests one placeholder evidence item; capture and adaptive planning are not implemented.

## Progress: typed events, silence timers, and controls

Implemented Pydantic-discriminated text, control, and timer events; an injectable monotonic clock; eight-second safety retries followed by stand-down; thirty-second evidence reminders; pause, resume, verbatim repeat, and slow-down metadata. Stale timers are ignored and immediately repeated event IDs are suppressed. Full durable idempotency remains part of persistence work.

CLI input runs separately from timer polling. Streamlit polls while its page is running using a one-second fragment. Pause retains the current task and cancels its timer; resume schedules a fresh deadline. Injury reports still pre-empt paused conversations, and resume cannot bypass stand-down. Slow-down is response metadata until the voice adapter exists.

Validation: 41 automated tests passed. Browser interaction has not been manually verified. Timers are in-process and are not persisted across restarts. The next infrastructure step is SQLite incident persistence and recovery; broader reviewed danger rules remain outstanding in the safety backlog.

## Progress: SQLite persistence and recovery

Implemented a Pydantic-backed repository contract, versioned SQLite schema, transactional event/response ledger and state snapshots, optimistic revision checks, replay suppression, and durable start/turn/reopen behavior. CLI supports --list and --incident; Streamlit supports saved-incident selection. Storage defaults outside the repository and can be overridden with CRISIS_COACH_DATA_DIR.

Reopening drops old monotonic deadlines and requires fresh safety answers. Stand-down and pause states remain enforced. Failed writes do not commit in-memory progress; emergency stand-down remains visible with an explicit unsaved warning. Durable graph checkpoints and attachments are deferred until those components exist.

Verification covers restart, medical re-entry, pause recovery, timer reset, replay, concurrent writers, corrupt data, future schema rejection, rollback, and failed safety saves. Next: domain contracts/registry and the shared deterministic orchestration graph, followed by collision evidence catalogue and adaptive planning. Reviewed broader danger rules remain a tracked safety gap.

## Progress: domain contracts, registry, and shared graph

Implemented DomainMetadata and DomainPack contracts, an explicit registry, CollisionPack policy, and WorkflowEngine. CollisionWorkflow remains a compatibility facade. Pydantic TurnState flows through safety, controls, gate, and plan nodes with deterministic conditional edges. The optional LangGraph backend and local runner share nodes/routing; neither permits model-selected transitions.

Incidents record domain_id and pack_version with legacy collision defaults. Reopening with a mismatched pack is rejected. A synthetic test-only domain verifies independent gate values and behavior; it is never exposed as a real crisis domain.

Next: versioned collision evidence catalogue, applicability rules, deterministic priority planner, and scenario coverage for Priya/Marcus/scuff. The current plan node still requests only the wide photograph. Broader danger policies remain a separate outstanding safety requirement. LangGraph checkpointers will be added with interruptible external tools, not alongside a second authoritative incident store now.

## Progress: evidence catalogue and adaptive planner

Implemented validated catalogue version 1, typed evidence records and planning decisions, full/unattended/scuff applicability, departing witness/driver urgency, explicit unavailable/failed records, missing-item reporting, and durable evidence recovery. Injury still exits before evidence updates. Pure ranking uses value/time with stable catalogue-order ties. Estimated deadlines use timezone-aware UTC and survive restart; estimated expiry does not assert actual departure.

Collection commands currently record user reports rather than actual attachments. No photo-quality verification or automatic extraction is claimed. Text scene interpretation is a limited deterministic phrase adapter with explicit scenario commands for demos. Existing evidence status and catalogue versions are validated before updates.

Next: typed tool registry/executor and actual local attachment/statement capture, then completeness and evidence-pack assembly. Source retrieval and bounded AI interpretation follow. Broader reviewed danger rules remain outstanding.

## Progress: local capture tools

Implemented typed tool metadata/arguments/results, explicit registry and executor, graph capture node, immutable content-addressed local attachments, verbatim text storage, CaptureEvent handling, CLI capture commands, and Streamlit upload/text controls. Domain applicability and safety gates precede capture. Pydantic attachment references persist in SQLite; collected files are distinct from reported evidence and are not marked verified.

External/approval-required tools are blocked; no approval UI or delivery tool is implied. Filesystem writes are idempotent but not transactionally coupled to SQLite: failed commits may leave unreferenced blobs. Photo screening checks size/signature only; actual image QA and OCR remain pending. Original text is stored unchanged and never interpreted as scene-control commands.

Next: completeness calculations and a local evidence pack containing actual attachments, original text, reported-only items, and explicit gaps. Broader reviewed safety policies and source-grounded guidance remain outstanding.

## Progress: completeness and local evidence packs

Implemented typed completeness rows and computed totals, a build_evidence_pack tool with its own argument/result models, DOCX image/text assembly, attachment path/hash checks, explicit partial-pack gaps, additional-evidence preservation, persisted export references, CLI /export, and Streamlit download controls. Export runs through a safety-gated report node on both graph backends. File generation is local, with no delivery or AI rewriting.

The document labels its creation time as export time; incident time, location, weather, source-grounded requirements, and insurer-specific intake are not fabricated. Completeness measures the current catalogue only. Existing collection instructions and timers survive export. Additional updates require a new snapshot.

Next: grounded knowledge/source contracts and local retrieval for policy/duties, followed by bounded AI interpretation and photo verification. The remaining broader danger policies, real context capture, profile setup/practice, and external approval/delivery flow remain tracked requirements.

## Progress: grounded local policy and duties retrieval

Implemented SourceCorpus/SourcePassage/KnowledgeContext/KnowledgeQuery/KnowledgeAnswer models, JSON ingestion, local topic retrieval, exact citation validation, check_policy and assess_duties tools, question/context graph routing, synthetic demonstration fixtures, and explicit context binding. Answers and citations persist in SQLite and evidence packs. Unknown/expired/unreviewed/inapplicable sources abstain; no corpus-loading failure blocks the local safety guard.

Streamlit includes source-context controls; CLI supports /knowledge-demo and /ask. Paid inference, Pinecone, semantic retrieval, live policy ingestion/OCR, and real legal sources are not part of this increment. Maintainer review is required for imported sources. Questions do not change the current collection task or timer.

Next: bounded AI scene interpretation and image-quality verification behind structured-output adapters, retaining deterministic safety, ordering, and offline fallback. Broader danger policies, real time/location/weather capture, profile/practice, and outbound approval remain tracked gaps.

## Progress: bounded AI interpretation and photo quality

Implemented structured scene/photo contracts, optional provider adapters, explicit per-session sharing controls, quoted scene proposals with confirmation, image assessment caching, two-rejection limits, preserved originals, and offline fallback. Reopening clears sharing consent. Deterministic safety and routing remain authoritative. AI usability status is not human or claim verification.

Validation uses mocked specialists without provider calls. Live provider compatibility and interactive Streamlit validation remain outstanding. Broader danger policies, actual incident context, profile/practice, and outbound approval remain tracked gaps.

## Progress: ElevenLabs voice input and output

Implemented optional REST speech synthesis/transcription adapters, Pydantic audio/configuration/transcript contracts, Streamlit recording and reviewed transcript submission, response playback with speech-rate support, per-browser consent, background requests, and stale-result invalidation. Existing workflow gates and timers remain authoritative. Audio is transient, not captured evidence. Opening/starting an incident resets voice consent.

Full-duplex streaming, barge-in, CLI microphone integration, live provider verification, and browser microphone/playback validation remain future work. Incident context capture remains the next planned functional milestone.
