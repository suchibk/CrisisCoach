"""Versioned local profile storage with optimistic updates."""
from pathlib import Path
import sqlite3
from pydantic import ValidationError
from ..models.profile import Profile
from .contracts import PersistenceError

class ProfileRepository:
    def __init__(self, path: Path):
        self.path = path

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path)
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            db.close()
            raise PersistenceError("Unsupported profile schema")
        db.execute("CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, data TEXT NOT NULL)")
        db.execute("PRAGMA user_version=1")
        db.commit()
        return db

    def load(self) -> Profile:
        if not self.path.exists(): return Profile()
        try:
            db = self._connect()
            try:
                row = db.execute("SELECT data FROM profile WHERE id=1").fetchone()
                return Profile.model_validate_json(row[0]) if row else Profile()
            finally:
                db.close()
        except (OSError, sqlite3.Error, ValidationError) as exc:
            raise PersistenceError("Cannot read profile") from exc

    def save(self, profile: Profile) -> Profile:
        try:
            db = self._connect()
            try:
                with db:
                    db.execute("BEGIN IMMEDIATE")
                    row = db.execute("SELECT revision FROM profile WHERE id=1").fetchone()
                    if (row[0] if row else 0) != profile.revision:
                        raise PersistenceError("Profile changed; reload before saving")
                    saved = profile.model_copy(update={"revision": profile.revision + 1})
                    db.execute("INSERT OR REPLACE INTO profile VALUES (1, ?, ?)", (saved.revision, saved.model_dump_json()))
                    return saved
            finally:
                db.close()
        except (OSError, sqlite3.Error) as exc:
            raise PersistenceError("Cannot save profile") from exc
