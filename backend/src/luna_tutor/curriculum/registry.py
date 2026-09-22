"""Validated access to the allow-listed curriculum collection."""

import re
from dataclasses import dataclass
from pathlib import Path
import yaml

from luna_tutor.curriculum.loader import load_unit
from luna_tutor.curriculum.lesson_script import LessonScript, load_lesson_script
from luna_tutor.curriculum.models import UnitCurriculum

_UNIT_ID = re.compile(r"^grade(?P<grade>\d{2})\.unit(?P<unit>\d{2})$")
SUPPORTED_UNIT_IDS = ('grade03.unit01',) + tuple(
    f'grade05.unit{number:02d}' for number in range(1, 6)
)


@dataclass(frozen=True)
class UnitSummary:
    id: str
    grade: int
    unit: int
    title: str


class UnknownUnitError(LookupError):
    pass


def _parse_unit_id(unit_id: str) -> tuple[int, int]:
    match = _UNIT_ID.fullmatch(unit_id)
    if match is None:
        raise ValueError(f"Invalid curriculum ID: {unit_id}")
    return int(match["grade"]), int(match["unit"])


class CurriculumRegistry:
    def __init__(self, root: Path, allowed_ids: tuple[str, ...]):
        loaded = {}
        self._lesson_scripts: dict[tuple[str, int], LessonScript] = {}
        for unit_id in allowed_ids:
            grade, unit = _parse_unit_id(unit_id)
            curriculum = load_unit(
                root / f"grade-{grade:02d}" / f"unit-{unit:02d}"
            )
            if curriculum.id != unit_id:
                raise ValueError(f"Curriculum ID mismatch for {unit_id}")
            loaded[unit_id] = curriculum
            if unit_id == 'grade03.unit01':
                for lesson_file in sorted((root / 'grade-03/unit-01').glob('lesson-*/content.yaml')):
                    content = yaml.safe_load(lesson_file.read_text(encoding='utf-8'))
                    if not isinstance(content, dict) or 'lesson' not in content:
                        continue
                    script = load_lesson_script(lesson_file)
                    if lesson_file.parent.name != f'lesson-{script.lesson:02d}':
                        raise ValueError(f'Lesson ID does not match directory: {lesson_file}')
                    self._lesson_scripts[(unit_id, script.lesson)] = script
        self._units = loaded

    def list_units(self) -> tuple[UnitSummary, ...]:
        return tuple(
            UnitSummary(
                id=item.id,
                grade=item.grade,
                unit=item.unit,
                title=item.title,
            )
            for item in sorted(
                self._units.values(), key=lambda value: (value.grade, value.unit)
            )
        )

    def get(self, unit_id: str) -> UnitCurriculum:
        try:
            return self._units[unit_id]
        except KeyError as error:
            raise UnknownUnitError(unit_id) from error

    def get_lesson_script(self, unit_id: str, lesson_id: int) -> LessonScript:
        try:
            return self._lesson_scripts[(unit_id, lesson_id)]
        except KeyError as error:
            raise UnknownUnitError(f'{unit_id}.lesson{lesson_id:02d}') from error

    def list_lesson_scripts(self, unit_id: str) -> tuple[LessonScript, ...]:
        return tuple(script for (owner, _), script in sorted(self._lesson_scripts.items())
                     if owner == unit_id)
