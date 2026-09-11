from __future__ import annotations

from enum import StrEnum
from typing import Literal
from .trace import TurnTrace
from .profile import Profile

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .incident_context import IncidentContext
from .ai import SceneObservation
from .knowledge import KnowledgeContext, KnowledgeAnswer
from .reports import EvidencePackReference
from .evidence import EvidenceRecord, PlanningDecision
from pydantic import JsonValue
from .responses import Instruction  # Compatibility export.


class SafetyGate(StrEnum):
    USER_INJURY = "user_injury"
    OTHER_INJURY = "other_injury"
    SAFE_LOCATION = "safe_location"
    MEDICAL_REENTRY = "medical_reentry"
    DANGER_REENTRY = "danger_reentry"
    CLEARED = "cleared"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    STOOD_DOWN = "stood_down"
    STOPPED = "stopped"
    COMPLETE = "complete"


class SceneState(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    incident_id: str = Field(min_length=1)
    person_name: str = Field(min_length=1)
    practice_mode: bool = False
    status: SessionStatus = SessionStatus.ACTIVE
    safety_gate: SafetyGate | str = SafetyGate.USER_INJURY
    unanswered_safety_turns: int = Field(default=0, ge=0, strict=True)
    injury_reason: str | None = None
    stand_down_kind: Literal["injury", "fire", "hostility"] | None = None
    trace: tuple[TurnTrace, ...] = ()
    profile: Profile | None = None
    events: list[str] = Field(default_factory=list)
    evidence_requests: list[str] = Field(default_factory=list)

    ai_text_allowed: bool = False
    ai_images_allowed: bool = False
    pending_scene_changes: tuple[SceneObservation, ...] = ()
    incident_context: IncidentContext = Field(default_factory=IncidentContext)
    knowledge_context: KnowledgeContext = Field(default_factory=KnowledgeContext)
    knowledge_answers: tuple[KnowledgeAnswer, ...] = ()
    exports: tuple[EvidencePackReference, ...] = ()
    evidence: dict[str, EvidenceRecord] = Field(default_factory=dict)
    current_evidence_id: str | None = None
    evidence_catalogue_version: str | None = None
    domain_data: dict[str, JsonValue] = Field(default_factory=dict)
    last_decision: PlanningDecision | None = None
    last_instruction: Instruction | None = None
    timer_id: str | None = None
    timer_deadline: float | None = Field(default=None, allow_inf_nan=False)
    last_event_id: str | None = None
    revision: int = Field(default=0, ge=0, strict=True)
    domain_id: str = Field(default="collision", pattern=r"^[a-z][a-z0-9_]*$")
    pack_version: str = Field(default="1", min_length=1)

    @field_validator("safety_gate", mode="before")
    @classmethod
    def preserve_legacy_gate(cls, value):
        try:
            return SafetyGate(value)
        except ValueError:
            return value
