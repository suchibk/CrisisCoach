"""Compatibility exports; collision safety now lives in safety.py."""

from .safety import (AFFIRMATIVE_PATTERNS, AMBIGUOUS_PATTERNS, INJURY_PATTERNS, NEGATIVE_PATTERNS, SafetyVerdict, classify_safety, run_safety_guard, stand_down)

__all__ = ["AFFIRMATIVE_PATTERNS", "AMBIGUOUS_PATTERNS", "INJURY_PATTERNS", "NEGATIVE_PATTERNS", "SafetyVerdict", "classify_safety", "run_safety_guard", "stand_down"]
