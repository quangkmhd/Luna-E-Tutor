import pytest

from luna_tutor.speech.language_segments import (
    SpeechSegment,
    parse_speech_segments,
    plain_speech_text,
)


def test_parses_ordered_language_segments_without_speaking_tags():
    text = '<vi>Xin chào.</vi> <en>[long pause] "HELLO"</en> <vi>con nhé.</vi>'
    assert parse_speech_segments(text) == (
        SpeechSegment('vi', 'Xin chào.'),
        SpeechSegment('en', '[long pause] "HELLO"'),
        SpeechSegment('vi', 'con nhé.'),
    )
    assert plain_speech_text(text) == 'Xin chào.  "HELLO" con nhé.'


def test_legacy_and_multiline_speech_keep_their_text():
    assert parse_speech_segments('Cô nói trước.\nCon nói sau.') == (
        SpeechSegment('vi', 'Cô nói trước.\nCon nói sau.'),
    )
    assert parse_speech_segments('<en>Listen first!\nHELLO</en><vi>  </vi>') == (
        SpeechSegment('en', 'Listen first!\nHELLO'),
    )


@pytest.mark.parametrize('text', [
    '<vi>Xin chào', '<en>Hello</vi>', '<vi>Xin <en>Hello</en></vi>', '</en>Hello',
])
def test_rejects_malformed_authored_markup(text):
    with pytest.raises(ValueError, match='language tag'):
        parse_speech_segments(text)


def test_generated_malformed_markup_falls_back_to_vi_without_tags():
    assert parse_speech_segments('<en>Hello</vi> con', strict=False) == (
        SpeechSegment('vi', 'Hello con'),
    )
