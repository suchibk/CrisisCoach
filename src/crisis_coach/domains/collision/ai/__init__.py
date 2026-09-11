"""Optional collision AI adapters."""

def build_optional_injury_classifier():
    """Compatibility entry point; construct dependencies lazily."""
    from ....bootstrap import build_optional_injury_classifier as build
    return build()

__all__ = ["build_optional_injury_classifier"]
