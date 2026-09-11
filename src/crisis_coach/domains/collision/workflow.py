"""Compatibility facade for the collision domain on the shared engine."""
from .ai.contracts import InjuryClassifier
from .pack import CollisionPack
from ...orchestration.engine import WorkflowEngine
from ...orchestration.clock import Clock
from ...persistence.contracts import IncidentRepository

class CollisionWorkflow(WorkflowEngine):
    def __init__(self, ai_classifier: InjuryClassifier | None = None, clock: Clock | None = None,
                 repository: IncidentRepository | None = None, backend: str = "local", executor=None, interpreter=None, photo_reviewer=None, attachment_store=None):
        super().__init__(CollisionPack(ai_classifier, interpreter=interpreter), clock=clock, repository=repository, backend=backend, executor=executor, photo_reviewer=photo_reviewer, attachment_store=attachment_store)

CrisisCoach = CollisionWorkflow
