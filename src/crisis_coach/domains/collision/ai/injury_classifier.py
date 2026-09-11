from __future__ import annotations

from ....ai.config import AISettings
from .contracts import AIInjuryResult
from ....ai.providers.nebius import build_chat_model


class NebiusInjuryClassifier:
    """Nebius adapter using its OpenAI-compatible chat interface.

    Imports the optional LangChain dependency lazily so offline mode remains
    dependency-light.
    """

    def __init__(self, settings: AISettings) -> None:
        model = build_chat_model(settings)
        self._classifier = model.with_structured_output(AIInjuryResult)

    def classify_injury(self, text: str) -> AIInjuryResult:
        result = self._classifier.invoke(
            [
                (
                    "system",
                    "Classify whether the speaker reports that anyone may be injured "
                    "after a car collision. Use injury if harm is possible, uncertain "
                    "if unclear, and no_injury only for an explicit denial.",
                ),
                ("human", text),
            ]
        )
        return AIInjuryResult.model_validate(result)
