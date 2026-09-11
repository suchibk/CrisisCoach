"""Offline topic retrieval returning passages, never inferred advice."""
from ..models.knowledge import SourceCorpus, KnowledgeQuery, KnowledgeAnswer
from ..guardrails.grounding import applicable, validate_grounding

class LocalKnowledgeRetriever:
    def __init__(self, corpus: SourceCorpus, unavailable: bool = False):
        self.corpus = corpus
        self.unavailable = unavailable

    def retrieve(self, query: KnowledgeQuery) -> KnowledgeAnswer:
        def missing(message): return KnowledgeAnswer(question=query.question, status="not_found", message=message)
        if self.unavailable: return missing("Local sources could not be loaded. No policy or duty answer is available.")
        if query.context.reference_date is None:
            return missing("Select the incident reference date before looking up policy or duty passages.")
        if query.corpus == "policy" and not query.context.policy_id:
            return missing("Select the applicable policy before looking up its passages.")
        if query.corpus == "duties" and not query.context.jurisdiction:
            return missing("Select the incident jurisdiction before looking up duty passages.")
        matches = tuple(sorted((p for p in self.corpus.passages if applicable(p, query)), key=lambda p: p.source_id))
        if not matches: return missing("No reviewed source passage matches this topic, context, and date. I cannot establish the requirement.")
        # Present all relevant passages without silently choosing among conflicts.
        answer = KnowledgeAnswer(question=query.question, status="found",
            message="Matching source passages (not a determination of how they apply):", citations=matches)
        return validate_grounding(answer, query, self.corpus.passages)
