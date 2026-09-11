"""Collision policy adapter; scene-specific rules stay outside the engine."""
from ...models.ai import SceneInterpretation
from datetime import datetime, timezone
from importlib.resources import files
from ...models.evidence import EvidenceCatalogue, EvidenceStatus
from ...orchestration.planner import rank_evidence
from .rules import apply_scene_changes, applicable_items, record_report
from ..contracts import DomainMetadata
from ...models import SceneState, Instruction, SessionStatus, SafetyGate
from .ai.contracts import InjuryClassifier, AIInjuryAssessment
from .safety import classify_safety, run_safety_guard, stand_down

class CollisionPack:
    metadata = DomainMetadata(domain_id="collision", version="1", display_name="Collision")

    def __init__(self, ai_classifier: InjuryClassifier | None = None, now=None, interpreter=None):
        self.ai_classifier = ai_classifier
        self.interpreter = interpreter
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.catalogue = EvidenceCatalogue.model_validate_json(files("crisis_coach.domains.collision").joinpath("resources/evidence_catalogue.json").read_text(encoding="utf-8"))

    def opening(self, state: SceneState) -> Instruction:
        state.safety_gate = SafetyGate.USER_INJURY
        return Instruction(text="Are you hurt anywhere?", expects="yes_or_no")

    def recovery(self, state: SceneState) -> Instruction:
        if state.status is SessionStatus.STOOD_DOWN and state.stand_down_kind in ("fire", "hostility"):
            from .danger import danger_recovery
            return danger_recovery(state)
        if state.status is SessionStatus.STOOD_DOWN:
            state.safety_gate = SafetyGate.MEDICAL_REENTRY
            return Instruction(text="Before anything else - has someone medical checked you?", expects="yes_or_no")
        if state.status is SessionStatus.COMPLETE:
            return Instruction(text="This incident is complete.", terminate=True)
        state.unanswered_safety_turns = 0
        first = self.opening(state)
        if state.status is SessionStatus.STOPPED:
            state.last_instruction = first
            return Instruction(text="Paused. Say go on whenever you're ready.")
        return first

    def preempt(self, state: SceneState, text: str) -> Instruction | None:
        if classify_safety(text).injury:
            return stand_down(state, text)
        from .danger import danger_kind, danger_stop
        kind = danger_kind(text)
        if kind:
            return danger_stop(state, kind, text)
        return None

    def guard(self, state: SceneState, text: str) -> Instruction | None:
        was_cleared = self.is_cleared(state)
        reply = run_safety_guard(state, text, self.ai_classifier)
        if state.status is SessionStatus.ACTIVE:
            previous = (dict(state.domain_data), {key: record.model_dump() for key, record in state.evidence.items()})
            apply_scene_changes(state, self.catalogue, text, self.now())
            if was_cleared:
                if text.strip().lower() not in ("confirm scene", "reject scene"):
                    state.pending_scene_changes = ()
                normalized = text.strip().lower()
                if normalized == "confirm scene" and state.pending_scene_changes:
                    for observation in state.pending_scene_changes:
                        canonical = {"witness_leaving":"witness is leaving", "driver_leaving":"driver is leaving", "driver_left":"driver has left", "witness_left":"witness has left", "unattended":"/scenario unattended", "scuff":"/scenario scuff"}[observation.signal]
                        apply_scene_changes(state, self.catalogue, canonical, self.now())
                    state.pending_scene_changes = ()
                    state.events.append("AI_SCENE_CONFIRMED")
                elif normalized == "reject scene":
                    state.pending_scene_changes = ()
                elif state.ai_text_allowed and self.interpreter is not None and reply is None and normalized and len(text) <= 2000 and not normalized.startswith("/") and normalized not in ("done", "photo taken", "got it", "yes", "no") and previous == (state.domain_data, {key: record.model_dump() for key, record in state.evidence.items()}):
                    try:
                        result = SceneInterpretation.model_validate(self.interpreter.interpret(text))
                        if result.possible_injury:
                            return stand_down(state, "possible injury reported: " + text)
                        if any(obs.supporting_quote not in text for obs in result.observations):
                            raise ValueError("Scene observation is not grounded in this utterance")
                        if result.observations:
                            state.pending_scene_changes = result.observations
                            descriptions = {"witness_leaving":"the witness is leaving", "driver_leaving":"the driver is leaving", "driver_left":"the driver has left", "witness_left":"the witness has left", "unattended":"this is unattended vehicle damage", "scuff":"this is a minor single-vehicle scuff"}
                            summary = "; ".join(descriptions[obs.signal] for obs in result.observations)
                            return Instruction(text=f"I understood that {summary}. Say 'confirm scene' or 'reject scene'.")
                    except Exception as exc:
                        state.events.append(f"AI_SCENE_FAILED: {type(exc).__name__}")
                error = record_report(state, self.catalogue, text)
                if error:
                    return Instruction(text=error)
                if text.strip().lower() in ("what's left?", "what is missing?", "what's missing?", "what is left?", "/missing"):
                    pending = [item.label for item in applicable_items(state, self.catalogue) if state.evidence[item.item_id].status is EvidenceStatus.PENDING]
                    unavailable = [item.label for item in applicable_items(state, self.catalogue) if state.evidence[item.item_id].status in (EvidenceStatus.UNAVAILABLE, EvidenceStatus.FAILED)]
                    return Instruction(text="Still to record: " + (", ".join(pending) or "none") + ". Unavailable or failed: " + (", ".join(unavailable) or "none") + ". User-reported items are not verified uploads.")
        return reply

    def paused(self, state: SceneState, text: str) -> Instruction:
        if self.ai_classifier is not None:
            try:
                if self.ai_classifier.classify_injury(text).assessment is AIInjuryAssessment.INJURY:
                    return stand_down(state, text)
            except Exception as exc:
                state.events.append(f"AI_INJURY_CLASSIFIER_FAILED: {type(exc).__name__}")
        return Instruction(text="Paused. Say go on whenever you're ready.")

    def silence(self, state: SceneState) -> Instruction:
        if state.safety_gate is SafetyGate.SAFE_LOCATION:
            state.unanswered_safety_turns += 1
            if state.unanswered_safety_turns >= 2:
                return stand_down(state, "safety question unanswered")
        reply = self.guard(state, "")
        if reply is None:
            raise RuntimeError("Silence handler requires an unanswered safety gate")
        return reply

    def is_cleared(self, state: SceneState) -> bool:
        return state.safety_gate is SafetyGate.CLEARED

    def next_instruction(self, state: SceneState) -> Instruction:
        if state.status is not SessionStatus.ACTIVE or not self.is_cleared(state):
            raise RuntimeError("Evidence requires active, cleared safety gates")
        apply_scene_changes(state, self.catalogue, "", self.now())
        items = applicable_items(state, self.catalogue)
        decision = rank_evidence(items, state.evidence, self.now())
        state.last_decision = decision
        state.current_evidence_id = decision.selected_id
        if decision.selected_id is None:
            return Instruction(text="No pending collection tasks remain. Reported items are not verified uploads; unavailable items remain gaps.")
        item = next(item for item in items if item.item_id == decision.selected_id)
        if item.item_id not in state.evidence_requests:
            state.evidence_requests.append(item.item_id)
        state.events.append(f"EVIDENCE_SELECTED: {item.item_id}")
        return Instruction(text=item.instruction, expects=item.expects)

    def capture_tool(self, state: SceneState, item_id: str) -> str | None:
        for item in applicable_items(state, self.catalogue):
            if item.item_id == item_id:
                return "capture_photo" if item.expects == "photo" else "record_statement"
        return None

    def capture_safety(self, state: SceneState, text: str) -> Instruction | None:
        # Submitted evidence is screened for injury, not interpreted as scene commands.
        return run_safety_guard(state, text, self.ai_classifier)

    def report_items(self, state: SceneState):
        return applicable_items(state, self.catalogue)

    def photo_goal(self, state, item_id):
        return next(item.instruction for item in self.catalogue.items if item.item_id == item_id)
