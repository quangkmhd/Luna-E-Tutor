"""Parse explicit language spans without leaking delivery markup to learners."""

import logging
import re
from dataclasses import dataclass
from typing import Literal

LanguageCode = Literal['vi', 'en']
_TAG = re.compile(r'<(/?)([a-z]{2})>')
_TAG_LIKE = re.compile(r'</?[A-Za-z][^>]*>')
_CUE = re.compile(r'\[[^\]]*\]')
_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpeechSegment:
    language: LanguageCode
    text: str


def _parse(text: str) -> tuple[SpeechSegment, ...]:
    active: LanguageCode | None = None
    pieces: list[tuple[LanguageCode, str]] = []
    position = 0
    for candidate in _TAG_LIKE.finditer(text):
        tag = _TAG.fullmatch(candidate.group())
        if tag is None:
            raise ValueError(f'Unsupported language tag {candidate.group()}')
        language = tag.group(2)
        if language not in ('vi', 'en'):
            raise ValueError(f'Unsupported language tag <{language}>')
        pieces.append((active or 'vi', text[position:candidate.start()]))
        if tag.group(1):
            if active != language:
                raise ValueError(f'Mismatched language tag </{language}>')
            active = None
        else:
            if active is not None:
                raise ValueError(f'Nested language tag <{language}>')
            active = language
        position = candidate.end()
    if active is not None:
        raise ValueError(f'Unclosed language tag <{active}>')
    pieces.append(('vi', text[position:]))

    merged: list[tuple[LanguageCode, str]] = []
    for language, fragment in pieces:
        if merged and merged[-1][0] == language:
            merged[-1] = (language, merged[-1][1] + fragment)
        else:
            merged.append((language, fragment))
    return tuple(SpeechSegment(language, fragment.strip()) for language, fragment in merged
                 if fragment.strip())


def parse_speech_segments(text: str, *, strict: bool = True) -> tuple[SpeechSegment, ...]:
    """Return ordered Soniox streams; malformed generated text safely falls back to VI."""
    try:
        return _parse(text)
    except ValueError:
        if strict:
            raise
        _logger.warning('Invalid language markup in generated teacher speech; using Vietnamese')
        clean = _TAG_LIKE.sub('', text).strip()
        return (SpeechSegment('vi', clean),) if clean else ()


def plain_speech_text(text: str) -> str:
    """Keep authored spacing/newlines while hiding language and TTS delivery tokens."""
    return _CUE.sub('', _TAG_LIKE.sub('', text))
