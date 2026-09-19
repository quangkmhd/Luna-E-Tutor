"""Atomic SQLite persistence for immutable lesson snapshots."""

from datetime import datetime, timezone
import json
from importlib.resources import files
from pathlib import Path

from pydantic import Field

from luna_tutor.domain.contracts import Contract, SnapshotItems
from luna_tutor.domain.decisions import CompletedTurn
from luna_tutor.domain.state import LessonState
from luna_tutor.storage.sqlite import connect
from luna_tutor.teaching.closing import finish_text_lesson


class SessionNotFoundError(LookupError):
    pass


class StateConflictError(RuntimeError):
    pass


class StoredSession(Contract):
    state: LessonState
    turns: SnapshotItems[CompletedTurn] = ()
    created_at: str
    updated_at: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        schema = files('luna_tutor.storage').joinpath('schema.sql').read_text(encoding='utf-8')
        with connect(self.path) as database:
            database.executescript(schema)

    def create_session(self, state: LessonState) -> StoredSession:
        timestamp = _now()
        with connect(self.path) as database:
            try:
                database.execute(
                    'INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)',
                    (state.session_id, state.state_version, state.status,
                     state.model_dump_json(), timestamp, timestamp))
            except Exception as error:
                if 'UNIQUE constraint failed' in str(error):
                    return self.get_session(state.session_id)
                raise
        return StoredSession(state=state, created_at=timestamp, updated_at=timestamp)

    def get_session(self, session_id: str) -> StoredSession:
        with connect(self.path) as database:
            row = database.execute(
                'SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
            if row is None:
                raise SessionNotFoundError(session_id)
            turns = database.execute(
                'SELECT completed_json FROM turns WHERE session_id = ? ORDER BY sequence_no',
                (session_id,)).fetchall()
        return StoredSession(
            state=LessonState.model_validate_json(row['state_json']),
            turns=tuple(CompletedTurn.model_validate_json(item['completed_json']) for item in turns),
            created_at=row['created_at'], updated_at=row['updated_at'])

    def list_sessions(self) -> list[StoredSession]:
        with connect(self.path) as database:
            ids = [row['id'] for row in database.execute(
                'SELECT id FROM sessions ORDER BY updated_at DESC, created_at DESC').fetchall()]
        return [self.get_session(session_id) for session_id in ids]

    def get_turn(self, session_id: str, turn_id: str) -> CompletedTurn | None:
        with connect(self.path) as database:
            row = database.execute(
                'SELECT completed_json FROM turns WHERE session_id = ? AND turn_id = ?',
                (session_id, turn_id)).fetchone()
        return None if row is None else CompletedTurn.model_validate_json(row['completed_json'])

    def commit_turn(self, session_id: str, expected_version: int,
                    completed: CompletedTurn) -> CompletedTurn:
        turn_id = completed.plan.turn_id
        with connect(self.path) as database:
            database.execute('BEGIN IMMEDIATE')
            duplicate = database.execute(
                'SELECT completed_json FROM turns WHERE session_id = ? AND turn_id = ?',
                (session_id, turn_id)).fetchone()
            if duplicate is not None:
                database.commit()
                return CompletedTurn.model_validate_json(duplicate['completed_json'])
            row = database.execute(
                'SELECT state_version, status FROM sessions WHERE id = ?',
                (session_id,)).fetchone()
            if row is None:
                database.rollback()
                raise SessionNotFoundError(session_id)
            if row['status'] != 'active':
                database.rollback()
                raise StateConflictError('session is not active')
            if row['state_version'] != expected_version:
                database.rollback()
                raise StateConflictError('state version mismatch')
            if (completed.plan.state_version != expected_version
                    or completed.next_state.state_version != expected_version + 1
                    or completed.next_state.session_id != session_id):
                database.rollback()
                raise StateConflictError('completed turn does not match session version')
            sequence = database.execute(
                'SELECT COUNT(*) AS count FROM turns WHERE session_id = ?',
                (session_id,)).fetchone()['count'] + 1
            timestamp = _now()
            database.execute(
                'INSERT INTO turns VALUES (?, ?, ?, ?, ?)',
                (session_id, turn_id, sequence, completed.model_dump_json(), timestamp))
            for evidence in completed.plan.evidence.objective_evidence:
                database.execute(
                    'INSERT INTO objective_evidence VALUES (?, ?, ?, ?)',
                    (session_id, turn_id, evidence.objective_id, evidence.model_dump_json()))
            database.execute('DELETE FROM review_items WHERE session_id = ?', (session_id,))
            for item in completed.next_state.review_queue:
                database.execute('INSERT INTO review_items VALUES (?, ?, ?)',
                                 (session_id, item.objective_id, item.model_dump_json()))
            database.execute(
                'UPDATE sessions SET state_version = ?, status = ?, state_json = ?, updated_at = ? WHERE id = ?',
                (completed.next_state.state_version, completed.next_state.status,
                 completed.next_state.model_dump_json(), timestamp, session_id))
            database.commit()
        return completed

    def abandon_session(self, session_id: str) -> StoredSession:
        return self._change_status(session_id, 'abandoned')

    def finish_free_talk(self, session_id: str, expected_version: int) -> StoredSession:
        with connect(self.path) as database:
            database.execute('BEGIN IMMEDIATE')
            row = database.execute('SELECT * FROM sessions WHERE id = ?',
                                   (session_id,)).fetchone()
            if row is None:
                database.rollback()
                raise SessionNotFoundError(session_id)
            state = LessonState.model_validate_json(row['state_json'])
            if state.status == 'completed':
                database.commit()
                return self.get_session(session_id)
            if state.status != 'active':
                database.rollback()
                raise StateConflictError('session is not active')
            if state.stage_id != 'free-talk':
                database.rollback()
                raise StateConflictError('session is not in free talk')
            if state.state_version != expected_version:
                database.rollback()
                raise StateConflictError('state version mismatch')
            next_state = finish_text_lesson(state)
            timestamp = _now()
            database.execute(
                'UPDATE sessions SET state_version = ?, status = ?, state_json = ?, updated_at = ? WHERE id = ?',
                (next_state.state_version, next_state.status,
                 next_state.model_dump_json(), timestamp, session_id))
            database.commit()
        return self.get_session(session_id)

    def _change_status(self, session_id: str, status: str) -> StoredSession:
        with connect(self.path) as database:
            database.execute('BEGIN IMMEDIATE')
            row = database.execute('SELECT state_json FROM sessions WHERE id = ?',
                                   (session_id,)).fetchone()
            if row is None:
                database.rollback()
                raise SessionNotFoundError(session_id)
            state = LessonState.model_validate_json(row['state_json'])
            if state.status == status:
                database.commit()
                return self.get_session(session_id)
            next_state = state.model_copy(update={'status': status})
            timestamp = _now()
            database.execute(
                'UPDATE sessions SET status = ?, state_json = ?, updated_at = ? WHERE id = ?',
                (status, next_state.model_dump_json(), timestamp, session_id))
            database.commit()
        return self.get_session(session_id)
