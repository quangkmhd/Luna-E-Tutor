PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    state_version INTEGER NOT NULL,
    status TEXT NOT NULL,
    state_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS turns (
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    turn_id TEXT NOT NULL,
    sequence_no INTEGER NOT NULL,
    completed_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (session_id, turn_id),
    UNIQUE (session_id, sequence_no)
);

CREATE TABLE IF NOT EXISTS objective_evidence (
    session_id TEXT NOT NULL,
    turn_id TEXT NOT NULL,
    objective_id TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    PRIMARY KEY (session_id, turn_id, objective_id),
    FOREIGN KEY (session_id, turn_id) REFERENCES turns(session_id, turn_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS review_items (
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    objective_id TEXT NOT NULL,
    review_json TEXT NOT NULL,
    PRIMARY KEY (session_id, objective_id)
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    PRIMARY KEY (session_id, name)
);
