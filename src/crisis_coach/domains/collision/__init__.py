"""Road-traffic collision workflow."""

__all__ = ["CollisionWorkflow", "CrisisCoach"]

def __getattr__(name):
    if name in __all__:
        from .workflow import CollisionWorkflow
        return CollisionWorkflow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
