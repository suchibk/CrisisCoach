"""Exact passage provenance and applicability validation."""
from ..models.knowledge import SourcePassage, KnowledgeQuery, KnowledgeAnswer


def applicable(passage: SourcePassage, query: KnowledgeQuery) -> bool:
    context = query.context
    if not passage.reviewed or passage.corpus != query.corpus or query.topic not in passage.topics:
        return False
    if passage.synthetic and not context.allow_synthetic: return False
    if context.reference_date is None: return False
    if context.reference_date < passage.effective_from: return False
    if passage.effective_until and context.reference_date > passage.effective_until: return False
    if passage.policy_id and passage.policy_id != context.policy_id: return False
    if passage.jurisdiction and passage.jurisdiction != context.jurisdiction: return False
    return True


def validate_grounding(answer: KnowledgeAnswer, query: KnowledgeQuery, sources: tuple[SourcePassage, ...]) -> KnowledgeAnswer:
    by_id = {source.source_id: source for source in sources}
    for citation in answer.citations:
        if by_id.get(citation.source_id) != citation or not applicable(citation, query):
            raise ValueError("Citation is altered, unknown, or inapplicable")
    return answer
