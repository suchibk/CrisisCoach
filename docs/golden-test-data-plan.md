# GoldenTestData: UI and testing implementation plan

Reviewed 2026-09-11. The implementation is now complete for the executable scope described below; see [acceptance report](golden-acceptance-report.md) for delivered behavior, adapted expectations, tests, screenshots, and remaining manual/expert checks. The original assessment below is retained as planning context.

## Sources and findings

- `GoldenTestData/2026-09-10/crisis-coach-prototype.html`: standalone browser simulation, phone frame, dark/light palettes, conversation, camera/microphone controls, suggested utterances, decision timeline, and scene ledger.
- `GoldenTestData/Crisis Coach - Deployment and Test 2926-09-10.docx`: launch instructions and fourteen manual acceptance cases (T1-T14). Preserve the original filename and case IDs for traceability.
- `GoldenTestData/2026-09-10/READ-ME-FIRST.txt`, `start.command`, and `start.sh`: demo launch references.

The folder contains an executable visual reference and a manual script, not a fixture dataset of photographs, profiles, transcripts, or reviewed policy documents. The camera simulates success/failure. Knowledge answers are fabricated. The HTML initializes eight evidence items and fixed windows; these differ from the Python catalogue and its scenario applicability. Its scene windows change on signals; there is no continuous countdown loop.

The existing `feature-traceability.md` and `evals/README.md` lag the implementation. Reconcile these during the first work package rather than treating their Planned labels as current coverage.

## How to use the prototype for UI

Retain Streamlit for the next UI increment. Reuse the visual hierarchy, colors, spacing, and interaction examples through Streamlit views and scoped styles. Keep WorkflowEngine, typed events, and persisted SceneState authoritative. Do not embed a second browser workflow engine. A pixel-matched standalone frontend would be a separate architecture decision requiring an API adapter.

### Active incident view

- Prominent current instruction, concise conversation history, visible safety status, and accessible pause/resume/repeat controls.
- Context-sensitive photo upload/text capture and existing reviewed voice transcription/playback. Disable collection while paused, uncleared, or stood down.
- Compact progress with separate stored, reported-only, pending, and unavailable counts. Show a retake reason only when an actual assessment supplies it.
- Expandable incident context, source citations, and evidence-pack review/download. Label observations, synthetic sources, and AI usability assessments accurately.
- Responsive layout and keyboard-accessible controls, visible focus, readable contrast, and text labels alongside color. Offer light/dark appearance without fabricated clock, battery, rain, or location displays.

### Practice and demonstration view

- Persistent Practice label, isolated temporary repository, synthetic identities, and no outbound tools or provider calls by default.
- Suggested utterances from each test step, reset, and explicit scenario selection. Show deterministic camera/voice fakes as simulations.
- Optional phone frame/device appearance controls. The frame is a visual demo aid, not proof of device compatibility.
- A side panel inspired by “How this is unfolding” and “Scene state”: actual gate status, selected evidence, priority reason, estimated deadline, and evidence status.
- Derive the panel from SceneState, PlanningDecision, accepted events, and actual graph routes. Current last_route is transient; persistent decision history needs a presentation trace contract. Do not invent untaken branches or claim a planner was never consulted earlier in the incident.
- Estimates must remain estimates: an elapsed deadline does not establish actual driver/witness departure. Keep detailed arithmetic in the demo panel rather than the main crisis interaction.

### Profile and report views

The reference does not design these screens. Add profile/practice entry, active incident, and evidence-pack review as distinct views. Model vehicle/policy/trusted-contact details explicitly, with synthetic practice defaults kept separate from real saved incidents. Profile completion must not delay starting safety checks. A profile must not silently establish policy applicability. Report review must expose original statements, attachments, missing items, and export snapshot age. Delivery remains a later explicit approval workflow.

## T1-T14 acceptance mapping

This table preserves test intent while separating deliberate backend differences from missing work. Source-level review plus the text probes below is not a browser pass report.

| ID | Reference expectation | Current application / planned acceptance |
|---|---|---|
| T1 | Opening injury question, empty planner, opening timeline node | Engine opens with injury question. Add initial UI/timeline assertion; require no selected evidence before clearance, not verbatim prototype wording. |
| T2 | Negative injury answer advances first gate | Exact scripted input advances correctly in local replay. Add scenario and UI assertion. |
| T3 | Others unhurt advances second gate | Exact scripted input advances correctly in local replay. Add scenario and UI assertion. |
| T4 | Safe location starts with witness | Local replay starts with wide_scene_photo. Preserve current catalogue behavior; explicitly seed a departing witness when testing witness priority. Do not change ranking solely to mimic the demo. |
| T5 | 180/600/600-second chips, zero of eight captured | Prototype-specific fixture values. Derive counts and estimates from the active backend catalogue and injected clock; unknown deadlines stay unknown. No literal eight-item requirement. |
| T6 | Driver departure changes priority to plate at 45 seconds | Exact input selects other_plate locally; backend uses a 60-second estimate. Assert selection, preserved completed items, and no extension on repeated signals. Display explanation from PlanningDecision. |
| T7 | First camera click always rejected | Use an explicit fake reviewer returning a rejection and a real synthetic image fixture. Original attachment remains stored; show assessment reason. Production must never force the first capture to fail. |
| T8 | Next photo succeeds and advances | Use a second distinct fixture with a usable fake assessment. Verify retained original, status, progression, and attachment integrity. Repeated identical bytes should use cached assessment. |
| T9 | Apology triggers admission warning and replacement script | Local replay preserves current item but has no special warning. Replace the prototype's categorical legal claim with a reviewed neutral-response requirement; preserve original words and avoid determining liability. Track as pending output-guidance work. |
| T10 | Police answer uses fabricated private-land duty and repeats task | Local replay abstains without source context. Test missing-source abstention and separately opt into synthetic demo sources to test citations. Preserve current task/deadline and avoid generalizing fabricated rules. |
| T11 | Injury immediately stops collection and displays alert | Exact neck-pain input stands down locally. Test terminal response, no later tool calls, hidden capture controls, and accurate history. Existing state may retain the current item for recovery; UI must not present it as actionable. |
| T12 | Shouting triggers hostile-scene stand-down | Exact input currently leaves the engine active. Prioritize reviewed danger handling and regression coverage; do not copy the prototype's location-specific instruction without review. |
| T13 | All reachable evidence gives pack-ready summary with gaps | Use applicable catalogue counts, actual attachments, explicit gaps, and a successful DOCX export. Reported-only completion must not imply a verified pack. Keep later additions and fresh export snapshots available. |
| T14 | Device frame and theme switch | New presentation work. Automate viewport/theme checks; optional frame switching belongs in demo mode. Verify text readability, keyboard focus, overflow, and state preservation. |

## Test architecture and fixtures

1. Preserve the HTML and DOCX as immutable references. Create validated scenario records under `evals/scenarios/` with source case IDs, fixture/version, initial state, typed input steps, fake-clock advances, expected state changes, expected tool calls, and prohibited effects.
2. Implement one replay runner against WorkflowEngine, with injected monotonic and UTC clocks, temporary SQLite/attachment/export directories, fake specialists, and no network. Assert structured outcomes; reserve exact text comparisons for repeat behavior and specifically approved wording.
3. Add synthetic image fixtures (usable and rejected examples with fake assessments), original statements, source corpora, and profiles as their features become executable. Record provenance, expected results, and fixture hashes. Cover duplicate bytes, corrupt images, and missing files separately.
4. Extend Streamlit AppTest coverage for safety gates, controls, source forms, recovery, profile/practice isolation, and export availability. Add browser tests for layout, upload/download, themes, focus, and responsive behavior; browser audio/device compatibility requires separate manual checks with explicit consent.
5. Run the source script manually as a demonstration checklist, recording app revision, fixture version, environment, pass/fail/blocked, and screenshots where useful. Mark changed expectations explicitly; do not report all fourteen passing when a source requirement has been replaced.

Additional golden scenarios: Priya full collision, witness departure, driver departure; Marcus unattended damage; minor scuff; Dana injury and medical re-entry; hostility and fire-risk language; neutral handling of apology; silence deadlines; pause/repeat/resume; restart recovery; rejected/duplicate photos; missing sources; provider failure; context/export; and practice reset isolation. Several backend tests already cover these subsets; reuse them rather than duplicate their implementation assertions.

Track scenario pass rate, safety violations, calls attempted after stand-down, repeated completed-item requests, citation validity, stored-versus-reported correctness, and recovery consistency. Safety violations and unintended external calls fail the run. Report blocked scenarios separately so an incomplete danger-policy suite cannot appear green.

## Differences to resolve before adoption

- Do not copy the HTML regex guard, simulated verification, memory-only save claims, unconditional source answers, or liability/apology assertions into the application.
- The HTML loads Google Fonts, despite the document's blanket no-network claim. Its browser speech API usage alone does not establish local processing. Practice tests should block network, provide local/system fonts, and fake voice; make no offline/privacy claim beyond what is verified.
- The prototype claims pack assembly without constructing an actual document. Connect UI readiness to real export results.
- Browser-support statements in the package are historical assertions, not validated current compatibility results. Test the intended environments before updating support claims.
- The two launch scripts have different port handling; the README's document path differs from the actual packaged DOCX path. Correct instructions in new documentation without modifying the archived reference.

## Implementation sequence and completion criteria

1. Golden scenario baseline and requirement reconciliation: validated T1-T14 mapping, executable runner, source IDs, deterministic replay, and explicit blocked cases. Refresh feature traceability.
2. Danger/output-guidance gap: reviewed hostility/fire policies and neutral speech requirements; regression tests for affirmative, denied, quoted, and ambiguous language. This should precede a broader demo-ready claim.
3. UI foundation: split Streamlit into views; active-incident layout, status, controls, evidence summary, and readable responsive appearance. Require AppTest coverage plus browser review.
4. Profile and practice: persistent profile contracts, isolated practice repositories, scenario selector, fake providers, and actual decision/state panels. Require isolation/reset tests and no external calls.
5. End-to-end acceptance: run capture/review/export/recovery scenarios, compare UI to reference intent, perform voice/device checks, and publish a coverage report with remaining blocked requirements.

This adds detail to the existing profile/practice milestone and moves the demonstrated hostility gap ahead of UI acceptance. It does not require a second workflow engine or a new crisis domain to begin UI work.

## Validation performed for this review

Read the HTML, all DOCX tables including T1-T14, launch instructions, current Streamlit view, catalogue, safety rules, planner tests, and voice UI test. Ran in-memory WorkflowEngine text probes for T1-T4, T6, T9-T12 without provider calls or durable writes. Confirmed gates, plate reprioritization, absent apology handling, missing-context abstention, injury stand-down, and the hostility gap. No browser rendering, camera, microphone, or complete T1-T14 acceptance run was performed.
