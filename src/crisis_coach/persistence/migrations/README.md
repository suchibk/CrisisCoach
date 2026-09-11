# SQLite migrations

001_initial.sql creates incident snapshots and event records atomically and sets PRAGMA user_version to 1. Future versions require explicit ordered migrations.
