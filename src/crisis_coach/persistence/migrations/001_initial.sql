BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY,
    revision INTEGER NOT NULL,
    state_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS incident_events (
    incident_id TEXT NOT NULL REFERENCES incidents(incident_id),
    event_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    event_json TEXT NOT NULL,
    response_json TEXT,
    PRIMARY KEY (incident_id, event_id)
);
PRAGMA user_version = 1;
COMMIT;
