# Persistence

SQLiteIncidentRepository implements the typed IncidentRepository contract. Version 1 stores validated SceneState snapshots and accepted event/response JSON atomically. Optimistic revisions prevent stale overwrites; event IDs support replay suppression. Connections are per operation and closed explicitly. Migration SQL ships with the package.

Monotonic timer identifiers and deadlines are never stored. Reopening rechecks safety, retaining stand-down or pause status. There is no LangGraph checkpoint adapter or attachment store yet. Schema versions newer than supported are rejected without migration.
