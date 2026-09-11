"""Application dependency construction."""
from __future__ import annotations

from .ai.config import AISettings
from .domains.collision.ai.contracts import InjuryClassifier


def build_optional_injury_classifier() -> InjuryClassifier | None:
    """Build the configured AI adapter, or return None for offline mode."""
    settings = AISettings.from_environment()
    if settings is None:
        return None

    from .domains.collision.ai.injury_classifier import NebiusInjuryClassifier

    return NebiusInjuryClassifier(settings)


def build_repository():
    from .config import AppSettings
    from .persistence.sqlite import SQLiteIncidentRepository
    return SQLiteIncidentRepository(AppSettings().database_path)


def build_domain_registry():
    from .domains.registry import DomainRegistry
    from .domains.collision.pack import CollisionPack
    registry = DomainRegistry()
    registry.register(CollisionPack(build_optional_injury_classifier(), interpreter=build_optional_specialist("scene")))
    return registry


def build_coach(domain_id: str = "collision", backend: str | None = None):
    from .config import AppSettings
    from .orchestration.engine import WorkflowEngine
    from .tools.capture import build_capture_executor
    from .persistence.attachments import AttachmentStore
    pack = build_domain_registry().get(domain_id)
    return WorkflowEngine(pack, repository=build_repository(), backend=backend or AppSettings().graph_backend, executor=build_capture_executor(AppSettings().data_dir / "attachments"), photo_reviewer=build_optional_specialist("vision"), attachment_store=AttachmentStore(AppSettings().data_dir / "attachments"))


def build_optional_specialist(capability: str):
    """Optional AI initialization must not disable local safety or capture."""
    try:
        settings = AISettings.for_capability(capability)
        if settings is None: return None
        if capability == "scene":
            from .ai.specialists.scene_interpreter import StructuredSceneInterpreter
            return StructuredSceneInterpreter(settings)
        from .ai.specialists.evidence_reviewer import StructuredPhotoReviewer
        return StructuredPhotoReviewer(settings)
    except (ImportError, RuntimeError, ValueError):
        return None
