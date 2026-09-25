"""Parse explicit language spans without leaking delivery markup to learners."""

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

LanguageCode = Literal['vi', 'en']
_TAG = re.compile(r'<(/?)([a-z]{2})>')
_TAG_LIKE = re.compile(r'</?[A-Za-z][^>]*>')
_ADJACENT_SPANS = re.compile(r'(?<=\S)</(?:vi|en)><(?:vi|en)>(?=\S)')
_CUE = re.compile(r'\[[^\]]*\]')
_COMPLETE_TAGGED_SPAN = re.compile(r'<(vi|en)>.*?</\1>', re.DOTALL)
_BOLD = re.compile(r'\*\*([^*\n]+)\*\*')
_EMPHASIS = re.compile(r'(?<!\*)(\*{1,2})([^*\n]+)\1(?!\*)')
_SPOKEN_PUNCTUATION = {'!': '.', '…': '.', ':': ',', ';': ',', '—': ',', '–': ','}
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


def _clean_speech_fragment(fragment: str) -> str:
    cleaned = []
    for index, char in enumerate(fragment):
        category = unicodedata.category(char)
        in_word_apostrophe = (
            char == "'" and 0 < index < len(fragment) - 1
            and fragment[index - 1].isalpha() and fragment[index + 1].isalpha()
        )
        if (char.isspace() or char in '.,?' or in_word_apostrophe
                or category[0] in 'LMN'):
            cleaned.append(char)
        elif char in _SPOKEN_PUNCTUATION:
            cleaned.append(_SPOKEN_PUNCTUATION[char])
        elif (index > 0 and index < len(fragment) - 1
              and fragment[index - 1].isalnum() and fragment[index + 1].isalnum()):
            cleaned.append(' ')
    return ''.join(cleaned)


def _clean_speech_text(text: str, *, visual_emphasis: bool) -> str:
    text = _CUE.sub('', _TAG_LIKE.sub('', _ADJACENT_SPANS.sub(' ', text)))
    pieces = []
    position = 0
    for match in _EMPHASIS.finditer(text):
        pieces.append(_clean_speech_fragment(text[position:match.start()]))
        emphasized = _clean_speech_fragment(match.group(2)).strip()
        if emphasized:
            pieces.append(f'**{emphasized}**' if visual_emphasis else emphasized)
        position = match.end()
    pieces.append(_clean_speech_fragment(text[position:]))
    return ''.join(pieces)


def plain_speech_text(text: str) -> str:
    """Preserve authored lines and visual emphasis without delivery or stray symbols."""
    return _clean_speech_text(text, visual_emphasis=True)


def tts_speech_text(text: str) -> str:
    """Send spoken words to TTS without authored punctuation or symbols."""
    spoken = _clean_speech_text(text, visual_emphasis=False)
    return re.sub(r'\s+', ' ', re.sub(r'[.,?]+', ' ', spoken)).strip()


def validate_tagged_teacher_speech(text: str) -> None:
    """Require every generated word to have a valid language and audible content."""
    spans = list(_COMPLETE_TAGGED_SPAN.finditer(text))
    if not spans or _COMPLETE_TAGGED_SPAN.sub('', text).strip():
        raise ValueError('Teacher speech needs valid language markup and speakable text')
    try:
        parsed = parse_speech_segments(text)
    except ValueError as error:
        raise ValueError('Teacher speech needs valid language markup and speakable text') from error
    if not plain_speech_text(text).strip():
        raise ValueError('Teacher speech needs valid language markup and speakable text')
    for span in parsed:
        spoken = _BOLD.sub(r'\1', span.text)
        for index, char in enumerate(spoken):
            category = unicodedata.category(char)
            in_word_apostrophe = (
                char == "'" and 0 < index < len(spoken) - 1
                and spoken[index - 1].isalpha() and spoken[index + 1].isalpha()
            )
            if (char.isspace() or char in '.,?' or in_word_apostrophe
                    or category[0] in 'LMN'):
                continue
            raise ValueError('Teacher speech has unsupported speech symbols')
