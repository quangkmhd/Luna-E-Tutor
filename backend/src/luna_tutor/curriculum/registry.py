"""Validated access to the allow-listed curriculum collection."""

import re
from dataclasses import dataclass
from pathlib import Path

from luna_tutor.curriculum.loader import load_unit
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
        for unit_id in allowed_ids:
            grade, unit = _parse_unit_id(unit_id)
            curriculum = load_unit(
                root / f"grade-{grade:02d}" / f"unit-{unit:02d}"
            )
            if curriculum.id != unit_id:
                raise ValueError(f"Curriculum ID mismatch for {unit_id}")
            loaded[unit_id] = curriculum
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
