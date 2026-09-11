"""Typed incident persistence boundary."""
from typing import Protocol
from pydantic import BaseModel, ConfigDict
from ..models import SceneState, Instruction, SessionStatus
from ..models.events import InputEvent

class PersistenceError(RuntimeError):
    """An incident could not be safely read or committed."""

class ConcurrentUpdateError(PersistenceError):
    """The caller's incident revision is stale."""

class IncidentSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    incident_id: str
    person_name: str
    status: SessionStatus
    revision: int

class IncidentRepository(Protocol):
    def load(self, incident_id: str) -> SceneState: ...
    def list_incidents(self) -> list[IncidentSummary]: ...
    def has_event(self, incident_id: str, event_id: str) -> bool: ...
    def save(self, state: SceneState, event: InputEvent | None = None,
             response: Instruction | None = None) -> None: ...
