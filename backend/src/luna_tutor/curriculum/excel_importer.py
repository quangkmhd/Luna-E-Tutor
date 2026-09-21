"""Import the supplied Global Success workbook layout without crossing Unit scope.

This is a content importer, not an activity generator. Imported objectives can be
reviewed before being used to author teaching activities and completion rules.
"""

import re
import unicodedata
from pathlib import Path

from openpyxl import load_workbook

from luna_tutor.curriculum.models import (
    ImportedLesson,
    ImportedUnit,
    Objective,
    Pattern,
    VocabularyItem,
)


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', ascii_text.lower()).strip('-')


def _pattern_id(text: str) -> str:
    """Use semantic IDs for Unit 1 targets, text-derived IDs for other targets."""
    normalized = text.lower().replace('’', "'")
    for phrase, identifier in [
        ('however', 'however'), ('moreover', 'moreover'),
        ("it's calm and the air is fresh", 'describe-countryside'),
        ("when's your birthday", 'birthday'), ("what's your hobby", 'hobby'),
        ("what's your favourite", 'favourite'), ("i'm in", 'class'),
        ('i live in the ___', 'live-in'),
    ]:
        if phrase in normalized:
            return identifier
    return 'pattern-' + _slug(text)


def _is_review(value: str) -> bool:
    normalized = _slug(value)
    return normalized.startswith(('on-tap', 'on-lai', 'review'))


def _split_vocabulary(text: str, *, grade: int, unit: int,
                      row: int, column: int) -> list[str]:
    """Split reviewed vocabulary cells without turning labels into targets."""
    items = [item.strip() for item in re.split(r'[,;\n]', text) if item.strip()]
    if (grade, unit, row, column) == (5, 2, 6, 4) and items:
        items[0] = items[0].removeprefix('numbers ').strip()
    if (grade, unit, row, column) == (5, 4, 11, 8):
        expanded = []
        for item in items:
            if item == 'percussion/wind/string instruments':
                expanded.extend([
                    'percussion instruments', 'wind instruments', 'string instruments',
                ])
            else:
                expanded.append(item)
        items = expanded
    return items


def import_workbook(path: Path, grade: int, unit: int) -> ImportedUnit:
    """Read one bounded Unit from its grade sheet, resolving review references.

    Blank and merged Unit cells inherit only the current explicit Unit heading.
    Level 2/3 are read once at unit scope, including later nonblank anchors. Blank
    lesson cells never inherit another lesson's vocabulary or sentence patterns.
    """
    workbook = load_workbook(path, data_only=True)
    try:
        matches = [sheet for sheet in workbook if re.match(rf'^Lớp\s+{grade}\s*\(', sheet.title)]
        if len(matches) != 1:
            raise ValueError(f'Grade {grade} sheet not found uniquely')
        sheet = matches[0]
        start = end = None
        title = ''
        for row in range(2, sheet.max_row + 1):
            value = str(sheet.cell(row, 1).value or '')
            heading = re.match(r'^Unit\s+(\d+)\s*:', value, re.IGNORECASE)
            if not heading:
                continue
            if start is not None:
                end = row
                break
            if int(heading.group(1)) == unit:
                start, title = row, value.split('\n')[0].split(':', 1)[1].strip()
        if start is None:
            raise ValueError(f'Unit {unit} not found in Grade {grade}')
        end = end or sheet.max_row + 1
        def cell(row: int, column: int):
            value = sheet.cell(row, column).value
            if value is not None:
                return str(value), row
            for merged in sheet.merged_cells.ranges:
                if (merged.min_row <= row <= merged.max_row
                        and merged.min_col <= column <= merged.max_col
                        and start <= merged.min_row < end):
                    # An anchor outside this Unit cannot provide content to it.
                    anchor = sheet.cell(merged.min_row, merged.min_col).value
                    return str(anchor or ''), merged.min_row
            return '', row

        vocabulary: dict[str, VocabularyItem] = {}
        patterns: dict[str, Pattern] = {}
        objectives: dict[str, Objective] = {}
        lessons: list[ImportedLesson] = []
        reviews: list[tuple[ImportedLesson, list[int]]] = []

        def add_content(text: str, scope: str, row: int, column: int, kind: str) -> list[str]:
            if not text or _is_review(text) or text.startswith('—'):
                return []
            items = (_split_vocabulary(
                text, grade=grade, unit=unit, row=row, column=column)
                if kind == 'vocabulary'
                else [item.strip() for item in re.split(
                    r'[;\n]' if column == 5 else r'\n', text) if item.strip()])
            ids = []
            for item_text in items:
                identifier = _slug(item_text) if kind == 'vocabulary' else _pattern_id(item_text)
                if kind == 'pattern':
                    base_identifier = identifier
                    suffix = 2
                    while identifier in patterns and patterns[identifier].text != item_text:
                        identifier = f'{base_identifier}-{suffix}'
                        suffix += 1
                objective_id = f'unit{unit:02d}.{scope}.{kind}.{identifier.replace("-", "_")}'
                if kind == 'vocabulary':
                    vocabulary.setdefault(identifier, VocabularyItem(id=identifier, text=item_text))
                    kwargs = {'vocabulary_ids': [identifier]}
                    criteria = f'Understand or use {item_text} in context; imitation alone is not independent use.'
                else:
                    patterns.setdefault(identifier, Pattern(id=identifier, text=item_text))
                    kwargs = {'pattern_ids': [identifier]}
                    criteria = 'Record communicative meaning and target form separately; accept valid alternatives.'
                objectives.setdefault(objective_id, Objective(
                    id=objective_id, description=f'{kind.title()}: {item_text}',
                    evidence_criteria=criteria, **kwargs,
                ))
                if objective_id not in ids:
                    ids.append(objective_id)
            return ids

        for row in range(start, end):
            lesson_match = re.match(r'Lesson\s+(\d+)', str(sheet.cell(row, 2).value or ''), re.IGNORECASE)
            if not lesson_match:
                continue
            number = int(lesson_match.group(1))
            scope = f'lesson{number:02d}'
            lesson = ImportedLesson(lesson=number, objective_ids=[])
            vocabulary_text, vocabulary_row = cell(row, 4)
            pattern_text, pattern_row = cell(row, 5)
            if _is_review(vocabulary_text) or _is_review(pattern_text):
                explicit = re.search(r'Lesson\s+(\d+(?:\s*\+\s*\d+)*)', vocabulary_text, re.IGNORECASE)
                targets = [int(n) for n in re.findall(r'\d+', explicit.group(1))] if explicit else [l.lesson for l in lessons]
                reviews.append((lesson, targets))
            else:
                lesson.objective_ids.extend(add_content(vocabulary_text, scope, vocabulary_row, 4, 'vocabulary'))
                lesson.objective_ids.extend(add_content(pattern_text, scope, pattern_row, 5, 'pattern'))
            lessons.append(lesson)
        lesson_map = {lesson.lesson: lesson for lesson in lessons}
        if len(lesson_map) != len(lessons):
            raise ValueError('Duplicate Lesson numbers inside Unit')
        for lesson, targets in reviews:
            if any(target not in lesson_map or target >= lesson.lesson for target in targets):
                raise ValueError('Review Lesson references must resolve to earlier Lessons in this Unit')
            lesson.objective_ids = list(dict.fromkeys(oid for target in targets for oid in lesson_map[target].objective_ids))
        # Merged/blank extensions belong to the Unit, never to each Lesson.
        for level, vocabulary_column, pattern_column in [(2, 6, 7), (3, 8, 9)]:
            for column, kind in [(vocabulary_column, 'vocabulary'), (pattern_column, 'pattern')]:
                seen = set()
                for row in range(start, end):
                    text, anchor = cell(row, column)
                    if text and text not in seen:
                        seen.add(text)
                        add_content(text, f'level{level:02d}', anchor, column, kind)
        return ImportedUnit(
            grade=grade, unit=unit, title=title,
            vocabulary=list(vocabulary.values()), patterns=list(patterns.values()),
            objectives=list(objectives.values()), lessons=lessons,
        )
    finally:
        workbook.close()
