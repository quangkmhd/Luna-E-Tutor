from pathlib import Path

import pytest
import yaml

from luna_tutor.curriculum.lesson_content import load_scripted_lesson


def _write(tmp_path: Path, items: list[dict]) -> Path:
    path = tmp_path / 'content.yaml'
    path.write_text(yaml.safe_dump({
        'lesson': 1,
        'title': 'Hello',
        'items': items,
    }, allow_unicode=True), encoding='utf-8')
    return path


def test_reads_ordered_script_items_and_preserves_authored_say(tmp_path):
    lesson = load_scripted_lesson(_write(tmp_path, [
        {'type': 'narration', 'say': '<vi>Vào bài.</vi>'},
        {'type': 'practice', 'say': '<en>Say hello.</en>',
         'learner_goal': 'Học sinh nói Hello.'},
        {'type': 'end', 'say': '<vi>Hết bài.</vi>'},
    ]))
    assert [item.type for item in lesson.items] == ['narration', 'practice', 'end']
    assert lesson.items[1].say == '<en>Say hello.</en>'
    assert lesson.items[1].learner_goal == 'Học sinh nói Hello.'


@pytest.mark.parametrize('items', [
    [{'type': 'practice', 'say': 'Say hello.'}, {'type': 'end', 'say': 'Done.'}],
    [{'type': 'narration', 'say': 'Hello.', 'learner_goal': 'Reply.'},
     {'type': 'end', 'say': 'Done.'}],
    [{'type': 'practice', 'say': 'Say hello.', 'learner_goal': 'Reply.',
      'accept': 'Hello'}, {'type': 'end', 'say': 'Done.'}],
    [{'type': 'practice', 'say': 'Say hello.', 'learner_goal': 'Reply.'}],
    [{'type': 'end', 'say': 'Done.'},
     {'type': 'practice', 'say': 'Say hello.', 'learner_goal': 'Reply.'}],
    [{'type': 'practice', 'say': 'Say hello.', 'learner_goal': 'Reply.'},
     {'type': 'end', 'say': '<en>Done.</vi>'}],
])
def test_rejects_invalid_script_instead_of_inventing_goal(tmp_path, items):
    with pytest.raises(ValueError, match='content.yaml'):
        load_scripted_lesson(_write(tmp_path, items))
