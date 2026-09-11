"""Evidence contracts distinguish user reports from verified attachments."""
from datetime import datetime
from .ai import PhotoAssessment
from ..tools.contracts import AttachmentReference
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator

class EvidenceStatus(StrEnum):
    PENDING = "pending"
    REPORTED = "reported"
    COLLECTED = "collected"
    VERIFIED = "verified"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"

class EvidenceDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    item_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1)
    instruction: str = Field(min_length=1)
    expects: str
    value: int = Field(ge=1, le=5)
    scenarios: tuple[str, ...]
    requires_driver: bool = False
    requires_witness: bool = False

class EvidenceCatalogue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: str
    items: tuple[EvidenceDefinition, ...]

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [item.item_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate catalogue item ID")
        return self

class EvidenceRecord(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")
    item_id: str
    status: EvidenceStatus = EvidenceStatus.PENDING
    note: str | None = None
    attachments: tuple[AttachmentReference, ...] = ()
    original_text: str | None = None
    photo_reviews: dict[str, PhotoAssessment] = Field(default_factory=dict)
    failed_photo_reviews: int = Field(default=0, ge=0, le=2)
    estimated_deadline: AwareDatetime | None = None

class PriorityCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    item_id: str
    score: float = Field(ge=0, allow_inf_nan=False)
    value: int
    seconds_remaining: float | None = None
    reason: str

class PlanningDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    selected_id: str | None
    candidates: tuple[PriorityCandidate, ...]
