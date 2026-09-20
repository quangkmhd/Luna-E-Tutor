"""Local digit-based contact redaction; never returns captured phone digits."""

import re
import unicodedata
from datetime import date
from typing import Annotated

from pydantic import AfterValidator

from luna_tutor.domain.contracts import Contract

# Digit boundaries keep a whole contact even when a word adjoins it. Only
# horizontal separators are allowed; a dot must directly precede another
# digit, so sentence-ending punctuation cannot swallow the next sentence.
_PHONE = re.compile(
    r'(?<!\d)(?:\+?\d|\(\d{2,4}\))'
    r'(?:[\d() \t\u00a0\u202f-]|\.(?=\d))*\d(?!\d)'
)
_DATE = re.compile(r'(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}-\d{1,2}-\d{4})')
_YEARS = re.compile(
    r'(?:19|20)\d{2}(?:(?:[ \t]+|[ \t]*-[ \t]*)(?:19|20)\d{2})*'
)


class RedactedText(Contract):
    text: str
    safety_event: bool


def _ordinary_date(candidate: str) -> bool:
    if not _DATE.fullmatch(candidate):
        return False
    parts = candidate.split('-')
    year, month, day = (parts if len(parts[0]) == 4 else reversed(parts))
    if not 1900 <= int(year) <= 2099:
        return False
    try:
        date(int(year), int(month), int(day))
    except ValueError:
        return False
    return True


def redact_sensitive_contact(text: str) -> RedactedText:
    """Replace phone-like digit sequences, preserving years and class labels.

    This is a conservative contact heuristic, not a general PII detector.
    Seven or more digits are treated as contact-like unless they form an
    ordinary date or a sequence of years. No matches or original text are
    retained in the returned object, including its representation.
    """
    if not isinstance(text, str):
        raise TypeError('Contact redaction requires text')
    safety_event = False

    def replace(match: re.Match[str]) -> str:
        nonlocal safety_event
        candidate = match.group()
        if (_ordinary_date(candidate) or _YEARS.fullmatch(candidate)
                or sum(char.isdecimal() for char in candidate) < 7):
            return candidate
        safety_event = True
        return '[REDACTED_PHONE]'

    sanitized = _PHONE.sub(replace, text)
    return RedactedText(text=sanitized, safety_event=safety_event)


def _normalize_spoken_text(text: str) -> str:
    normalized = unicodedata.normalize('NFKC', text).casefold().strip()
    return re.sub(r'\s+', ' ', normalized)


def redact_address_practice(
        text: str, *, activity_id: str,
        safe_examples: tuple[str, ...]) -> RedactedText:
    """Allow reviewed fictional examples, but discard other address practice.

    Address-shaped free text is only sensitive in the single curriculum
    activity that explicitly asks for a fictional address. Keeping this
    contextual avoids treating ordinary descriptions of a home as private.
    """
    if not isinstance(text, str):
        raise TypeError('Address redaction requires text')
    if activity_id != 'lesson-02.fictional-address':
        return RedactedText(text=text, safety_event=False)
    normalized = _normalize_spoken_text(text)
    if normalized in {_normalize_spoken_text(item) for item in safe_examples}:
        return RedactedText(text=text, safety_event=False)
    return RedactedText(text='[REDACTED_ADDRESS]', safety_event=True)


def _require_sanitized(text: str) -> str:
    if redact_sensitive_contact(text).safety_event:
        raise ValueError('Contact text must be locally redacted first')
    return text


SanitizedText = Annotated[str, AfterValidator(_require_sanitized)]
