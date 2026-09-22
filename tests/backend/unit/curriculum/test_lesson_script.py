from pathlib import Path

import pytest
import yaml

from luna_tutor.curriculum.lesson_script import load_lesson_script


def payload():
    return {
        'lesson': 1, 'title': 'Hello',
        'greeting': {'order': 1, 'say': 'Hi, con!', 'accept': 'Chấp nhận Hi hoặc Hello.'},
        'words': ['hello', 'hi'], 'patterns': {},
        'stations': [
            {'id': 'vocabulary', 'steps': [
                {'order': 2, 'target': 'hello', 'say': 'Say hello.', 'accept': 'Chấp nhận hello.'},
                {'order': 3, 'target': 'hi', 'say': 'Say hi.', 'accept': 'Chấp nhận hi.'},
            ]},
            {'id': 'patterns', 'steps': [
                {'order': 4, 'say': 'Try a greeting.', 'accept': 'Chấp nhận lời chào.'},
            ]},
            {'id': 'conversation', 'steps': [
                {'order': 5, 'say': 'Start now.', 'accept': 'Chấp nhận lời mở đầu.'},
            ]},
        ],
    }


def write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / 'lesson.yaml'
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
    return path


def test_loads_compact_lesson_and_preserves_accept_for_llm(tmp_path):
    script = load_lesson_script(write(tmp_path, payload()))
    assert script.greeting.order == 1
    assert script.stations[0].steps[0].accept == 'Chấp nhận hello.'
    assert [step.order for station in script.stations for step in station.steps] == [2, 3, 4, 5]


def test_rejects_malformed_speech_tag_with_field_name(tmp_path):
    data = payload()
    data['stations'][0]['steps'][0]['say'] = '<en>HELLO</vi>'
    with pytest.raises(ValueError, match='say'):
        load_lesson_script(write(tmp_path, data))


def test_one_item_can_reference_several_vocabulary_words(tmp_path):
    data = payload()
    data['stations'][0]['steps'][0]['target'] = ['hello', 'hi']
    script = load_lesson_script(write(tmp_path, data))
    assert script.stations[0].steps[0].target == ['hello', 'hi']


@pytest.mark.parametrize('change', [
    lambda data: data['greeting'].update(say=''),
    lambda data: data['greeting'].update(accept=''),
    lambda data: data['greeting'].update(order=2),
    lambda data: data['stations'][0]['steps'][1].update(order=2),
    lambda data: data['stations'][0]['steps'][1].update(order=7),
    lambda data: data['stations'][0]['steps'][1].update(target='missing'),
    lambda data: data['stations'][0]['steps'][1].update(accept=''),
    lambda data: data['stations'][1].update(id='vocabulary'),
])
def test_rejects_invalid_authoring(tmp_path, change):
    data = payload()
    change(data)
    with pytest.raises(ValueError):
        load_lesson_script(write(tmp_path, data))


def test_registry_discovers_a_new_compact_lesson_without_code_changes(tmp_path):
    from luna_tutor.curriculum.registry import CurriculumRegistry
    import shutil

    source = Path(__file__).resolve().parents[4] / 'curriculum/grade-03/unit-01'
    destination = tmp_path / 'grade-03/unit-01'
    shutil.copytree(source, destination)
    second = payload()
    second['lesson'] = 2
    second['title'] = 'Another lesson'
    (destination / 'lesson-02/content.yaml').write_text(
        yaml.safe_dump(second, allow_unicode=True), encoding='utf-8')
    registry = CurriculumRegistry(tmp_path, ('grade03.unit01',))
    assert registry.get_lesson_script('grade03.unit01', 2).title == 'Another lesson'
