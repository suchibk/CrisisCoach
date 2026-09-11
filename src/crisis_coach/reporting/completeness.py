"""Exact catalogue coverage, separate from photo quality and claim readiness."""
from pydantic import BaseModel, ConfigDict, computed_field
from ..models.evidence import EvidenceDefinition, EvidenceRecord, EvidenceStatus

class CompletenessItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    item_id: str
    label: str
    status: EvidenceStatus
    stored: bool
    problem: str | None = None

class CompletenessReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[CompletenessItem, ...]

    @computed_field
    @property
    def required_count(self) -> int: return len(self.items)
    @computed_field
    @property
    def stored_count(self) -> int: return sum(item.stored for item in self.items)
    @computed_field
    @property
    def reported_only_count(self) -> int:
        return sum(item.status is EvidenceStatus.REPORTED and not item.stored for item in self.items)
    @computed_field
    @property
    def missing_count(self) -> int: return self.required_count - self.stored_count
    @computed_field
    @property
    def stored_percent(self) -> float:
        return round(100 * self.stored_count / self.required_count, 1) if self.required_count else 0.0


def calculate_completeness(items: tuple[EvidenceDefinition, ...], records: dict[str, EvidenceRecord], problems: dict[str, str] | None = None) -> CompletenessReport:
    problems = problems or {}
    rows = []
    for definition in items:
        record = records.get(definition.item_id, EvidenceRecord(item_id=definition.item_id))
        problem = problems.get(definition.item_id)
        stored = bool(record.attachments) and record.status in (EvidenceStatus.COLLECTED, EvidenceStatus.VERIFIED) and not problem
        if not stored and problem is None:
            problem = record.note if record.status in (EvidenceStatus.FAILED, EvidenceStatus.UNAVAILABLE) else "No stored attachment; user reports do not count as stored evidence"
        rows.append(CompletenessItem(item_id=definition.item_id, label=definition.label, status=record.status, stored=stored, problem=problem))
    return CompletenessReport(items=tuple(rows))
