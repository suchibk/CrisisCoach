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


@pytest.mark.parametrize("overrides", [
    {"api_key": "   "}, {"base_url": "not-a-url"},
    {"base_url": "file:///tmp/model"}, {"model": "   "},
    {"timeout_seconds": float("inf")}, {"timeout_seconds": float("nan")},
])
def test_ai_settings_reject_invalid_provider_configuration(overrides) -> None:
    values = {"api_key": "private-token", "base_url": "https://example.test/v1", "model": "model"}
    values.update(overrides)
    with pytest.raises(ValidationError):
        AISettings.model_validate(values)


def test_ai_settings_hide_credentials_in_repr_and_json() -> None:
    settings = AISettings(api_key="private-token", base_url="https://example.test/v1", model="model")
    assert "private-token" not in repr(settings)
    assert "private-token" not in settings.model_dump_json()
    assert settings.api_key.get_secret_value() == "private-token"


def test_session_rejects_negative_safety_counter_on_assignment() -> None:
    from crisis_coach.models import SceneState
    state = SceneState(incident_id="incident", person_name="Dana")
    with pytest.raises(ValidationError):
        state.unanswered_safety_turns = -1


def test_instruction_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        Instruction(text="")
