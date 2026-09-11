from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from .ai.contracts import AIInjuryAssessment, InjuryClassifier
from ...models import Instruction, SafetyGate, SceneState, SessionStatus


INJURY_PATTERNS = (
    r"\bhurt(?:s|ing)?\b",
    r"\bpain(?:ful)?\b",
    r"\bbleed(?:ing)?\b",
    r"\bunconscious\b",
    r"\bcan(?:no|')t breathe\b",
    r"\bdizz(?:y|iness)\b",
    r"\bnumb(?:ness)?\b",
    r"\bbroken (?:arm|leg|rib|bone|neck|back|wrist|ankle)\b",
)
NEGATIVE_PATTERNS = (
    r"^no(?:pe)?[.!?]?$",
    r"^no(?:pe)?,? (?:but |i(?: am|'m) |he(?: is|'s) |she(?: is|'s) |they |everyone )",
    r"\b(?:no (?:pain|injuries|injury|bleeding)|nobody (?:is )?hurt|no one (?:is )?hurt)\b",
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
    # Remove explicit symptom denials before detecting positive injury signals.
    injury_text = re.sub(r"\b(?:not hurt|no (?:pain|bleeding|injury|injuries)|nobody (?:is )?hurt|no one (?:is )?hurt)\b", "", normalized)
    if any(re.search(pattern, injury_text) for pattern in INJURY_PATTERNS):
        return SafetyVerdict(injury=True, reason=text.strip())
    if any(re.search(pattern, normalized) for pattern in AMBIGUOUS_PATTERNS):
        return SafetyVerdict(ambiguous=True, reason="uncertain answer")
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
            "I am not going to ask you anything else. This session is ending."
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
    normalized = " ".join(text.lower().replace("’", "'").strip().split())
    verdict = classify_safety(normalized)

    # Positive injury signals pre-empt re-entry and all collection states.
    if verdict.injury:
        return stand_down(state, text.strip() or "injury reported")

    if state.status is SessionStatus.STOOD_DOWN:
        already_asked = state.safety_gate is SafetyGate.MEDICAL_REENTRY
        state.safety_gate = SafetyGate.MEDICAL_REENTRY
        affirmative = bool(re.fullmatch(r"yes[.!]?", normalized) or re.match(r"^yes[, ]", normalized))
        explicit_check = bool(re.search(r"\b(?:doctor|paramedic|medic|nurse|hospital|medical)\b", normalized)) and bool(re.search(r"\b(?:checked|examined|assessed|cleared|seen)\b", normalized))
        denied = bool(re.search(r"\b(?:no|not|never|maybe|unsure)\b", normalized))
        if not already_asked or denied or not (affirmative or explicit_check):
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

    injury_gate = state.safety_gate in (SafetyGate.USER_INJURY, SafetyGate.OTHER_INJURY)
    if injury_gate and re.fullmatch(r"(?:yes|yeah|yep)[.!]?", normalized):
        return stand_down(state, "injury confirmed")

    if verdict.ambiguous and normalized and ai_classifier is not None:
        try:
            ai_result = ai_classifier.classify_injury(text)
            state.events.append(f"AI_INJURY_ASSESSMENT: {ai_result.assessment.value}")
            if ai_result.assessment is AIInjuryAssessment.INJURY:
                return stand_down(state, f"possible injury reported: {text.strip()}")
        except Exception as exc:
            state.events.append(f"AI_INJURY_CLASSIFIER_FAILED: {type(exc).__name__}")

    # Collection responses are not answers to an injury question.
    if state.safety_gate is SafetyGate.CLEARED:
        return None

    if state.safety_gate is SafetyGate.SAFE_LOCATION:
        safe = bool(re.fullmatch(r"(?:yes|yeah|yep)[.!]?", normalized) or re.match(r"^yes[, ]", normalized))
        unsafe_or_uncertain = bool(re.search(r"\b(?:no|not|never|maybe|unsure|traffic|road)\b", normalized))
        if safe and not unsafe_or_uncertain:
            state.safety_gate = SafetyGate.CLEARED
            state.unanswered_safety_turns = 0
            state.events.append("SAFETY_GATES_CLEARED")
            return None
        # A known unsafe location cannot be converted into clearance or evidence work.
        return Instruction(text="Are you somewhere safe to stand?", expects="yes_or_no", reason="safe location not confirmed")

    if verdict.ambiguous:
        state.unanswered_safety_turns += 1
        if state.unanswered_safety_turns >= 2:
            return stand_down(state, verdict.reason or "safety question unanswered")
        question = "Are you hurt anywhere?" if state.safety_gate is SafetyGate.USER_INJURY else "Is anyone else hurt?"
        return Instruction(text=question, expects="yes_or_no")

    state.unanswered_safety_turns = 0
    if state.safety_gate is SafetyGate.USER_INJURY:
        state.safety_gate = SafetyGate.OTHER_INJURY
        return Instruction(text="Is anyone else hurt? The other driver, a passenger, anyone on foot?", expects="yes_or_no")
    if state.safety_gate is SafetyGate.OTHER_INJURY:
        state.safety_gate = SafetyGate.SAFE_LOCATION
        return Instruction(text="Are you somewhere safe to stand?", expects="yes_or_no")
    raise RuntimeError("Unexpected active safety gate")
