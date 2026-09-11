from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from ...ai import AIInjuryAssessment, InjuryClassifier
from ...models import Instruction, SafetyGate, SceneState, SessionStatus


INJURY_PATTERNS = (
    r"\bhurt(?:s|ing)?\b",
    r"\bpain(?:ful)?\b",
    r"\bbleed(?:ing)?\b",
    r"\bunconscious\b",
    r"\bcan(?:no|')t breathe\b",
    r"\bdizz(?:y|iness)\b",
    r"\bnumb(?:ness)?\b",
    r"\bbroken\b",
)
NEGATIVE_PATTERNS = (
    r"\bno(?:pe)?\b",
    r"\bnot hurt\b",
    r"\b(?:i(?:'m| am)|everyone(?:'s| is)|they(?:'re| are)|he(?:'s| is)|she(?:'s| is)) (?:fine|okay|ok|unhurt)\b",
)
AMBIGUOUS_PATTERNS = (r"\bi don(?:'t| not) know\b", r"\bnot sure\b", r"\bmaybe\b")
AFFIRMATIVE_PATTERNS = (r"\byes\b", r"\bchecked\b", r"\bcleared\b", r"\bseen by\b")


class SafetyVerdict(BaseModel):
    """Validated result of deterministic safety classification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    injury: bool = False
    clear: bool = False
    ambiguous: bool = False
    reason: str | None = None


def classify_safety(text: str) -> SafetyVerdict:
    normalized = " ".join(text.lower().strip().split())
    if not normalized:
        return SafetyVerdict(ambiguous=True, reason="no answer")
    if any(re.search(pattern, normalized) for pattern in AMBIGUOUS_PATTERNS):
        return SafetyVerdict(ambiguous=True, reason="uncertain answer")
    injury_text = re.sub(r"\bnot hurt\b", "", normalized)
    if any(re.search(pattern, injury_text) for pattern in INJURY_PATTERNS):
        return SafetyVerdict(injury=True, reason=text.strip())
    if any(re.search(pattern, normalized) for pattern in NEGATIVE_PATTERNS):
        return SafetyVerdict(clear=True)
    return SafetyVerdict(ambiguous=True, reason="injury status not established")


def stand_down(state: SceneState, reason: str) -> Instruction:
    state.status = SessionStatus.STOOD_DOWN
    state.injury_reason = reason
    state.events.append(f"SAFETY_STAND_DOWN: {reason}")
    detail = (
        "chest pain after a seatbelt"
        if re.search(r"\b(chest|seatbelt|seat belt)\b", reason, re.IGNORECASE)
        else "that someone may be hurt after a collision"
    )
    return Instruction(
        text=(
            f"Stop. Hang up and call 911 now, and tell them {detail}. "
            "I am not going to ask you anything else. Everything so far is saved."
        ),
        terminate=True,
        reason=reason,
    )


def run_safety_guard(
    state: SceneState,
    text: str,
    ai_classifier: InjuryClassifier | None = None,
) -> Instruction | None:
    """Run before planning. Returning None is the only route to non-safety work."""
    if state.status is SessionStatus.STOOD_DOWN:
        state.safety_gate = SafetyGate.MEDICAL_REENTRY
        normalized = " ".join(text.lower().strip().split())
        medically_cleared = any(
            re.search(pattern, normalized) for pattern in AFFIRMATIVE_PATTERNS
        ) and not re.search(r"\b(no|not|never)\b", normalized)
        if not medically_cleared:
            return Instruction(
                text="Before anything else - has someone medical checked you?",
                expects="yes_or_no",
                reason="medical clearance required after stand-down",
            )
        state.status = SessionStatus.ACTIVE
        state.safety_gate = SafetyGate.USER_INJURY
        state.unanswered_safety_turns = 0
        state.events.append("MEDICAL_REENTRY_CLEARED")
        return Instruction(text="Are you hurt anywhere?", expects="yes_or_no")

    if state.status is not SessionStatus.ACTIVE:
        return Instruction(text="This session is not active.", terminate=True)

    verdict = classify_safety(text)
    if verdict.injury:
        return stand_down(state, verdict.reason or "injury reported")

    if verdict.ambiguous and text.strip() and ai_classifier is not None:
        try:
            ai_result = ai_classifier.classify_injury(text)
            state.events.append(
                f"AI_INJURY_ASSESSMENT: {ai_result.assessment.value}"
            )
            if ai_result.assessment is AIInjuryAssessment.INJURY:
                return stand_down(state, f"possible injury reported: {text.strip()}")
        except Exception as exc:
            state.events.append(f"AI_INJURY_CLASSIFIER_FAILED: {type(exc).__name__}")

    if verdict.ambiguous:
        state.unanswered_safety_turns += 1
        if state.unanswered_safety_turns >= 2:
            return stand_down(state, verdict.reason or "safety question unanswered")
        if state.safety_gate is SafetyGate.USER_INJURY:
            return Instruction(text="Are you hurt anywhere?", expects="yes_or_no")
        return Instruction(text="Is anyone else hurt?", expects="yes_or_no")

    state.unanswered_safety_turns = 0
    if state.safety_gate is SafetyGate.USER_INJURY:
        state.safety_gate = SafetyGate.OTHER_INJURY
        return Instruction(
            text="Is anyone else hurt? The other driver, a passenger, anyone on foot?",
            expects="yes_or_no",
        )
    if state.safety_gate is SafetyGate.OTHER_INJURY:
        state.safety_gate = SafetyGate.SAFE_LOCATION
        return Instruction(text="Are you somewhere safe to stand?", expects="yes_or_no")
    if state.safety_gate is SafetyGate.SAFE_LOCATION:
        state.safety_gate = SafetyGate.CLEARED
        state.events.append("SAFETY_GATES_CLEARED")
        return None
    return None
