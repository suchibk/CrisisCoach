from crisis_coach import CrisisCoach, SessionStatus


def test_dana_chest_pain_stands_down_immediately() -> None:
    coach = CrisisCoach()
    state, first = coach.start("Dana Okoye")

    assert first.text == "Are you hurt anywhere?"
    reply = coach.turn(state, "My chest hurts, where the belt was.")

    assert reply.terminate is True
    assert reply.text.startswith("Stop. Hang up and call 911 now")
    assert state.status is SessionStatus.STOOD_DOWN
    assert state.evidence_requests == []


def test_stood_down_session_never_collects_evidence() -> None:
    coach = CrisisCoach()
    state, _ = coach.start()
    coach.turn(state, "My chest hurts")

    reply = coach.turn(state, "Take a photo")

    assert "medical checked" in reply.text
    assert state.evidence_requests == []


def test_reentry_requires_medical_check_then_restarts_safety_gate() -> None:
    coach = CrisisCoach()
    state, _ = coach.start()
    coach.turn(state, "My chest hurts")

    blocked = coach.turn(state, "No")
    cleared = coach.turn(state, "Yes, I was checked and I am fine")

    assert "medical checked" in blocked.text
    assert cleared.text == "Are you hurt anywhere?"
    assert state.status is SessionStatus.ACTIVE


def test_two_silent_safety_answers_fail_safe() -> None:
    coach = CrisisCoach()
    state, _ = coach.start()

    first_retry = coach.turn(state, "")
    reply = coach.turn(state, "")

    assert first_retry.terminate is False
    assert reply.terminate is True
    assert state.status is SessionStatus.STOOD_DOWN


def test_injury_language_overrides_a_generic_no() -> None:
    coach = CrisisCoach()
    state, _ = coach.start()

    instruction = coach.turn(state, "No, but my chest hurts.")

    assert instruction.terminate is True
    assert state.status is SessionStatus.STOOD_DOWN
