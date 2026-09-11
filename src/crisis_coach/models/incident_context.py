"""User-supplied incident facts, separate from source lookup context."""
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

class IncidentContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    occurred_at: AwareDatetime | None = None
    location: str | None = Field(default=None, max_length=1000)
    weather: str | None = Field(default=None, max_length=1000)

    def safety_text(self) -> str:
        return "\n".join(value for value in (self.location, self.weather) if value)
