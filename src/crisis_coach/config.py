"""Application settings; incident data defaults outside the source tree."""
import os
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


def default_data_dir() -> Path:
    override = os.getenv("CRISIS_COACH_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        return Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "CrisisCoach"
    return Path(os.getenv("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "crisis-coach"


class AppSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    data_dir: Path = Field(default_factory=default_data_dir)
    graph_backend: Literal["local", "langgraph"] = Field(default_factory=lambda: os.getenv("CRISIS_COACH_GRAPH_BACKEND", "local"), validate_default=True)

    @property
    def database_path(self) -> Path:
        return self.data_dir / "incidents.sqlite3"
