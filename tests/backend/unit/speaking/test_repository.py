import pytest

from luna_tutor.speaking.models import SessionConfig, SpeakingState, TurnInput
from luna_tutor.speaking.repository import Conflict, SessionClosed, SpeakingRepository


def initial():
    return SpeakingState.initial('s1', SessionConfig(grade=5, topic='Food', words=('juice',)))


def test_session_is_independent_from_unit_sessions(tmp_path):
    repo = SpeakingRepository(tmp_path / 'sessions.sqlite3')
    repo.create(initial())
    stored = repo.get('s1')
    assert stored.config.topic == 'Food'
    assert not hasattr(stored, 'unit_id')


def test_turn_id_is_idempotent_and_payload_is_bound(tmp_path):
    repo = SpeakingRepository(tmp_path / 'sessions.sqlite3')
    repo.create(initial())
    turn = TurnInput(turn_id='t1', text='I like juice.', expected_version=0)
    first = repo.reserve_turn('s1', turn)
    assert first.existing_reply is None
    reply = {'text': 'Great! What juice do you like?'}
    next_state = initial().model_copy(update={'version': 1})
    repo.commit_turn('s1', 't1', first.generation, next_state, reply)
    repeated = repo.reserve_turn('s1', turn)
    assert repeated.existing_reply == reply
    with pytest.raises(Conflict):
        repo.reserve_turn('s1', turn.model_copy(update={'text': 'Different'}))


def test_stale_version_and_concurrent_reservation_are_rejected(tmp_path):
    path = tmp_path / 'sessions.sqlite3'
    first, second = SpeakingRepository(path), SpeakingRepository(path)
    first.create(initial())
    first.reserve_turn('s1', TurnInput(turn_id='t1', text='Hello', expected_version=0))
    with pytest.raises(Conflict):
        second.reserve_turn('s1', TurnInput(turn_id='t2', text='Hi', expected_version=0))


def test_finish_closes_session_even_with_unseen_words(tmp_path):
    repo = SpeakingRepository(tmp_path / 'sessions.sqlite3')
    repo.create(initial())
    finished = repo.finish('s1', 0)
    assert finished.status == 'completed'
    with pytest.raises(SessionClosed):
        repo.reserve_turn('s1', TurnInput(turn_id='t1', text='Hello', expected_version=1))


def test_late_commit_cannot_reopen_finished_session(tmp_path):
    repo = SpeakingRepository(tmp_path / 'sessions.sqlite3')
    repo.create(initial())
    reservation = repo.reserve_turn('s1', TurnInput(turn_id='t1', text='Hello', expected_version=0))
    repo.finish('s1', 0)
    with pytest.raises(Conflict):
        repo.commit_turn('s1', 't1', reservation.generation,
                         initial().model_copy(update={'version': 1}), {'text': 'late'})
    assert repo.get('s1').status == 'completed'


def test_expired_reservation_can_be_recovered(tmp_path):
    clock = [100.0]
    repo = SpeakingRepository(tmp_path / 'sessions.sqlite3', lease_seconds=5, time_fn=lambda: clock[0])
    repo.create(initial())
    repo.reserve_turn('s1', TurnInput(turn_id='t1', text='Hello', expected_version=0))
    clock[0] = 106.0
    replacement = repo.reserve_turn('s1', TurnInput(turn_id='t2', text='Try again', expected_version=0))
    assert replacement.existing_reply is None


def test_expired_reservation_can_retry_same_id(tmp_path):
    clock = [100.0]
    repo = SpeakingRepository(tmp_path / 'sessions.sqlite3', lease_seconds=5, time_fn=lambda: clock[0])
    repo.create(initial())
    turn = TurnInput(turn_id='t1', text='Hello', expected_version=0)
    first = repo.reserve_turn('s1', turn)
    clock[0] = 106.0
    retried = repo.reserve_turn('s1', turn)
    assert retried.generation != first.generation


def test_only_one_live_voice_connection_owns_a_session(tmp_path):
    clock = [100.0]
    repo = SpeakingRepository(tmp_path / 'sessions.sqlite3', time_fn=lambda: clock[0])
    repo.create(initial())
    repo.acquire_voice('s1', 'first', ttl_seconds=30)
    with pytest.raises(Conflict):
        repo.acquire_voice('s1', 'second', ttl_seconds=30)
    clock[0] = 131.0
    repo.acquire_voice('s1', 'second', ttl_seconds=30)
    repo.release_voice('s1', 'second')
    repo.acquire_voice('s1', 'third', ttl_seconds=30)
