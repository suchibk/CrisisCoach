# GoldenTestData implementation and acceptance

Validated 2026-09-11 on Windows, Python 3.14, Pydantic 2.13.5, Streamlit 1.63.0, LangGraph 1.2.11, and Playwright 1.62.0/Chromium 151. Changes are in the working tree; no commit or deployment was made.

## Delivered

- Validated golden scenario runner, synthetic PNG fixtures with hashes, fake clock/reviewer, tool-call audit, and source-case mapping.
- Bounded hostility/fire stops, danger-specific re-entry, preserved injury precedence, and a neutral apology response. Safety-source rationale is in [danger policy](../src/crisis_coach/domains/collision/resources/danger-policy.md). Independent domain-expert review is still required before calling the policy broadly validated.
- Streamlit Incident, Evidence pack, and Profile views, visible safety/current-task controls, stored/reported/gap counts, original text/photo review, and local dark/light styles.
- Isolated Practice mode with scenario selection, suggested utterances, explicit simulated photo outcomes, manually advanced timers, and actual persisted graph traces/priority data.
- Optional local profile with conflict detection and snapshots in new incidents. Profile context never silently becomes source applicability. Practice uses synthetic profiles and does not read/update the saved personal profile.
- Practice exports contain a prominent synthetic/simulation label. Live incident recovery rechecks safety when returning from practice.

## Results

| Check | Result | Evidence |
|---|---|---|
| Full unit/integration/UI suite | 174 passed; 1 opt-in browser test skipped in this run | [pytest XML](../evals/results/pytest.xml) |
| Chromium end-to-end browser suite | 1 passed, run separately | [browser XML](../evals/results/browser.xml) |
| Golden scenario replay, local backend | 14 passed, 0 failed | [local results](../evals/results/golden.json) |
| Golden scenario replay, LangGraph backend | 14 passed, 0 failed | [LangGraph results](../evals/results/golden-langgraph.json) |
| Installed wheel smoke test | Imports, fixtures, safety resource, migrations, capture and DOCX export passed | [package results](../evals/results/package.json) |

Golden tests block network calls. Browser requests outside the test's localhost server are blocked and asserted absent. The browser flow checks a real upload and a downloadable DOCX containing the original account, not merely a success message. Screenshot review led to stronger caption contrast, bounded conversation/trace panels, and testing the collapsed sidebar at mobile width. Keyboard focus and absence of horizontal page overflow are checked. These are targeted checks, not a comprehensive accessibility audit.

## Source-case outcomes

| Cases | Implemented acceptance |
|---|---|
| T1-T3 | Injury gates before any collection; current task and trace reflect the engine |
| T4-T5 | Applicable catalogue/estimated deadlines shown; original fixed eight-item count and witness-first assumption are not copied |
| T6 | Driver signal reprioritizes plate; backend uses its existing 60-second estimate rather than the demo's 45 seconds |
| T7-T8 | Explicit simulated rejected/usable fixture outcomes; real attachments retained and assessment cached |
| T9 | Neutral response preserves task and original account; no categorical admission-of-liability assertion |
| T10 | Missing-source abstention plus separately enabled synthetic citations; no fabricated private-land rule presented as real |
| T11 | Injury stops collection, tools and timers; UI hides actionable capture |
| T12 | Directed hostility stops collection; explicit danger re-entry then full safety gates |
| T13 | Actual applicable attachments/original account exported; gaps and practice status labelled; reopen preserves snapshot |
| T14 | Dark/light theme and responsive 1440px/390px layouts checked; decorative iPhone/Android frames were optional and are not implemented |

The fourteen executable scenarios are not a claim that the original fourteen rows were accepted verbatim. The mapping above documents deliberate differences.

## Screenshots

- [Desktop, dark](../evals/results/ui/practice-desktop-dark.png)
- [Desktop, light](../evals/results/ui/practice-desktop-light.png)
- [Mobile-width, light](../evals/results/ui/practice-mobile-light.png)
- [Hostility stand-down](../evals/results/ui/hostility-stand-down.png)

## Remaining checks and scope

Real microphone/playback, native iPhone/Android behavior, live AI/voice provider compatibility, and independent safety/domain review remain pending. No incident data was sent to providers during this work. Prototype advice/corpus text was not adopted as validated legal guidance. Automatic location/weather services, AI statement drafting, approved outbound delivery, and a reviewed second domain remain future milestones.

A practice session's trace retains the latest 100 accepted turns for display, while the incident event ledger remains the persistence record. Estimated departure windows are never treated as proof that someone has left. Stored-file counts include retained retakes and are distinct from export completeness or verification.
