"""Validated tool metadata, inputs, context, and results."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class ToolSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str = Field(min_length=1)
    requires_approval: bool = False
    external: bool = False

class FileCaptureArgs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_path: str = Field(min_length=1)

class StatementArgs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    text: str = Field(min_length=1, max_length=20000)

    @model_validator(mode="after")
    def nonblank(self):
        if not self.text.strip(): raise ValueError("Statement must not be blank")
        return self

class ToolContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    incident_id: str
    event_id: str

class AttachmentReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    relative_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)
    media_type: Literal["image/jpeg", "image/png", "text/plain"]

class CaptureResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    attachment: AttachmentReference
    original_text: str | None = None

class ToolError(RuntimeError): pass
class ApprovalRequired(ToolError): pass
