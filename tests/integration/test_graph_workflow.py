import importlib.util
import pytest
from crisis_coach import CollisionWorkflow, SessionStatus
from crisis_coach.models import SceneState, Instruction, SafetyGate
from crisis_coach.domains.contracts import DomainMetadata
from crisis_coach.domains.registry import DomainRegistry
from crisis_coach.orchestration.engine import WorkflowEngine
from crisis_coach.persistence.sqlite import SQLiteIncidentRepository

BACKENDS = ["local", pytest.param("langgraph", marks=pytest.mark.skipif(
    importlib.util.find_spec("langgraph") is None, reason="optional LangGraph dependency not installed"))]

@pytest.mark.parametrize("backend", BACKENDS)
def test_injury_preempts_all_later_nodes(backend):
    coach = CollisionWorkflow(backend=backend)
    state, _ = coach.start()
    assert coach.turn(state, "My chest hurts").terminate
    assert coach.last_route == ("safety",)
    assert not state.evidence_requests

@pytest.mark.parametrize("backend", BACKENDS)
def test_gate_controls_and_collection_routes(backend):
    coach = CollisionWorkflow(backend=backend)
    state, _ = coach.start()
    coach.turn(state, "repeat")
    assert coach.last_route == ("safety", "controls")
    coach.turn(state, "No")
    assert coach.last_route == ("safety", "controls", "gate")
    coach.turn(state, "No")
    assert coach.turn(state, "Yes").expects == "photo"
    assert coach.last_route == ("safety", "controls", "gate", "plan")

@pytest.mark.parametrize("backend", BACKENDS)
def test_graph_persistence_and_paused_safety(tmp_path, backend):
    repo = SQLiteIncidentRepository(tmp_path / "incidents.db")
    coach = CollisionWorkflow(repository=repo, backend=backend)
    state, _ = coach.start()
    coach.turn(state, "pause")
    assert coach.turn(state, "My chest hurts").terminate
    recovered, reply = coach.reopen(state.incident_id)
    assert "medical checked" in reply.text
    assert recovered.status is SessionStatus.STOOD_DOWN

class SyntheticPack:
    """Test-only policy; not real crisis guidance and never registered in the app."""
    metadata = DomainMetadata(domain_id="synthetic", version="test1", display_name="Test")
    def opening(self, state):
        state.safety_gate = "test_pending"
        return Instruction(text="Test gate?")
    def recovery(self, state): return self.opening(state)
    def preempt(self, state, text):
        if text == "halt":
            state.status = SessionStatus.STOOD_DOWN
            return Instruction(text="Test halted", terminate=True)
    def guard(self, state, text):
        if text == "ready": state.safety_gate = "test_clear"
        if not self.is_cleared(state): return Instruction(text="Test gate?")
    def paused(self, state, text): return Instruction(text="Test paused")
    def silence(self, state): return Instruction(text="Test gate?")
    def is_cleared(self, state): return state.safety_gate == "test_clear"
    def next_instruction(self, state): return Instruction(text="Test action")

@pytest.mark.parametrize("backend", BACKENDS)
def test_second_domain_uses_same_engine_without_collision_logic(backend):
    registry = DomainRegistry()
    registry.register(SyntheticPack())
    engine = WorkflowEngine(registry.get("synthetic"), backend=backend)
    state, reply = engine.start("Test user")
    assert state.domain_id == "synthetic"
    assert state.pack_version == "test1"
    assert engine.turn(state, "ready").text == "Test action"
    assert not state.evidence_requests
    assert engine.turn(state, "halt").terminate
    assert engine.last_route == ("safety",)

def test_registry_rejects_duplicates_and_unavailable_domains():
    registry = DomainRegistry()
    registry.register(SyntheticPack())
    with pytest.raises(ValueError): registry.register(SyntheticPack())
    with pytest.raises(ValueError): registry.get("medical")
    assert [m.domain_id for m in registry.available()] == ["synthetic"]

def test_version_and_domain_mismatch_are_rejected_before_progress(tmp_path):
    repo = SQLiteIncidentRepository(tmp_path / "incidents.db")
    engine = WorkflowEngine(SyntheticPack(), repository=repo)
    state, _ = engine.start()
    with pytest.raises(ValueError): CollisionWorkflow(repository=repo).reopen(state.incident_id)
    state.pack_version = "unknown"
    with pytest.raises(ValueError): engine.turn(state, "ready")

def test_legacy_json_defaults_and_domain_specific_gates_round_trip():
    legacy = SceneState.model_validate_json('{"incident_id":"old","person_name":"Dana","safety_gate":"other_injury"}')
    assert legacy.domain_id == "collision" and legacy.pack_version == "1"
    assert legacy.safety_gate is SafetyGate.OTHER_INJURY
    custom = SceneState(incident_id="new", person_name="Test", domain_id="synthetic", safety_gate="custom")
    assert SceneState.model_validate_json(custom.model_dump_json()).safety_gate == "custom"
