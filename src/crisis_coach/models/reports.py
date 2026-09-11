"""Durable reference to a generated local evidence pack."""
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime

class EvidencePackReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    relative_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    incident_revision: int = Field(ge=0)
    generated_at: AwareDatetime
    stored_items: int = Field(ge=0)
    required_items: int = Field(ge=0)
    problems: tuple[str, ...] = ()
