"""Immutable interface response contracts."""

from .knowledge import SourcePassage
from pydantic import BaseModel, ConfigDict, Field

class Instruction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(min_length=1)
    expects: str | None = None
    terminate: bool = False
    reason: str | None = None
    speech_rate: float = Field(default=1.0, gt=0, le=1.0)
    citations: tuple[SourcePassage, ...] = ()
