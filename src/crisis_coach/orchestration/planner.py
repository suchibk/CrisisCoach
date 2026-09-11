"""Pure deterministic priority calculation; no provider calls or scene mutation."""
from datetime import datetime
from ..models.evidence import EvidenceDefinition, EvidenceRecord, EvidenceStatus, PriorityCandidate, PlanningDecision

def rank_evidence(items: tuple[EvidenceDefinition, ...], records: dict[str, EvidenceRecord], now: datetime) -> PlanningDecision:
    if now.tzinfo is None:
        raise ValueError("Planner requires timezone-aware time")
    candidates = []
    for item in items:
        record = records[item.item_id]
        if record.status is not EvidenceStatus.PENDING:
            continue
        remaining = (record.estimated_deadline - now).total_seconds() if record.estimated_deadline else None
        denominator = max(1.0, remaining) if remaining is not None else 300.0
        candidates.append(PriorityCandidate(item_id=item.item_id, value=item.value,
            score=item.value / denominator, seconds_remaining=remaining,
            reason="Estimated capture window; availability not confirmed" if remaining is not None else "Routine collection; no reported departure"))
    # Stable sorting preserves catalogue order for equal scores.
    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    return PlanningDecision(selected_id=candidates[0].item_id if candidates else None, candidates=tuple(candidates))
