CREATE TABLE observations (
    observation_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    period_end TEXT NOT NULL,
    published_at TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    UNIQUE (entity_id, metric, period_end, published_at, revision_id, source_id)
);
CREATE INDEX observations_series ON observations(entity_id, metric, period_end, published_at);

CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    input_snapshot_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE manifests (
    manifest_id TEXT PRIMARY KEY,
    content_json TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE snapshots (
    snapshot_id TEXT PRIMARY KEY,
    manifest_id TEXT NOT NULL REFERENCES manifests(manifest_id),
    published_at TEXT NOT NULL
);

CREATE TRIGGER observations_immutable_update BEFORE UPDATE ON observations
BEGIN SELECT RAISE(ABORT, 'observations are immutable'); END;
CREATE TRIGGER observations_immutable_delete BEFORE DELETE ON observations
BEGIN SELECT RAISE(ABORT, 'observations are immutable'); END;
CREATE TRIGGER manifests_immutable_update BEFORE UPDATE ON manifests
BEGIN SELECT RAISE(ABORT, 'manifests are immutable'); END;
CREATE TRIGGER manifests_immutable_delete BEFORE DELETE ON manifests
BEGIN SELECT RAISE(ABORT, 'manifests are immutable'); END;
CREATE TRIGGER snapshots_immutable_update BEFORE UPDATE ON snapshots
BEGIN SELECT RAISE(ABORT, 'snapshots are immutable'); END;
CREATE TRIGGER snapshots_immutable_delete BEFORE DELETE ON snapshots
BEGIN SELECT RAISE(ABORT, 'snapshots are immutable'); END;
