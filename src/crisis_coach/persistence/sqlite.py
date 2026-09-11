"""Atomic, revision-checked incident snapshots and input/output ledger."""
import sqlite3
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path
from pydantic import ValidationError
from .contracts import ConcurrentUpdateError, IncidentSummary, PersistenceError
from ..models import SceneState, Instruction
from ..models.events import InputEvent, INPUT_EVENT_ADAPTER


class SQLiteIncidentRepository:
    def __init__(self, path: Path):
        self.path = Path(path)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._connection() as db:
                version = db.execute("PRAGMA user_version").fetchone()[0]
                if version == 0:
                    migration = files("crisis_coach.persistence").joinpath("migrations/001_initial.sql").read_text(encoding="utf-8")
                    db.executescript(migration)
                elif version != 1:
                    raise PersistenceError(f"Unsupported database schema version: {version}")
        except OSError as exc:
            raise PersistenceError("Cannot create incident storage") from exc

    @contextmanager
    def _connection(self):
        db = None
        try:
            db = sqlite3.connect(self.path, timeout=5)
            db.execute("PRAGMA foreign_keys = ON")
            with db:
                yield db
        except sqlite3.Error as exc:
            raise PersistenceError("Incident database operation failed") from exc
        finally:
            if db is not None:
                db.close()

    def load(self, incident_id: str) -> SceneState:
        with self._connection() as db:
            row = db.execute("SELECT state_json FROM incidents WHERE incident_id = ?", (incident_id,)).fetchone()
        if row is None:
            raise KeyError(incident_id)
        try:
            return SceneState.model_validate_json(row[0])
        except ValidationError as exc:
            raise PersistenceError("Stored incident failed validation") from exc

    def list_incidents(self) -> list[IncidentSummary]:
        with self._connection() as db:
            rows = db.execute("SELECT state_json FROM incidents ORDER BY rowid DESC").fetchall()
        try:
            states = [SceneState.model_validate_json(row[0]) for row in rows]
        except ValidationError as exc:
            raise PersistenceError("Stored incident failed validation") from exc
        return [IncidentSummary(incident_id=s.incident_id, person_name=s.person_name,
                status=s.status, revision=s.revision) for s in states]

    def has_event(self, incident_id: str, event_id: str) -> bool:
        with self._connection() as db:
            return db.execute("SELECT 1 FROM incident_events WHERE incident_id = ? AND event_id = ?",
                              (incident_id, event_id)).fetchone() is not None

    def save(self, state: SceneState, event: InputEvent | None = None,
             response: Instruction | None = None) -> None:
        # Validate even in-place collection changes before they reach disk.
        snapshot = SceneState.model_validate(state.model_dump())
        snapshot.revision += 1
        # Process-local monotonic deadlines have no meaning after restart.
        snapshot.timer_id = None
        snapshot.timer_deadline = None
        event_json = INPUT_EVENT_ADAPTER.dump_json(event).decode() if event is not None else None
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT revision FROM incidents WHERE incident_id = ?", (state.incident_id,)).fetchone()
            if row is None:
                if state.revision != 0:
                    raise ConcurrentUpdateError("Incident no longer exists")
                db.execute("INSERT INTO incidents VALUES (?, ?, ?)",
                           (state.incident_id, snapshot.revision, snapshot.model_dump_json()))
            else:
                if row[0] != state.revision:
                    raise ConcurrentUpdateError("Incident changed; reopen it before continuing")
                if event is not None and db.execute("SELECT 1 FROM incident_events WHERE incident_id = ? AND event_id = ?",
                                                    (state.incident_id, event.event_id)).fetchone():
                    raise ConcurrentUpdateError("Event already committed")
                db.execute("UPDATE incidents SET revision = ?, state_json = ? WHERE incident_id = ?",
                           (snapshot.revision, snapshot.model_dump_json(), state.incident_id))
            if event is not None:
                db.execute("INSERT INTO incident_events VALUES (?, ?, ?, ?, ?)",
                           (state.incident_id, event.event_id, snapshot.revision, event_json,
                            response.model_dump_json() if response is not None else None))
        state.revision = snapshot.revision
