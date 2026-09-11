from crisis_coach import CollisionWorkflow, SessionStatus
from crisis_coach.ai import AIInjuryAssessment, AIInjuryResult


class FakeClassifier:
    def __init__(
        self,
        assessment: AIInjuryAssessment = AIInjuryAssessment.UNCERTAIN,
        error: Exception | None = None,
    ) -> None:
        self.assessment = assessment
        self.error = error
        self.calls: list[str] = []

    def classify_injury(self, text: str) -> AIInjuryResult:
        self.calls.append(text)
        if self.error:
            raise self.error
        return AIInjuryResult(assessment=self.assessment, rationale="fake result")


def test_dana_explicit_injury_stands_down_without_ai_call() -> None:
    classifier = FakeClassifier(AIInjuryAssessment.NO_INJURY)
    coach = CollisionWorkflow(ai_classifier=classifier)
    state, _ = coach.start()

    instruction = coach.turn(state, "My chest hurts, where the belt was.")

    assert instruction.terminate is True
    assert state.status is SessionStatus.STOOD_DOWN
    assert classifier.calls == []


def test_ai_may_escalate_locally_ambiguous_language() -> None:
    classifier = FakeClassifier(AIInjuryAssessment.INJURY)
    coach = CollisionWorkflow(ai_classifier=classifier)
    state, _ = coach.start()

    instruction = coach.turn(state, "The belt knocked the wind out of me.")

    assert instruction.terminate is True
    assert state.status is SessionStatus.STOOD_DOWN
    assert classifier.calls == ["The belt knocked the wind out of me."]


def test_ai_cannot_clear_an_ambiguous_safety_answer() -> None:
    classifier = FakeClassifier(AIInjuryAssessment.NO_INJURY)
    coach = CollisionWorkflow(ai_classifier=classifier)
    state, _ = coach.start()

    instruction = coach.turn(state, "I feel strange.")

    assert instruction.terminate is False
    assert instruction.text == "Are you hurt anywhere?"
    assert state.unanswered_safety_turns == 1


def test_ai_failure_falls_back_to_conservative_local_behavior() -> None:
    classifier = FakeClassifier(error=TimeoutError("provider unavailable"))
    coach = CollisionWorkflow(ai_classifier=classifier)
    state, _ = coach.start()

    instruction = coach.turn(state, "I feel strange.")

    assert instruction.text == "Are you hurt anywhere?"
    assert "AI_INJURY_CLASSIFIER_FAILED: TimeoutError" in state.events
