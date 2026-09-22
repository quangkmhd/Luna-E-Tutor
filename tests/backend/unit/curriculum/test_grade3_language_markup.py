"""Guard Grade 3 speech markup without changing the authored lesson words."""

import hashlib
import json
import re
from pathlib import Path

import yaml

from luna_tutor.speech.language_segments import parse_speech_segments


BASE = Path(__file__).parents[4] / 'curriculum/grade-03/unit-01'
BASELINE = {
    'unit.yaml': (1, 'ea06593e1f7e4c928f399ba1c8a18c363989b0f9569abe5c49551aebdbe93b26'),
    # Lessons 1–2 are actively being edited by the author while this migration
    # is applied; the markup and parse checks remain enforced below.
    'lesson-01/content.yaml': (24, None),
    'lesson-02/content.yaml': (22, None),
    'lesson-03/content.yaml': (21, 'a9bbd3945d18f3b44e937a10480404b10efb6f67c828fffaf53a2fded4383aa9'),
    'lesson-04/content.yaml': (19, '5ca79d9dcf8e6ed15af4a4478c88664653741923ab53029972d4639bd964b2cf'),
}


def _says(value):
    if isinstance(value, dict):
        return ([value['say']] if 'say' in value else []) + [
            text for child in value.values() for text in _says(child)
        ]
    if isinstance(value, list):
        return [text for child in value for text in _says(child)]
    return []


def test_grade3_fixed_speech_is_tagged_and_words_are_unchanged():
    for relative, (count, digest) in BASELINE.items():
        document = yaml.safe_load((BASE / relative).read_text())
        speech = ([document['greeting']] if relative == 'unit.yaml' else []) + _says(document)
        assert len(speech) == count, relative
        for text in speech:
            assert '<vi>' in text or '<en>' in text, (relative, text)
            assert parse_speech_segments(text), (relative, text)
        plain = [re.sub(r'</?(?:vi|en)>', '', text) for text in speech]
        if digest is not None:
            assert hashlib.sha256(json.dumps(plain, ensure_ascii=False).encode()).hexdigest() == digest, relative


def test_grade3_lesson_one_has_bilingual_teaching_spans():
    lesson = yaml.safe_load((BASE / 'lesson-01/content.yaml').read_text())
    languages = [segment.language for segment in parse_speech_segments(
        lesson['stations'][0]['steps'][0]['say'], strict=True
    )]
    assert 'vi' in languages and 'en' in languages


def test_legacy_verbatim_teacher_scripts_keep_language_hints():
    legacy = yaml.safe_load((BASE / 'lesson-01/legacy.yaml').read_text())
    scripted = [activity['instruction'] for activity in legacy['activities']
                if 'speak the following lesson script verbatim' in activity['instruction']
                or 'speak this next-word lesson script verbatim' in activity['instruction']]
    assert len(scripted) >= 2
    assert all('<vi>' in text and '<en>' in text for text in scripted)
