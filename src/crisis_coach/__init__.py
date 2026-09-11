"""Crisis Coach prototype."""

from .models import Instruction, SceneState, SessionStatus
from .domains.collision import CollisionWorkflow

CrisisCoach = CollisionWorkflow

__all__ = [
    "CollisionWorkflow",
    "CrisisCoach",
    "Instruction",
    "SceneState",
    "SessionStatus",
]
