# Demo presentation notes: implemented agentic concepts

## Opening description (30 seconds)

> Crisis Coach is a stateful collision-support prototype. It checks safety before it plans or uses tools, adapts evidence priorities as the scene changes, and retains incident history. ElevenLabs adds spoken instructions and reviewed voice input. Local knowledge lookup provides source-backed passages, while optional AI specialists can interpret scene descriptions or review photos. The workflow controls transitions, and automated evaluations check that safety restrictions hold.

## What we can accurately claim

| Concept | Implementation and source | What to say |
| --- | --- | --- |
| Stateful orchestration | Explicit conditional routes in [TurnGraph](../src/crisis_coach/orchestration/graph.py); local runner or optional LangGraph backend. | Every input passes through the same safety and workflow gates. |
| Adaptive planning | [Evidence ranking](../src/crisis_coach/orchestration/planner.py) uses evidence value and estimated time remaining. | A departing witness can change what we collect next. Planning here is deterministic. |
| Tool execution | Validated registry/executor for capture_photo, record_statement, check_policy, and assess_duties; see [tools](../src/crisis_coach/tools/README.md) and [knowledge tools](../src/crisis_coach/tools/knowledge.py). | Tools run only through permitted workflow routes with validated arguments. |
| Grounded retrieval | [Local retriever](../src/crisis_coach/knowledge/README.md) filters applicable passages and validates exact citations; snapshots persist with answers. | We retrieve and cite local sources rather than invent missing policy details. This is not vector search or LLM-generated RAG. |
| Human-in-the-loop | Reviewed transcript submission, opt-in external calls, and confirmation of AI scene suggestions. | Hearing speech does not silently submit a safety answer. |
| Memory | SQLite incidents, profile snapshots, evidence references, and recovery. | Reopening remembers restrictions and evidence; this is persisted application state, not model memory. |
| Safety guardrails | Injury pre-emption, uncertainty stand-down, gated collection, and medical re-entry handling. | Safety rules take precedence over planning and optional AI. These rules are prototype behavior, not a claim of clinical validation. |
| Voice integration | ElevenLabs synthesis and transcription, cached response audio, optional automatic playback. | Real provider speech is integrated with the same text workflow. |
| Optional AI specialists | Injury classifier, structured scene interpreter, and structured photo reviewer. | Models assist bounded tasks when configured; they cannot override safety clearance. |
| Evals | [Golden suite](../evals/README.md), regression tests, tool/state assertions, optional browser acceptance. | We test routing and side effects, not just whether an answer sounds plausible. |

The standard ElevenLabs demo runs without an LLM key. Do not describe its rule-based responses as live LLM reasoning. Specialist modules are not a demonstrated autonomous multi-agent team. Pinecone/vector RAG, insurer submission, and continuous hands-free conversation are not implemented demo capabilities. Installing a dependency does not prove an integration exists.

## Suggested five-minute walkthrough

1. **Set the scene:** Dana has had a minor collision. All demo details are synthetic. Introduce the opening description before starting the live incident so safety timers are not running during narration.
2. **Voice happy path:** show one generated response playing, then a recorded and reviewed answer. Complete No / No / Yes for safety. Say: "Voice is an interface; the same guarded workflow handles typed and reviewed spoken answers."
3. **Tool use:** upload a synthetic photo via the active capture control. Say: "This saves actual evidence; a verbal claim that a photo was taken is recorded separately."
4. **Uncertainty:** start a new incident and use I'm not sure / I don't know. Show collection stopping, reopen, and answer No. Say: "The coach acknowledges the answer and preserves the safety restriction. It does not guess clearance."
5. **Validation:** show the readiness JSON from the smoke script. Say: "These checks cover safety, tools, retrieval, recovery, and voice wiring with simulated providers. The audio you heard is a separate real-provider check."

Pause between sections when the session permits it. Eight-second safety timers make long explanations during questions unreliable. Use the [illustrated walkthrough](../demo/README.md) for the exact controls.

## Optional knowledge demonstration

After clearing safety with No / No / Yes, submit `/knowledge-demo`, then ask `How long do I have to notify my insurer?`. The bundled synthetic source should produce a labelled demo passage with a citation (the fixture includes section 7.2 and 24 hours). Say: "This is a synthetic policy record illustrating retrieval and citation, not Dana's actual insurance terms."

On a separate fresh, safety-cleared incident without knowledge context, ask `/ask What is my excess?`. The app should avoid inventing an answer. This demonstrates source applicability and abstention. It does not demonstrate embeddings, a vector database, or generative synthesis.

## Optional LangGraph and specialist discussion

The local runner is the default. To actually demonstrate LangGraph, install `.[agent]`, set `CRISIS_COACH_GRAPH_BACKEND=langgraph`, restart, and run the LangGraph golden evaluation from the eval guide. Simply showing the graph architecture does not mean LangGraph was active in the voice demo.

Scene and vision specialists need their respective `CRISIS_COACH_AI_SCENE_MODEL` / `CRISIS_COACH_AI_VISION_MODEL`, the shared API base URL/key, and UI opt-in. The injury classifier uses `CRISIS_COACH_AI_MODEL`. Treat these as optional configured extensions unless you have verified live calls beforehand.

## Closing description

> This demo shows bounded agency: a persistent workflow chooses the next permitted action, uses validated tools, cites applicable local knowledge, and requires human confirmation where needed. Voice makes that workflow accessible, and evaluations check its behavior across happy, uncertain, and recovery paths.
