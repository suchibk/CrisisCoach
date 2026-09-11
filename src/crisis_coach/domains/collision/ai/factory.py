from __future__ import annotations

from ....ai.config import AISettings
from ....ai.contracts import InjuryClassifier


def build_optional_injury_classifier() -> InjuryClassifier | None:
    """Build the configured AI adapter, or return None for offline mode."""
    settings = AISettings.from_environment()
    if settings is None:
        return None

    from .injury_classifier import NebiusInjuryClassifier

    return NebiusInjuryClassifier(settings)
