from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SessionStatus(StrEnum):
    ACTIVE = "active"
    STOOD_DOWN = "stood_down"
    STOPPED = "stopped"
    COMPLETE = "complete"


class SafetyGate(StrEnum):
    USER_INJURY = "user_injury"
    OTHER_INJURY = "other_injury"
    SAFE_LOCATION = "safe_location"
    MEDICAL_REENTRY = "medical_reentry"
    CLEARED = "cleared"


class SceneState(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    incident_id: str
    person_name: str
    status: SessionStatus = SessionStatus.ACTIVE
    safety_gate: SafetyGate = SafetyGate.USER_INJURY
    unanswered_safety_turns: int = 0
    injury_reason: str | None = None
    events: list[str] = Field(default_factory=list)
    evidence_requests: list[str] = Field(default_factory=list)


class Instruction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    expects: str | None = None
    terminate: bool = False
    reason: str | None = None
