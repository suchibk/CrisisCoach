from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field


class AISettings(BaseModel):
    """Validated configuration for an OpenAI-compatible AI provider."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    api_key: str
    base_url: str
    model: str
    timeout_seconds: float = Field(default=1.5, gt=0)

    @classmethod
    def from_environment(cls) -> AISettings | None:
        api_key = os.getenv("CRISIS_COACH_AI_API_KEY")
        base_url = os.getenv("CRISIS_COACH_AI_BASE_URL")
        model = os.getenv("CRISIS_COACH_AI_MODEL")
        if not api_key or not base_url or not model:
            return None
        return cls(api_key=api_key, base_url=base_url, model=model)
