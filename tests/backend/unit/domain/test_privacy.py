import pytest
from luna_tutor.domain.privacy import (
    SanitizedText,
    redact_address_practice,
    redact_sensitive_contact,
)
from pydantic import TypeAdapter, ValidationError


@pytest.mark.parametrize('phone', [
    '0912345678', '0912 345 678', '0912.345.678', '0912-345-678',
    '+84 912 345 678', '+84 (0) 912 345 678', '+1 (202) 555-0123',
    '(020) 7946 0958', '202 555 0123', '555-0123', '０９１２３４５６７８',
    '0912\u00a0345\u00a0678', '0912\u202f345\u202f678', '0912-34-56',
])
def test_redacts_likely_phone_without_retaining_digits(phone):
    result = redact_sensitive_contact(f'My number is {phone}. I live in the city.')
    assert result.text == 'My number is [REDACTED_PHONE]. I live in the city.'
    assert result.safety_event is True
    assert not any(character.isdecimal() for character in result.model_dump_json())


@pytest.mark.parametrize('text', [
    'I was born in 2015.', 'I am in class 5A.', 'My birthday is 19-09-2015.',
    'I lived here in 2019 2020.', 'There are 19 words and 5 classes.',
    'My birthday is 2015-09-19.',
    'phone number', '', '[REDACTED_PHONE]',
])
def test_preserves_non_contact_text(text):
    result = redact_sensitive_contact(text)
    assert result.text == text
    assert result.safety_event is False


def test_redacts_every_contact_and_is_idempotent():
    result = redact_sensitive_contact('0912345678 or +1-202-555-0123')
    assert result.text == '[REDACTED_PHONE] or [REDACTED_PHONE]'
    assert redact_sensitive_contact(result.text).text == result.text


@pytest.mark.parametrize(('text', 'expected'), [
    ('My phone is0912345678.', 'My phone is[REDACTED_PHONE].'),
    ('Call 0912345678please.', 'Call [REDACTED_PHONE]please.'),
    ('0912 345 678please', '[REDACTED_PHONE]please'),
    ('Call0912.345.678please', 'Call[REDACTED_PHONE]please'),
])
def test_redacts_entire_contact_span_even_when_words_adjoin_it(text, expected):
    result = redact_sensitive_contact(text)
    assert result.text == expected
    assert result.safety_event is True
    assert not any(char.isdecimal() for char in result.model_dump_json())
    with pytest.raises(ValidationError):
        TypeAdapter(SanitizedText).validate_python(text)
    assert TypeAdapter(SanitizedText).validate_python(result.text) == expected


@pytest.mark.parametrize('separator', ['. ', '.\t', '.\u00a0', '.\u202f', '.\n'])
def test_contact_stops_before_sentence_boundary_and_preserves_following_year(separator):
    text = f'My phone is 0912 345 678{separator}2015 is my birth year.'
    result = redact_sensitive_contact(text)
    assert result.text == f'My phone is [REDACTED_PHONE]{separator}2015 is my birth year.'
    assert result.safety_event is True


@pytest.mark.parametrize('text', [
    'I studied in 2025-2026.', 'I studied in 2025 - 2026.',
    'I studied in 2025–2026.', 'I am in class5A.', '5A and 6B',
])
def test_preserves_school_year_ranges_and_short_class_identifiers(text):
    result = redact_sensitive_contact(text)
    assert result.text == text
    assert result.safety_event is False
    assert TypeAdapter(SanitizedText).validate_python(text) == text


def test_fictional_address_practice_preserves_only_reviewed_examples():
    examples = ("It's 23 Green Street.", "It's 38 Park Road.")

    safe = redact_address_practice(
        "It's 23 Green Street.",
        activity_id="lesson-02.fictional-address",
        safe_examples=examples,
    )
    assert safe.text == "It's 23 Green Street."
    assert not safe.safety_event

    learner_address = "I live at 19 River Lane."
    removed = redact_address_practice(
        learner_address,
        activity_id="lesson-02.fictional-address",
        safe_examples=examples,
    )
    assert removed.text == "[REDACTED_ADDRESS]"
    assert removed.safety_event
    assert learner_address not in repr(removed)


def test_address_redaction_is_contextual_not_a_general_home_filter():
    text = "My house has a garden and two floors."
    result = redact_address_practice(
        text,
        activity_id="lesson-01.home-type",
        safe_examples=("It's 23 Green Street.",),
    )
    assert result.text == text
    assert not result.safety_event
