from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError
import yaml

ROOT = Path(__file__).resolve().parents[4]
UNIT = ROOT / 'curriculum/grade-05/unit-01'
EXPECTED_VOCABULARY = {
    'city', 'class', 'countryside', 'dolphin', 'pink', 'sandwich',
    'table-tennis', 'birthday', 'hobby', 'phone-number', 'subject',
    'cottage', 'calm', 'crowded', 'vehicles', 'traffic-jam',
    'pavement', 'drawback', 'amusement-park',
}
EXPECTED_PATTERNS = {'class', 'live-in', 'favourite', 'birthday', 'hobby',
                     'describe-countryside', 'however', 'moreover'}


@pytest.fixture
def unit_01():
    from luna_tutor.curriculum.loader import load_unit
    return load_unit(UNIT)


def test_unit_01_has_expected_vocabulary(unit_01):
    assert unit_01.vocabulary_ids() == EXPECTED_VOCABULARY
    assert {p.id for p in unit_01.patterns} == EXPECTED_PATTERNS


def test_all_activity_references_resolve(unit_01):
    unit_01.validate_references()
    assert [s.id for s in unit_01.stages] == [
        'warm-up', 'lesson-01', 'lesson-02', 'lesson-03',
        'level-02', 'level-03', 'free-talk', 'summary',
    ]
    assert [a.id for s in unit_01.stages for a in unit_01.activities if a.stage_id == s.id] == [a.id for a in unit_01.activities]


def test_each_new_word_is_taught_separately_before_practice(unit_01):
    teaching = [a for a in unit_01.activities if a.kind == 'vocabulary_introduction']
    assert len(teaching) == 19
    objectives = {o.id: o for o in unit_01.objectives}
    assert {objectives[a.objective_ids[0]].vocabulary_ids[0] for a in teaching} == EXPECTED_VOCABULARY
    for activity in teaching:
        assert len(activity.objective_ids) == 1
        assert activity.required
        assert activity.completion_rule.model_repetitions == 2
        assert activity.completion_rule.response_opportunity_required
        assert activity.completion_rule.feedback_required
    for stage_id in ['lesson-01', 'lesson-02', 'level-02', 'level-03']:
        activities = [a for a in unit_01.activities if a.stage_id == stage_id]
        assert any(a.kind == 'ask_teacher' and a.required for a in activities)


def test_lesson_three_reviews_existing_objectives_without_new_content(unit_01):
    lesson3 = [a for a in unit_01.activities if a.stage_id == 'lesson-03']
    originals = {o.id for o in unit_01.objectives if '.lesson01.' in o.id or '.lesson02.' in o.id}
    assert {oid for a in lesson3 for oid in a.objective_ids} == originals
    assert not any('.lesson03.' in o.id for o in unit_01.objectives)
    assert all(a.kind != 'vocabulary_introduction' for a in lesson3)


def test_warm_up_only_greets_checks_emotion_and_bridges(unit_01):
    warm_up = [a for a in unit_01.activities if a.stage_id == 'warm-up']
    assert {a.kind for a in warm_up} == {'greeting', 'emotion_check', 'bridge'}
    assert all(not a.objective_ids for a in warm_up)


def test_free_talk_allows_open_review_and_declares_selection_and_role(unit_01):
    stage = next(s for s in unit_01.stages if s.id == 'free-talk')
    assert stage.role.name == 'Emma'
    assert stage.role.country == 'England'
    assert stage.role.announce_start and stage.role.announce_end
    assert stage.review.allow_unresolved_on_exit
    assert stage.review.max_items_per_turn == 1
    assert stage.review.rank_by == ['contextual_relevance', 'importance', 'required_support', 'recency']
    assert stage.review.cancel_if_independently_demonstrated
    assert stage.prerequisite_stage_ids == ['lesson-01', 'lesson-02', 'lesson-03', 'level-02', 'level-03']


def test_all_curriculum_items_preserve_traceable_sources(unit_01):
    for items in [unit_01.vocabulary, unit_01.patterns, unit_01.objectives, unit_01.activities, unit_01.stages]:
        for item in items:
            assert (ROOT / item.source.file).is_file()
            assert item.source.section.strip()
    assert 'Quang' in unit_01.teacher_prompt
    assert not unit_01.teaching_policy.recast_requires_repetition
    assert unit_01.teaching_policy.max_attempts == 2


@pytest.mark.parametrize(('collection', 'field', 'value', 'message'), [
    ('vocabulary', 'unexpected', True, 'Extra inputs'),
    ('vocabulary', 'id', '', 'String'),
    ('activities', 'objective_ids', ['missing'], 'objective'),
    ('activities', 'stage_id', 'missing', 'stage'),
    ('activities', 'max_attempts', 3, 'less than or equal'),
    ('activities', 'max_attempts', '2', 'integer'),
    ('activities', 'completion_rule', None, 'dictionary'),
    ('objectives', 'vocabulary_ids', ['missing'], 'vocabulary'),
    ('objectives', 'pattern_ids', ['missing'], 'pattern'),
    ('stages', 'exits', [], 'at least 1'),
    ('stages', 'exits', ['missing'], 'exit'),
    ('stages', 'prerequisite_stage_ids', ['missing'], 'prerequisite'),
])
def test_rejects_invalid_curriculum(unit_01, collection, field, value, message):
    from luna_tutor.curriculum.models import UnitCurriculum
    data = unit_01.model_dump()
    data[collection][0][field] = value
    with pytest.raises(ValidationError, match=message):
        UnitCurriculum.model_validate(data)


@pytest.mark.parametrize('collection', ['vocabulary', 'patterns', 'objectives', 'activities', 'stages'])
def test_rejects_duplicate_ids(unit_01, collection):
    from luna_tutor.curriculum.models import UnitCurriculum
    data = unit_01.model_dump()
    data[collection].append(deepcopy(data[collection][0]))
    with pytest.raises(ValidationError, match='Duplicate'):
        UnitCurriculum.model_validate(data)


def test_rejects_stage_cycle_without_terminal_exit(unit_01):
    from luna_tutor.curriculum.models import UnitCurriculum
    data = unit_01.model_dump()
    data['stages'][-1]['exits'] = ['warm-up']
    with pytest.raises(ValidationError, match='terminal'):
        UnitCurriculum.model_validate(data)


def test_rejects_entry_route_bypassing_free_talk_prerequisites(unit_01):
    from luna_tutor.curriculum.models import UnitCurriculum
    data = unit_01.model_dump()
    lesson_one = next(stage for stage in data['stages'] if stage['id'] == 'lesson-01')
    lesson_one['exits'] = ['free-talk']
    with pytest.raises(ValidationError, match='entry.*prerequisites'):
        UnitCurriculum.model_validate(data)


def test_rejects_prerequisites_only_reachable_on_separate_routes(unit_01):
    from luna_tutor.curriculum.models import UnitCurriculum
    data = unit_01.model_dump()
    stages = {stage['id']: stage for stage in data['stages']}
    stages['lesson-01']['exits'] = ['lesson-02', 'lesson-03']
    stages['lesson-02']['exits'] = ['level-02']
    # Every stage is graph-reachable, but no route handles both Lessons 2 and 3.
    with pytest.raises(ValidationError, match='entry.*prerequisites'):
        UnitCurriculum.model_validate(data)


def test_rejects_missing_objective_coverage(unit_01):
    from luna_tutor.curriculum.models import UnitCurriculum
    data = unit_01.model_dump()
    objective = deepcopy(data['objectives'][0])
    objective['id'] = 'uncovered-objective'
    data['objectives'].append(objective)
    with pytest.raises(ValidationError, match='coverage'):
        UnitCurriculum.model_validate(data)


def test_loader_accepts_manifest_path(unit_01):
    from luna_tutor.curriculum.loader import load_unit
    assert load_unit(UNIT / 'unit.yaml') == unit_01


def test_loader_rejects_unknown_manifest_fields(tmp_path):
    from luna_tutor.curriculum.loader import load_unit
    content = yaml.safe_load((UNIT / 'unit.yaml').read_text())
    content['typo'] = True
    path = tmp_path / 'unit.yaml'
    path.write_text(yaml.safe_dump(content))
    with pytest.raises(ValidationError, match='Extra inputs'):
        load_unit(path)


def test_rejects_practice_with_passive_completion_rule(unit_01):
    from luna_tutor.curriculum.models import UnitCurriculum
    data = unit_01.model_dump()
    activity = next(a for a in data['activities'] if a['kind'] == 'guided_response')
    activity['completion_rule']['mode'] = 'delivered'
    with pytest.raises(ValidationError, match='completion mode'):
        UnitCurriculum.model_validate(data)


def test_rejects_taught_item_without_objective(unit_01):
    from luna_tutor.curriculum.models import UnitCurriculum
    data = unit_01.model_dump()
    item = deepcopy(data['vocabulary'][0])
    item['id'] = 'orphan-word'
    data['vocabulary'].append(item)
    with pytest.raises(ValidationError, match='objective coverage'):
        UnitCurriculum.model_validate(data)


def test_rejects_objective_without_learning_target(unit_01):
    from luna_tutor.curriculum.models import UnitCurriculum
    data = unit_01.model_dump()
    data['objectives'][0]['vocabulary_ids'] = []
    with pytest.raises(ValidationError, match='learning target'):
        UnitCurriculum.model_validate(data)


def test_rejects_word_introduction_pointing_to_pattern(unit_01):
    from luna_tutor.curriculum.models import UnitCurriculum
    data = unit_01.model_dump()
    activity = next(a for a in data['activities'] if a['kind'] == 'vocabulary_introduction')
    activity['objective_ids'] = ['unit01.lesson01.pattern.live_in']
    with pytest.raises(ValidationError, match='one taught vocabulary'):
        UnitCurriculum.model_validate(data)


def test_rejects_activities_outside_stage_order(unit_01):
    from luna_tutor.curriculum.models import UnitCurriculum
    data = unit_01.model_dump()
    data['activities'].reverse()
    with pytest.raises(ValidationError, match='stage order'):
        UnitCurriculum.model_validate(data)


def test_loader_rejects_content_path_outside_unit(tmp_path):
    from luna_tutor.curriculum.loader import load_unit
    content = yaml.safe_load((UNIT / 'unit.yaml').read_text())
    content['content_files'][0] = '../elsewhere.yaml'
    path = tmp_path / 'unit.yaml'
    path.write_text(yaml.safe_dump(content))
    with pytest.raises(ValueError, match='inside the unit'):
        load_unit(path)
