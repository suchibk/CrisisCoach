from __future__ import annotations

from uuid import uuid4

from ...ai import InjuryClassifier
from ...models import Instruction, SafetyGate, SceneState
from .injury_guard import run_safety_guard


class CollisionWorkflow:
    """Deterministic collision workflow for the first prototype slice."""

    def __init__(self, ai_classifier: InjuryClassifier | None = None) -> None:
        self._ai_classifier = ai_classifier

    def start(self, person_name: str = "Dana Okoye") -> tuple[SceneState, Instruction]:
        state = SceneState(incident_id=str(uuid4()), person_name=person_name)
        state.events.append("SCENE_OPENED")
        return state, Instruction(text="Are you hurt anywhere?", expects="yes_or_no")

    def turn(self, state: SceneState, user_text: str) -> Instruction:
        state.events.append(f"USER: {user_text}")
        guarded = run_safety_guard(state, user_text, self._ai_classifier)
        if guarded is not None:
            return guarded
        if state.safety_gate is SafetyGate.CLEARED:
            state.evidence_requests.append("wide_scene_photo")
            return Instruction(
                text="Photograph both cars exactly where they are, before anyone moves them.",
                expects="photo",
            )
        raise RuntimeError("No route from current scene state")


# Compatibility alias for callers created during the first prototype slice.
CrisisCoach = CollisionWorkflow
