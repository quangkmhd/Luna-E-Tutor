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
