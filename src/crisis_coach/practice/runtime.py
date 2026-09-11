"""Temporary storage and explicit fakes; never build configured providers."""
from datetime import datetime, timezone, timedelta
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory
from ..domains.collision.pack import CollisionPack
from ..orchestration.engine import WorkflowEngine
from ..persistence.sqlite import SQLiteIncidentRepository
from ..persistence.attachments import AttachmentStore
from ..models.profile import Profile
from ..models.events import CaptureEvent, AIConsentEvent
from ..models.ai import PhotoAssessment
from ..tools.capture import build_capture_executor

SCENARIOS = {
    "Priya · full collision": ("Priya (practice)", None),
    "Priya · departing witness": ("Priya (practice)", "There's a witness walking away"),
    "Priya · departing driver": ("Priya (practice)", "He's getting back in his car"),
    "Marcus · unattended damage": ("Marcus (practice)", "/scenario unattended"),
    "Priya · minor scuff": ("Priya (practice)", "/scenario scuff"),
    "Dana · injury stand-down": ("Dana (practice)", None),
    "Hostile scene": ("Priya (practice)", None),
}

class ScriptClock:
    def __init__(self):
        self.seconds = 0.0
    def now(self): return self.seconds
    def utcnow(self): return datetime(2026, 9, 11, 12, tzinfo=timezone.utc) + timedelta(seconds=self.seconds)
    def advance(self, seconds):
        if seconds < 0: raise ValueError("Clock cannot move backwards")
        self.seconds += seconds

class FixtureReviewer:
    provider_label = "local practice simulation (no network)"
    def __init__(self): self.calls = 0
    def review(self, data, media_type, goal):
        self.calls += 1
        if data == fixture_bytes("retake"):
            return PhotoAssessment(verdict="retake", issues=("dark",))
        if data == fixture_bytes("usable"):
            return PhotoAssessment(verdict="usable")
        return PhotoAssessment(verdict="uncertain")

def fixture_bytes(name):
    if name not in ("retake", "usable"): raise ValueError("Unknown practice fixture")
    return files("crisis_coach.practice").joinpath(f"fixtures/{name}.png").read_bytes()

class AuditedExecutor:
    def __init__(self, executor):
        self.executor = executor
        self.calls = []
    def execute(self, name, arguments, context):
        self.calls.append(name)
        return self.executor.execute(name, arguments, context)

class PracticeRuntime:
    def __init__(self, scenario="Priya · full collision", backend="local"):
        if scenario not in SCENARIOS: raise ValueError("Unknown practice scenario")
        self.scenario = scenario
        self.temporary = TemporaryDirectory(prefix="crisis-practice-")
        self.root = Path(self.temporary.name)
        self.clock = ScriptClock()
        self.reviewer = FixtureReviewer()
        self.repo = SQLiteIncidentRepository(self.root / "incidents.sqlite3")
        knowledge = Path(str(files("crisis_coach.domains.collision").joinpath("resources/knowledge")))
        self.coach = WorkflowEngine(CollisionPack(now=self.clock.utcnow), clock=self.clock, repository=self.repo, backend=backend,
            executor=build_capture_executor(self.root / "attachments", knowledge_root=knowledge),
            photo_reviewer=self.reviewer, attachment_store=AttachmentStore(self.root / "attachments"))
        self.audit = AuditedExecutor(self.coach.executor)
        self.coach.executor = self.audit
        name, self.seed = SCENARIOS[scenario]
        self.scene, self.first = self.coach.start(name, profile=Profile(name=name, vehicle="Synthetic demo vehicle"), practice=True)

    def submit(self, text):
        cleared = self.coach.pack.is_cleared(self.scene)
        reply = self.coach.turn(self.scene, text)
        if not cleared and self.coach.pack.is_cleared(self.scene) and self.seed:
            seed, self.seed = self.seed, None
            reply = self.coach.turn(self.scene, seed)
        return reply

    def capture(self, verdict, item_id=None):
        item_id = item_id or self.scene.current_evidence_id
        if item_id is None: raise ValueError("No current photo task")
        if not self.scene.ai_images_allowed:
            self.coach.handle_event(self.scene, AIConsentEvent(capability="images", allowed=True))
        path = self.root / (verdict + ".png")
        path.write_bytes(fixture_bytes(verdict))
        return self.coach.handle_event(self.scene, CaptureEvent(item_id=item_id, tool="capture_photo", arguments={"source_path": str(path)}))

    def close(self):
        self.temporary.cleanup()

    def __enter__(self): return self
    def __exit__(self, *args): self.close()
