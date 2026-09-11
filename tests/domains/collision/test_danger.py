import pytest
from crisis_coach import CollisionWorkflow, SessionStatus
from crisis_coach.models.events import CaptureEvent, IncidentContextEvent
from crisis_coach.models.incident_context import IncidentContext
from crisis_coach.practice.runtime import PracticeRuntime

@pytest.mark.parametrize("text",["He's shouting at me", "He is threatening me", "She is yelling at us", "Smoke is coming from the engine", "The vehicle is on fire", "Fuel is leaking", "I'm not sure, but the car is on fire"])
@pytest.mark.parametrize("paused",[False,True])
def test_danger_preempts_tools_and_controls(text,paused):
    with PracticeRuntime() as run:
        for reply in ["No","No","Yes"]: run.submit(reply)
        if paused: run.submit("pause")
        before=run.scene.evidence.copy()
        reply=run.submit(text)
        assert reply.terminate and run.scene.status is SessionStatus.STOOD_DOWN
        assert run.coach.last_route == ("safety",)
        assert run.scene.evidence == before and not run.audit.calls
        assert run.scene.timer_id is None

@pytest.mark.parametrize("text",["He is not shouting at me", "He isn't threatening me", "There is no smoke from the engine", "The car is not on fire", "What if the car is on fire?", "What happens if he's shouting at me?"])
def test_negated_and_hypothetical_reports_do_not_assert_danger(text):
    coach=CollisionWorkflow();state,_=coach.start()
    for reply in ["No","No","Yes"]: coach.turn(state,reply)
    assert not coach.turn(state,text).terminate
    assert state.status is SessionStatus.ACTIVE


def test_danger_in_context_and_statement_is_screened():
    for event in [IncidentContextEvent(context=IncidentContext(location="Smoke is coming from the engine")),CaptureEvent(item_id="statement",tool="record_statement",arguments={"text":"He is threatening me"})]:
        with PracticeRuntime() as run:
            for reply in ["No","No","Yes"]: run.submit(reply)
            reply=run.coach.handle_event(run.scene,event)
            assert reply.terminate and not run.audit.calls


def test_injury_recovery_cannot_be_replaced_by_environmental_clearance():
    with PracticeRuntime() as run:
        run.submit("My neck hurts")
        run.submit("The car is on fire")
        assert run.scene.stand_down_kind == "injury"
        run.submit("I am away from the danger and safe now")
        assert run.scene.status is SessionStatus.STOOD_DOWN
        assert "medical" in run.scene.last_instruction.text


def test_current_quoted_threat_and_denial_contrast_still_stop():
    with PracticeRuntime() as run:
        run.submit('He is not shouting at me, but he is threatening me')
        assert run.scene.status is SessionStatus.STOOD_DOWN


def test_fire_takes_precedence_over_hostility():
    with PracticeRuntime() as run:
        reply=run.submit("He's shouting at me, but the car is on fire")
        assert run.scene.stand_down_kind == "fire"
        assert "burning vehicle" in reply.text
