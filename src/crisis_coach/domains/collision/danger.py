"""Bounded local danger rules; see resources/danger-policy.md for scope."""
import re
from ...models import Instruction, SessionStatus, SafetyGate


def danger_kind(text: str) -> str | None:
    text = text.lower().replace("’", "'")
    # Hypothetical training questions are not present-scene assertions. A later
    # sentence or contrast remains eligible for detection.
    clauses = re.split(r"[.!?;\n]|\bbut\b", text)
    found = None
    for clause in clauses:
        if re.match(r"\s*(?:what if|what happens if|suppose|in (?:a|the) (?:demo|example)|if )", clause):
            continue
        clean = re.sub(r"\b(?:not|isn't|aren't|wasn't|no longer)\s+(?:shouting|yelling|threatening|violent|on fire|burning)(?:\s+at me)?", "", clause)
        clean = re.sub(r"\bno\s+(?:fire|smoke|fuel leak|petrol leak|threats?)\b", "", clean)
        if re.search(r"\b(?:on fire|(?:car|vehicle|engine) (?:is )?burning|smoke (?:is )?(?:coming )?from|(?:fuel|petrol|gasoline) (?:is )?leaking|(?:fuel|petrol) leak)\b", clean):
            return "fire"
        if re.search(r"\b(?:(?:shouting|yelling) at (?:me|us)|threaten(?:ing|s|ed) (?:me|us)|(?:he|she|they|driver) (?:is |are |being )?violent|(?:scared|afraid) for (?:my|our) safety)\b", clean):
            found = "hostility"
    return found


def danger_stop(state, kind: str, text: str) -> Instruction:
    state.status = SessionStatus.STOOD_DOWN
    if state.stand_down_kind != "injury":
        state.stand_down_kind = kind
    state.injury_reason = text
    state.events.append(f"DANGER_STAND_DOWN: {kind}")
    if kind == "fire":
        message = "Stop collecting evidence. Move away from the vehicle and traffic. Call 911 from a safe place and follow the dispatcher's instructions. Do not return to a burning vehicle."
    else:
        message = "Stop collecting evidence and avoid confronting the other person. If you are in immediate danger, call 911 and follow the dispatcher's instructions."
    return Instruction(text=message, terminate=True, reason=kind)


def danger_recovery(state, text: str = "") -> Instruction:
    asked = state.safety_gate == SafetyGate.DANGER_REENTRY
    state.safety_gate = SafetyGate.DANGER_REENTRY
    # No generic 'resume', 'yes', or restart can clear this stand-down.
    if asked and text.lower().strip().rstrip('.!') == "i am away from the danger and safe now":
        state.status = SessionStatus.ACTIVE
        state.stand_down_kind = None
        state.safety_gate = SafetyGate.USER_INJURY
        state.unanswered_safety_turns = 0
        return Instruction(text="Are you hurt anywhere?", expects="yes_or_no")
    return Instruction(text="Collection remains stopped. Only when you are away from the danger, say: 'I am away from the danger and safe now'. We will then restart the safety checks.", expects="danger_clearance")
