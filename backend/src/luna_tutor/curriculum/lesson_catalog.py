"""Grade 3 lesson discovery without interpreting author-owned lesson goals."""

from pathlib import Path

import yaml

from luna_tutor.curriculum.lesson_content import ScriptedLesson, load_scripted_lesson

GRADE3_UNIT_ID = 'grade03.unit01'


class ScriptedCatalog:
    def __init__(self, root: Path):
        self.root = root
        self.unit_path = root / 'grade-03/unit-01'
        manifest = yaml.safe_load((self.unit_path / 'unit.yaml').read_text(encoding='utf-8'))
        if manifest['id'] != GRADE3_UNIT_ID or manifest['grade'] != 3 or manifest['unit'] != 1:
            raise ValueError('Grade 3 Unit 1 metadata mismatch')
        self.unit = {
            'id': GRADE3_UNIT_ID,
            'grade': 3,
            'unit': 1,
            'title': manifest['title'],
        }

    def units(self) -> list[dict]:
        return [self.unit.copy()]

    def lessons(self, unit_id: str) -> list[dict]:
        if unit_id != GRADE3_UNIT_ID:
            raise LookupError(unit_id)
        result = []
        for path in sorted(self.unit_path.glob('lesson-*/content.yaml')):
            content = yaml.safe_load(path.read_text(encoding='utf-8'))
            if not isinstance(content, dict) or not isinstance(content.get('lesson'), int):
                continue
            if path.parent.name != f"lesson-{content['lesson']:02d}":
                raise ValueError(f'Lesson ID does not match directory: {path}')
            result.append({'lesson': content['lesson'], 'title': content['title']})
        return result

    def load(self, unit_id: str, lesson_id: int) -> ScriptedLesson:
        if unit_id != GRADE3_UNIT_ID or lesson_id not in {
            item['lesson'] for item in self.lessons(GRADE3_UNIT_ID)
        }:
            raise LookupError(f'{unit_id}.lesson{lesson_id:02d}')
        return load_scripted_lesson(
            self.unit_path / f'lesson-{lesson_id:02d}' / 'content.yaml')
