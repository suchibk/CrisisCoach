# Local knowledge

The JSON loader validates SourceCorpus and SourcePassage models, then caches the corpus in memory for the workflow lifetime. Optional CRISIS_COACH_KNOWLEDGE_DIR selects a local directory; otherwise bundled synthetic demo records are used. Invalid, missing, or duplicate-ID corpora disable lookup without blocking the safety workflow. URLs in provenance are never fetched.

LocalKnowledgeRetriever filters by topic, corpus, reviewed flag, policy ID, jurisdiction, reference date, and explicit synthetic opt-in. It returns matching passages verbatim, including all matches rather than resolving contradictions. This is conservative topic retrieval, not semantic search or a determination of legal applicability. No model or network call is involved.

Grounding validates that each citation exactly matches an applicable source record. Answers retain their source snapshots in SQLite and evidence packs. No real policy or legal corpus is bundled. Setting reviewed=true records the corpus maintainer's review; it does not perform legal validation automatically.
