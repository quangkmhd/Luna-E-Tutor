from copy import deepcopy
from pathlib import Path
import shutil

import pytest
import yaml
from pydantic import ValidationError

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


def test_load_unit_does_not_require_a_shared_directory(tmp_path):
    """A unit's activity config is self-contained."""
    unit_root = tmp_path / "grade-05" / "unit-01"
    shutil.copytree(UNIT, unit_root)

    from luna_tutor.curriculum.loader import load_unit

    unit = load_unit(unit_root)

    assert next(item for item in unit.activities if item.id == "warm-up.hello").max_attempts == 1


def test_load_unit_does_not_require_legacy_curriculum_metadata(tmp_path):
    """Runtime curriculum does not need format, stage, or pattern-example metadata."""
    unit_root = tmp_path / "grade-05" / "unit-01"
    shutil.copytree(UNIT, unit_root)

    def strip_metadata(fragment):
        if isinstance(fragment, dict):
            fragment.pop("schema_version", None)
            fragment.pop("source", None)
            stage = fragment.get("stage")
            if stage:
                stage.pop("level", None)
                stage.pop("lesson", None)
            for value in fragment.values():
                strip_metadata(value)
        elif isinstance(fragment, list):
            for value in fragment:
                strip_metadata(value)

    for path in unit_root.rglob("*.yaml"):
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        strip_metadata(payload)
        for name in ("opening", "closing"):
            if name in payload:
                strip_metadata(payload[name])
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    from luna_tutor.curriculum.loader import load_unit

    unit = load_unit(unit_root)

    assert unit.id == "grade05.unit01"
    assert next(item for item in unit.patterns if item.id == "class").text.startswith("Can you tell")


def test_completion_rules_do_not_expose_repeated_policy_flags():
    from luna_tutor.curriculum.models import CompletionRule

    assert not {
        "response_opportunity_required",
        "feedback_required",
        "allow_support_limit_exit",
        "mastery_required",
    } & CompletionRule.model_fields.keys()


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
