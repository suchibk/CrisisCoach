from __future__ import annotations

from ....ai.config import AISettings
from ....ai.contracts import AIInjuryResult


class NebiusInjuryClassifier:
    """Nebius adapter using its OpenAI-compatible chat interface.

    Imports the optional LangChain dependency lazily so offline mode remains
    dependency-light.
    """

    def __init__(self, settings: AISettings) -> None:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError(
                'AI support is not installed; run: pip install -e ".[agent]"'
            ) from exc

        model = ChatOpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            model=settings.model,
            temperature=0,
            timeout=settings.timeout_seconds,
            max_retries=0,
        )
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
