from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

from luna_tutor.speaking.models import SpeakingState, TurnInput


class NotFound(LookupError): pass
class Conflict(RuntimeError): pass
class SessionClosed(RuntimeError): pass


@dataclass(frozen=True)
class Reservation:
    generation: str
    existing_reply: dict | None = None


class SpeakingRepository:
    def __init__(self, path: Path, *, lease_seconds: float = 60.0, time_fn=time.time):
        self.path = path
        self.lease_seconds = lease_seconds
        self.time_fn = time_fn
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(Path(__file__).with_name('schema.sql').read_text())

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _dump(state: SpeakingState) -> str:
        return state.model_dump_json()

    def create(self, state: SpeakingState) -> SpeakingState:
        with self._connect() as db:
            db.execute('INSERT INTO speaking_sessions VALUES (?, ?, ?, ?, NULL)',
                       (state.session_id, self._dump(state), state.version, state.status))
        return state

    def get(self, session_id: str) -> SpeakingState:
        with self._connect() as db:
            row = db.execute('SELECT state_json FROM speaking_sessions WHERE session_id=?',
                             (session_id,)).fetchone()
        if row is None:
            raise NotFound(session_id)
        return SpeakingState.model_validate_json(row['state_json'])

    def list_sessions(self) -> list[SpeakingState]:
        with self._connect() as db:
            rows = db.execute('SELECT state_json FROM speaking_sessions ORDER BY rowid DESC').fetchall()
        return [SpeakingState.model_validate_json(row['state_json']) for row in rows]

    def acquire_voice(self, session_id: str, token: str, ttl_seconds: float = 30.0) -> None:
        now = self.time_fn()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            session = db.execute('SELECT status FROM speaking_sessions WHERE session_id=?',
                                 (session_id,)).fetchone()
            if session is None:
                raise NotFound(session_id)
            if session['status'] != 'active':
                raise SessionClosed(session_id)
            lease = db.execute('SELECT * FROM speaking_voice_leases WHERE session_id=?',
                               (session_id,)).fetchone()
            if lease and lease['token'] != token and lease['expires_at'] > now:
                raise Conflict('voice is already connected for this session')
            db.execute(
                'INSERT INTO speaking_voice_leases VALUES (?, ?, ?) '
                'ON CONFLICT(session_id) DO UPDATE SET token=excluded.token, expires_at=excluded.expires_at',
                (session_id, token, now + ttl_seconds),
            )

    def release_voice(self, session_id: str, token: str) -> None:
        with self._connect() as db:
            db.execute('DELETE FROM speaking_voice_leases WHERE session_id=? AND token=?',
                       (session_id, token))

    def reserve_turn(self, session_id: str, turn: TurnInput) -> Reservation:
        digest = hashlib.sha256(turn.model_dump_json().encode()).hexdigest()
        generation = str(uuid4())
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            session = db.execute('SELECT * FROM speaking_sessions WHERE session_id=?',
                                 (session_id,)).fetchone()
            if session is None:
                raise NotFound(session_id)
            if session['status'] != 'active':
                raise SessionClosed(session_id)
            now = self.time_fn()
            if session['active_turn_id'] is not None:
                active = db.execute('SELECT * FROM speaking_turns WHERE session_id=? AND turn_id=?',
                                    (session_id, session['active_turn_id'])).fetchone()
                if active and active['status'] == 'reserved' and now - active['reserved_at'] >= self.lease_seconds:
                    db.execute('UPDATE speaking_turns SET status=? WHERE session_id=? AND turn_id=?',
                               ('expired', session_id, session['active_turn_id']))
                    db.execute('UPDATE speaking_sessions SET active_turn_id=NULL WHERE session_id=?',
                               (session_id,))
                    session = db.execute('SELECT * FROM speaking_sessions WHERE session_id=?',
                                         (session_id,)).fetchone()
            old = db.execute('SELECT * FROM speaking_turns WHERE session_id=? AND turn_id=?',
                             (session_id, turn.turn_id)).fetchone()
            if old:
                if old['payload_hash'] != digest:
                    raise Conflict('turn id already belongs to different input')
                if old['status'] == 'committed':
                    return Reservation(old['generation'], json.loads(old['reply_json']))
                if old['status'] == 'expired':
                    db.execute('DELETE FROM speaking_turns WHERE session_id=? AND turn_id=?',
                               (session_id, turn.turn_id))
                else:
                    raise Conflict('turn is already being processed')
            if session['version'] != turn.expected_version:
                raise Conflict('session version changed')
            if session['active_turn_id'] is not None:
                raise Conflict('another turn is being processed')
            db.execute('INSERT INTO speaking_turns VALUES (?, ?, ?, ?, ?, ?, NULL)',
                       (session_id, turn.turn_id, digest, generation, now, 'reserved'))
            db.execute('UPDATE speaking_sessions SET active_turn_id=? WHERE session_id=?',
                       (turn.turn_id, session_id))
        return Reservation(generation)

    def commit_turn(self, session_id: str, turn_id: str, generation: str,
                    next_state: SpeakingState, reply: dict) -> None:
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            session = db.execute('SELECT * FROM speaking_sessions WHERE session_id=?',
                                 (session_id,)).fetchone()
            turn = db.execute('SELECT * FROM speaking_turns WHERE session_id=? AND turn_id=?',
                              (session_id, turn_id)).fetchone()
            if (session is None or session['status'] != 'active' or
                    session['active_turn_id'] != turn_id or
                    next_state.version != session['version'] + 1 or
                    turn is None or turn['generation'] != generation or turn['status'] != 'reserved'):
                raise Conflict('turn reservation is no longer valid')
            db.execute('UPDATE speaking_turns SET status=?, reply_json=? WHERE session_id=? AND turn_id=?',
                       ('committed', json.dumps(reply), session_id, turn_id))
            db.execute('UPDATE speaking_sessions SET state_json=?, version=?, status=?, active_turn_id=NULL WHERE session_id=?',
                       (self._dump(next_state), next_state.version, next_state.status, session_id))

    def release_turn(self, session_id: str, turn_id: str, generation: str) -> None:
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM speaking_turns WHERE session_id=? AND turn_id=? AND generation=? AND status=?',
                       (session_id, turn_id, generation, 'reserved'))
            db.execute('UPDATE speaking_sessions SET active_turn_id=NULL WHERE session_id=? AND active_turn_id=?',
                       (session_id, turn_id))

    def finish(self, session_id: str, expected_version: int) -> SpeakingState:
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM speaking_sessions WHERE session_id=?', (session_id,)).fetchone()
            if row is None: raise NotFound(session_id)
            state = SpeakingState.model_validate_json(row['state_json'])
            if state.status != 'active': return state
            if state.version != expected_version: raise Conflict('session version changed')
            state = state.model_copy(update={'status': 'completed', 'version': state.version + 1})
            db.execute('UPDATE speaking_turns SET status=? WHERE session_id=? AND status=?',
                       ('cancelled', session_id, 'reserved'))
            db.execute('UPDATE speaking_sessions SET state_json=?, version=?, status=?, active_turn_id=NULL WHERE session_id=?',
                       (self._dump(state), state.version, state.status, session_id))
        return state
