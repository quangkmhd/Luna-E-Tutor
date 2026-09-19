CREATE TABLE IF NOT EXISTS speaking_sessions (
  session_id TEXT PRIMARY KEY,
  state_json TEXT NOT NULL,
  version INTEGER NOT NULL,
  status TEXT NOT NULL,
  active_turn_id TEXT
);
CREATE TABLE IF NOT EXISTS speaking_turns (
  session_id TEXT NOT NULL,
  turn_id TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  generation TEXT NOT NULL,
  reserved_at REAL NOT NULL,
  status TEXT NOT NULL,
  reply_json TEXT,
  PRIMARY KEY (session_id, turn_id)
);
CREATE TABLE IF NOT EXISTS speaking_voice_leases (
  session_id TEXT PRIMARY KEY,
  token TEXT NOT NULL,
  expires_at REAL NOT NULL
);
