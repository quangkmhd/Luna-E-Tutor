from pathlib import Path

import pytest

from luna_tutor.domain.decisions import (
    CompletedTurn, PlannedTurn, TeacherConstraints, TeacherTurnRequest,
    TeacherUtterance, TeachingDecision,
)
from luna_tutor.domain.evidence import EvaluatorResult
from luna_tutor.domain.state import LessonState
from luna_tutor.storage.session_repository import (
    SessionRepository, StateConflictError,
)


def state(session_id='session-1', version=0):
    return LessonState(session_id=session_id, unit_id='grade05.unit01',
                       state_version=version, stage_id='warm-up',
                       activity_id='warm-up.hello')


def completed(turn_id='turn-1', session_id='session-1'):
    before = state(session_id)
    evidence = EvaluatorResult(
        turn_id=turn_id, state_version=0, response_kind='answer',
        emotional_signals=[], objective_evidence=[], needs_clarification=False,
        ambiguity_reason=None)
    decision = TeachingDecision(
        feedback_action='acknowledge_and_continue', progression_action='stay')
    request = TeacherTurnRequest(
        turn_id=turn_id, feedback_action='acknowledge_and_continue',
        learner_meaning='Hello', next_teaching_move='Ask how Quang feels.',
        constraints=TeacherConstraints())
    after = before.model_copy(update={
        'state_version': 1, 'applied_turn_ids': (turn_id,),
        'last_teacher_turn': 'Hello, Quang!',
    })
    plan = PlannedTurn(
        turn_id=turn_id, state_version=0, learner_text='Hello',
        privacy_event=False, evidence=evidence, decision=decision,
        teacher_request=request,
        proposed_next_state=after.model_copy(update={'last_teacher_turn': ''}),
    )
    return CompletedTurn(
        plan=plan,
        teacher_utterance=TeacherUtterance(
            spoken_text='Hello, Quang!', delivery_intent='warm'),
        next_state=after)


@pytest.fixture
def repository(tmp_path: Path):
    return SessionRepository(tmp_path / 'sessions.sqlite3')


def test_commit_turn_is_atomic(repository):
    repository.create_session(state())
    repository.commit_turn('session-1', 0, completed())
    loaded = repository.get_session('session-1')
    assert loaded.state.state_version == 1
    assert loaded.turns[-1].plan.turn_id == 'turn-1'


def test_duplicate_turn_id_returns_existing_turn(repository):
    repository.create_session(state())
    first = repository.commit_turn('session-1', 0, completed())
    second = repository.commit_turn('session-1', 0, completed())
    assert second == first
    assert len(repository.get_session('session-1').turns) == 1


def test_stale_different_turn_is_rejected_without_mutation(repository):
    repository.create_session(state())
    repository.commit_turn('session-1', 0, completed())
    with pytest.raises(StateConflictError):
        repository.commit_turn('session-1', 0, completed('turn-2'))
    assert len(repository.get_session('session-1').turns) == 1


def test_abandon_preserves_history_and_list_order(repository):
    repository.create_session(state('old'))
    repository.commit_turn('old', 0, completed(session_id='old'))
    repository.abandon_session('old')
    repository.create_session(state('new'))
    sessions = repository.list_sessions()
    assert [item.state.session_id for item in sessions] == ['new', 'old']
    assert sessions[1].state.status == 'abandoned'
    assert len(sessions[1].turns) == 1


def test_replace_with_session_deletes_all_existing_session_data(repository):
    repository.create_session(state('old'))
    repository.commit_turn('old', 0, completed(session_id='old'))

    fresh = repository.replace_with_session(state('fresh'))

    assert fresh.state.session_id == 'fresh'
    assert [item.state.session_id for item in repository.list_sessions()] == ['fresh']


def test_finish_only_accepts_free_talk_and_is_idempotent(repository):
    repository.create_session(state())
    with pytest.raises(StateConflictError):
        repository.finish_free_talk('session-1', 0)
    free = state().model_copy(update={'stage_id': 'free-talk',
                                      'activity_id': 'free-talk.conversation'})
    repository = SessionRepository(repository.path.parent / 'free.sqlite3')
    repository.create_session(free)
    first = repository.finish_free_talk('session-1', 0)
    second = repository.finish_free_talk('session-1', 0)
    assert first.state.status == second.state.status == 'completed'
    assert first.state.state_version == 1
