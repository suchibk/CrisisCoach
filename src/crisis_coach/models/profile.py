"""Optional personal preparation, never a safety or source-applicability gate."""
from pydantic import BaseModel, ConfigDict, Field

class Profile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str = Field(default="", max_length=120)
    vehicle: str = Field(default="", max_length=200)
    registration: str = Field(default="", max_length=40)
    policy_id: str = Field(default="", max_length=120)
    insurer: str = Field(default="", max_length=120)
    trusted_contact: str = Field(default="", max_length=120)
    contact_phone: str = Field(default="", max_length=80)
    revision: int = Field(default=0, ge=0, strict=True)
