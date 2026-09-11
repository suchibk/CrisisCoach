from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr, field_validator


class AISettings(BaseModel):
    """Validated configuration for an OpenAI-compatible AI provider."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    api_key: SecretStr
    base_url: HttpUrl
    model: str = Field(min_length=1)
    timeout_seconds: float = Field(default=1.5, gt=0, allow_inf_nan=False)

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("API key must not be blank")
        return value

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Model must not be blank")
        return value

    @classmethod
    def from_environment(cls) -> AISettings | None:
        api_key = os.getenv("CRISIS_COACH_AI_API_KEY")
        base_url = os.getenv("CRISIS_COACH_AI_BASE_URL")
        model = os.getenv("CRISIS_COACH_AI_MODEL")
        if not api_key or not base_url or not model:
            return None
        return cls(api_key=api_key, base_url=base_url, model=model)

    @classmethod
    def for_capability(cls, capability: str) -> AISettings | None:
        if capability not in ("scene", "vision"): raise ValueError("Unknown capability")
        key = os.getenv("CRISIS_COACH_AI_API_KEY")
        url = os.getenv("CRISIS_COACH_AI_BASE_URL")
        model = os.getenv(f"CRISIS_COACH_AI_{capability.upper()}_MODEL")
        if not all((key, url, model)): return None
        return cls(api_key=key, base_url=url, model=model)
