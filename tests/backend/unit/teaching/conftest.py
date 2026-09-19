from pathlib import Path

import pytest

from luna_tutor.curriculum.loader import load_unit
from luna_tutor.domain.evidence import EvaluatorResult, ObjectiveEvidence
from luna_tutor.domain.state import ActivityProgress, LessonState
from luna_tutor.teaching.engine import TeachingEngine

HOME = 'unit01.lesson01.pattern.live_in'
CITY = 'unit01.lesson01.vocabulary.city'
COUNTRY = 'unit01.lesson01.vocabulary.countryside'
HOBBY = 'unit01.level02.pattern.hobby'
TRAFFIC = 'unit01.level03.vocabulary.traffic_jam'


@pytest.fixture
def engine():
    return TeachingEngine()


@pytest.fixture
def unit_01():
    return load_unit(Path(__file__).resolve().parents[4] / 'curriculum/grade-05/unit-01')


@pytest.fixture
def state(unit_01):
    prior = []
    for activity in unit_01.activities:
        if activity.id == 'lesson-01.home':
            break
        if activity.stage_id == 'lesson-01':
            prior.append(ActivityProgress(activity_id=activity.id, status='completed'))
    return LessonState(
        session_id='session-1', unit_id=unit_01.id, stage_id='lesson-01',
        activity_id='lesson-01.home', objective_id=HOME,
        completed_stage_ids=('warm-up',),
        activity_progress=(*prior, ActivityProgress(
            activity_id='lesson-01.home', status='in_progress',
            response_opportunity_given=True,
        )),
    )


@pytest.fixture
def evidence():
    def make(*, meaning='satisfied', form='correct_target_form', quote='I live in the city.',
             objective_id=HOME, recast=False, correction=None, kind='answer',
             emotion=(), clarify=False, reason=None, items=None, **extra):
        if items is None:
            items = [ObjectiveEvidence(
                objective_id=objective_id, meaning_status=meaning,
                target_form_status=form, evidence_quote=quote,
                recast_needed=recast, corrected_form=correction,
            )]
        return EvaluatorResult(
            turn_id='turn-1', state_version=0, response_kind=kind,
            emotional_signals=list(emotion), objective_evidence=items,
            needs_clarification=clarify, ambiguity_reason=reason, **extra,
        )
    return make


@pytest.fixture
def free_state(unit_01):
    return LessonState(
        session_id='session-1', unit_id=unit_01.id, stage_id='free-talk',
        activity_id='free-talk.conversation',
        completed_stage_ids=('warm-up', 'lesson-01', 'lesson-02', 'lesson-03', 'level-02', 'level-03'),
        activity_progress=(ActivityProgress(
            activity_id='free-talk.conversation', status='in_progress',
            response_opportunity_given=True,
        ),),
    )
