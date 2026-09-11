"""Bounded AI outputs; no executable actions or free-form coaching."""
from typing import Literal, Protocol
from pydantic import BaseModel, ConfigDict, Field, model_validator

class SceneObservation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    signal: Literal["witness_leaving", "driver_leaving", "driver_left", "witness_left", "unattended", "scuff"]
    supporting_quote: str = Field(min_length=1, max_length=500)

class SceneInterpretation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    possible_injury: bool = False
    observations: tuple[SceneObservation, ...] = Field(default=(), max_length=3)

    @model_validator(mode="after")
    def consistent_observations(self):
        signals = [obs.signal for obs in self.observations]
        if len(signals) != len(set(signals)): raise ValueError("Duplicate observations")
        for pair in ({"driver_left", "driver_leaving"}, {"witness_left", "witness_leaving"}, {"scuff", "unattended"}):
            if pair.issubset(signals): raise ValueError("Conflicting observations")
        return self

class PhotoAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    verdict: Literal["usable", "retake", "uncertain"]
    issues: tuple[Literal["blur", "dark", "occluded", "wrong_subject", "unreadable"], ...] = ()

    @model_validator(mode="after")
    def consistent(self):
        if self.verdict == "usable" and self.issues: raise ValueError("Usable result cannot include quality defects")
        if self.verdict == "retake" and not self.issues: raise ValueError("Retake requires an identified defect")
        return self

class SceneInterpreter(Protocol):
    def interpret(self, text: str) -> SceneInterpretation: ...

class PhotoReviewer(Protocol):
    def review(self, data: bytes, media_type: str, goal: str) -> PhotoAssessment: ...
