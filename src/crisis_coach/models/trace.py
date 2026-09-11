"""Persisted presentation trace derived from accepted workflow execution."""
from pydantic import BaseModel, ConfigDict

class TurnTrace(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    event_id: str
    event_kind: str
    route: tuple[str, ...]
    status: str
    gate: str
    selected_id: str | None = None
    response: str | None = None
