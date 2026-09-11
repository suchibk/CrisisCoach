# Architecture and package boundaries

The target is one deterministic supervisor with bounded AI specialists and versioned domain packs. Implemented behavior includes collision safety, controls, timers, shared graph routing, and durable SQLite storage. Adaptive evidence collection and additional real domains remain planned.

- orchestration: shared graph, routing, planner, clock, and nodes.
- domains: domain contracts and registry; collision policy and resources. Other domains remain unavailable placeholders.
- models: typed state, responses, evidence, events, profiles, knowledge, and actions.
- ai: settings, provider adapters, and bounded interpretation, evidence, knowledge, and statement specialists.
- guardrails: shared approval, grounding, output, and disclosure rules.
- tools: typed actions through one executor; no direct specialist authorization.
- knowledge: ingestion, local retrieval, and optional Pinecone adapter.
- persistence: authoritative incident repository, checkpoints, attachments, and migrations.
- reporting: exact completeness and deterministic evidence-pack assembly.
- observability: local records and optional synthetic-only remote tracing.
- interfaces: CLI, Streamlit views, and optional voice adapters.
- bootstrap: constructs concrete dependencies.

Shared orchestration must depend on domain interfaces rather than collision rules. SceneState accepts domain-defined string gates and retains the original SafetyGate enum for compatibility. The collision state module re-exports that enum; the shared engine does not import collision rules.

Runtime databases, exports, and incident attachments belong in a configurable application-data directory outside the repository. SQLite incident persistence is implemented; graph checkpoints and attachment storage remain planned. Original requirements documents remain unchanged.

Planned leaf modules are created with real implementations, not empty executable stubs. README files preserve planned package and resource boundaries in version control.

## Pydantic conventions

Use Pydantic v2 models for configuration, domain resources, input events, state, tool arguments/results, source references, approval records, and AI structured outputs as these capabilities are implemented. Validate JSON at ingress with model_validate or model_validate_json; serialize with model_dump(mode="json") or model_dump_json. Reject unknown fields with extra="forbid".

Use frozen models for value contracts and validate_assignment for mutable session state. Frozen models are not deeply immutable: prefer tuples for immutable collections. Assignment validation does not validate in-place list mutations; introduce validated event/evidence methods with the ledger implementation. Constrain identifiers, counters, enums, and numeric ranges at the boundary.

Use SecretStr for credentials and validated HTTP URLs for provider endpoints. Unwrap secrets only at the provider boundary; never log them. Use Protocol for service interfaces and regular functions/classes for orchestration rather than forcing behavior into data models. Keep domain-specific models in their domain package.
