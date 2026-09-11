from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class AIInjuryAssessment(StrEnum):
    INJURY = "injury"
    NO_INJURY = "no_injury"
    UNCERTAIN = "uncertain"


class AIInjuryResult(BaseModel):
    """Validated structured output returned by an AI injury classifier."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    assessment: AIInjuryAssessment
    rationale: str | None = Field(default=None, max_length=300)


class InjuryClassifier(Protocol):
    """Optional classifier contract, kept independent of any AI vendor."""

    def classify_injury(self, text: str) -> AIInjuryResult: ...
