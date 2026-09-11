import pytest
from pydantic import ValidationError

from crisis_coach.ai import AIInjuryAssessment, AIInjuryResult
from crisis_coach.ai.config import AISettings
from crisis_coach.models import Instruction


def test_ai_result_parses_enum_from_structured_output() -> None:
    result = AIInjuryResult.model_validate(
        {"assessment": "injury", "rationale": "Chest discomfort reported."}
    )

    assert result.assessment is AIInjuryAssessment.INJURY


def test_ai_settings_reject_invalid_timeout() -> None:
    with pytest.raises(ValidationError):
        AISettings(api_key="key", base_url="https://example.test/v1", model="model", timeout_seconds=0)


def test_instruction_is_immutable() -> None:
    instruction = Instruction(text="Are you hurt anywhere?")

    with pytest.raises(ValidationError):
        instruction.text = "Changed"
