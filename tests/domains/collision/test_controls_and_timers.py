import pytest
from pydantic import ValidationError
from crisis_coach import CollisionWorkflow, SessionStatus
from crisis_coach.models import SafetyGate
from crisis_coach.models.events import TextEvent, TimerEvent, ControlEvent, Control, INPUT_EVENT_ADAPTER

class FakeClock:
    def __init__(self):
        self.time = 100.0
    def now(self):
        return self.time

@pytest.fixture
def scene():
    clock = FakeClock()
    coach = CollisionWorkflow(clock=clock)
    state, first = coach.start()
    return clock, coach, state, first


def test_safety_silence_retries_at_eight_seconds_then_stops(scene):
    clock, coach, state, first = scene
    clock.time += 7.9
    assert coach.poll(state) is None
    clock.time += 0.1
    assert coach.poll(state).text == first.text
    assert state.unanswered_safety_turns == 1
    clock.time += 8
    assert coach.poll(state).terminate
    assert state.status is SessionStatus.STOOD_DOWN
    assert coach.poll(state) is None


def test_stale_and_early_timers_do_not_mutate_state(scene):
    clock, coach, state, _ = scene
    event = TimerEvent(timer_id=state.timer_id)
    assert coach.handle_event(state, event) is None
    coach.turn(state, "No")
    clock.time += 8
    before = state.model_dump()
    assert coach.handle_event(state, event) is None
    assert state.model_dump() == before


def test_pause_cancels_timer_resume_preserves_question(scene):
    clock, coach, state, _ = scene
    current = coach.turn(state, "No")
    coach.turn(state, "stop")
    clock.time += 100
    assert coach.poll(state) is None
    assert state.status is SessionStatus.STOPPED
    assert coach.turn(state, "go on").text == current.text
    assert state.safety_gate is SafetyGate.OTHER_INJURY
    assert coach.seconds_until_timer(state) == 8


def test_repeat_and_slow_down_preserve_words_and_deadline(scene):
    clock, coach, state, first = scene
    clock.time += 5
    assert coach.turn(state, "repeat").text == first.text
    slower = coach.handle_event(state, ControlEvent(control=Control.SLOW_DOWN))
    assert slower.text == first.text
    assert slower.speech_rate == 0.75
    assert coach.seconds_until_timer(state) == 3
    assert state.unanswered_safety_turns == 0


def test_paused_injury_still_stands_down(scene):
    _, coach, state, _ = scene
    coach.turn(state, "stop")
    assert coach.turn(state, "My chest hurts").terminate
    assert state.status is SessionStatus.STOOD_DOWN
    coach.turn(state, "go on")
    assert state.status is SessionStatus.STOOD_DOWN


def test_evidence_silence_does_not_become_injury(scene):
    clock, coach, state, _ = scene
    for text in ("No", "No", "Yes"):
        coach.turn(state, text)
    for _ in range(3):
        clock.time += 30
        assert not coach.poll(state).terminate
    assert state.status is SessionStatus.ACTIVE
    assert state.unanswered_safety_turns == 0


def test_location_silence_retries_then_stops(scene):
    clock, coach, state, _ = scene
    coach.turn(state, "No")
    coach.turn(state, "No")
    clock.time += 8
    assert coach.poll(state).expects == "yes_or_no"
    clock.time += 8
    assert coach.poll(state).terminate


def test_immediate_duplicate_event_is_ignored(scene):
    _, coach, state, _ = scene
    event = TextEvent(text="No")
    coach.handle_event(state, event)
    assert coach.handle_event(state, event) is None
    assert state.safety_gate is SafetyGate.OTHER_INJURY


def test_event_json_contract_rejects_unknown_fields():
    event = INPUT_EVENT_ADAPTER.validate_json('{"kind":"control","control":"repeat"}')
    assert event.control is Control.REPEAT
    with pytest.raises(ValidationError):
        INPUT_EVENT_ADAPTER.validate_python({"kind": "timer", "timer_id": "x", "extra": True})
