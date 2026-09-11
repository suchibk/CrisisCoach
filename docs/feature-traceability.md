# Feature traceability

Updated after GoldenTestData implementation, 2026-09-11. Implemented means executable prototype behavior, not production or domain-expert validation. See [acceptance report](golden-acceptance-report.md).

| ID | Feature | Ownership | Status |
|---|---|---|---|
| 1 | Profile: vehicle and policy | models/profile; persistence/profiles; views/profile | Implemented; optional local profile and incident snapshot |
| 2 | Trusted contact | models/profile; views/profile | Stored; no contact/delivery action |
| 3 | Practice | practice/runtime; views/practice | Implemented; isolated storage, synthetic profiles and local fakes |
| 4 | Fast start | interfaces/streamlit_app | Implemented; safety starts without profile completion |
| 5 | Safety first | collision/safety; collision/danger | Implemented bounded rules; broader expert-reviewed language coverage pending |
| 6 | One instruction | models/responses; views/incident | Implemented prominent current task and separate history |
| 7 | Repeat and slow down | orchestration; interfaces/voice | Implemented controls and optional playback metadata |
| 8 | Adaptive ordering | orchestration/planner; collision/rules | Implemented and golden-tested |
| 9 | Mid-scene questions | knowledge; orchestration/engine | Implemented source lookup/abstention preserving task |
| 10 | Reviewed speech guidance | collision/danger; orchestration/graph | Neutral apology response implemented; independent policy review pending |
| 11 | Photo instructions | collision resources; tools/capture | Implemented with real local upload |
| 12 | Photo quality | ai/specialists; practice/runtime | Optional bounded reviewer; fake-based tests, live quality validation pending |
| 13 | Party details | tools/capture; models/evidence | Verbatim text capture; OCR/extraction pending |
| 14 | Original account | tools/capture; persistence | Implemented verbatim storage and review |
| 15 | Time place weather | models/incident_context; views/collection | User-provided capture implemented; automatic integrations pending |
| 16 | Missing items | reporting/completeness; views/report | Implemented with applicable catalogue counts |
| 17 | Sourced duties | knowledge; guardrails/grounding | Retrieval implemented; bundled sources are synthetic, production source review pending |
| 18 | Immediate stand-down | collision/safety; collision/danger | Injury, directed hostility, and bounded fire rules implemented |
| 19 | Stop | orchestration; views/incident | Implemented pause/resume with gates preserved |
| 20 | Evidence file | reporting/evidence_pack | Real local DOCX export implemented |
| 21 | Honest gaps | reporting/completeness | Implemented; reports distinct from stored/verified evidence |
| 22 | Statement draft | ai/specialists/statement_writer | Pending; only original text is stored/exported |
| 23 | Next steps | knowledge; reporting | Partial; source passages and export review, no comprehensive next-step plan |
| 24 | Approved sending | guardrails/approvals; tools/delivery | Pending; external tools remain blocked |
| 25 | Later additions | persistence; orchestration | Implemented same-incident additions and fresh export snapshots |
| 26 | Sources | models/knowledge; guardrails/grounding | Implemented citation/context contracts and export inclusion |
| 27 | Ordering explanation | models/trace; views/practice | Implemented actual graph trace and priority comparison |
| 28 | Local data | persistence | SQLite, attachments, exports and profile; storage is not encrypted |
| 29 | Offline operation | practice; knowledge/local; orchestration | Local engine/golden runs need no provider; voice/AI remain optional |
| 30 | Domain choice | domains/registry | Only collision exposed; reviewed second domain pending |
