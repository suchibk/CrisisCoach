import pytest

from crisis_coach import CollisionWorkflow, SessionStatus
from crisis_coach.models import SafetyGate
from crisis_coach.domains.collision.safety import classify_safety


def reach_location():
    coach = CollisionWorkflow()
    state, _ = coach.start()
    coach.turn(state, "No")
    coach.turn(state, "No")
    assert state.safety_gate is SafetyGate.SAFE_LOCATION
    return coach, state


@pytest.mark.parametrize("text", ["Yes", "Maybe, my chest hurts", "Not sure, he is bleeding"])
def test_injury_stops_in_same_turn(text):
    coach = CollisionWorkflow()
    state, _ = coach.start()
    assert coach.turn(state, text).terminate
    assert not state.evidence_requests


def test_no_at_location_blocks_evidence_then_yes_clears():
    coach, state = reach_location()
    coach.turn(state, "No")
    assert state.safety_gate is SafetyGate.SAFE_LOCATION
    assert not state.evidence_requests
    assert coach.turn(state, "Yes, I'm on the kerb.").expects == "photo"


def test_collection_responses_do_not_restart_injury_gates():
    coach, state = reach_location()
    coach.turn(state, "Yes")
    coach.turn(state, "Photo taken")
    coach.turn(state, "The plate is ABC123")
    assert state.status is SessionStatus.ACTIVE
    assert state.unanswered_safety_turns == 0
    assert state.evidence_requests == ["wide_scene_photo", "other_plate"]
    assert coach.turn(state, "My chest hurts now").terminate


@pytest.mark.parametrize("text", ["No pain", "I am not hurt", "The mirror is broken"])
def test_denial_or_vehicle_damage_is_not_positive_injury(text):
    assert not classify_safety(text).injury


def test_unrelated_no_does_not_clear_injury_gate():
    coach = CollisionWorkflow()
    state, _ = coach.start()
    coach.turn(state, "No insurance card")
    assert state.safety_gate is SafetyGate.USER_INJURY


def test_reentry_requires_question_and_medical_answer():
    coach = CollisionWorkflow()
    state, _ = coach.start()
    coach.turn(state, "My chest hurts")
    coach.turn(state, "Yes")
    assert state.status is SessionStatus.STOOD_DOWN
    coach.turn(state, "I checked my car")
    assert state.status is SessionStatus.STOOD_DOWN
    coach.turn(state, "Yes, a doctor checked me")
    assert state.status is SessionStatus.ACTIVE
    assert state.safety_gate is SafetyGate.USER_INJURY


def test_injury_preempts_medical_reentry():
    coach = CollisionWorkflow()
    state, _ = coach.start()
    coach.turn(state, "My chest hurts")
    coach.turn(state, "")
    assert coach.turn(state, "Yes, but my chest still hurts").terminate
    assert state.status is SessionStatus.STOOD_DOWN


@pytest.mark.parametrize("answer", ["No", "No.", "Nope", "Not yet", "No, nobody has checked me"])
def test_medical_reentry_acknowledges_no_and_stays_blocked(answer):
    coach = CollisionWorkflow()
    state, _ = coach.start()
    coach.turn(state, "My chest hurts")
    question = coach.turn(state, "I want to continue")
    assert "medical checked" in question.text
    for _ in range(2):
        reply = coach.turn(state, answer)
        assert "Understood" in reply.text
        assert "Coaching remains paused" in reply.text
        assert "?" not in reply.text
        assert state.status is SessionStatus.STOOD_DOWN
        assert state.safety_gate is SafetyGate.MEDICAL_REENTRY
        assert not state.evidence_requests
        assert "MEDICAL_REENTRY_CLEARED" not in state.events
    reply = coach.turn(state, "Yes, a doctor checked me")
    assert reply.text == "Are you hurt anywhere?"
    assert state.status is SessionStatus.ACTIVE


def test_unclear_medical_reentry_answer_still_asks_question():
    coach = CollisionWorkflow()
    state, _ = coach.start()
    coach.turn(state, "My chest hurts")
    coach.turn(state, "I want to continue")
    reply = coach.turn(state, "Maybe")
    assert "medical checked" in reply.text
    assert state.status is SessionStatus.STOOD_DOWN
