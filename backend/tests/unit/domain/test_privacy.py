import pytest

from luna_tutor.domain.privacy import redact_sensitive_contact


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
