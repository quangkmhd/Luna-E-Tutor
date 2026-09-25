import pytest
from luna_tutor.speech.language_segments import (
    SpeechSegment,
    parse_speech_segments,
    plain_speech_text,
    tts_speech_text,
    validate_tagged_teacher_speech,
)


def test_parses_ordered_language_segments_without_speaking_tags():
    text = '<vi>Xin chào.</vi> <en>[long pause] "HELLO"</en> <vi>con nhé.</vi>'
    assert parse_speech_segments(text) == (
        SpeechSegment('vi', 'Xin chào.'),
        SpeechSegment('en', '[long pause] "HELLO"'),
        SpeechSegment('vi', 'con nhé.'),
    )
    assert plain_speech_text(text) == 'Xin chào.  HELLO con nhé.'


def test_adjacent_language_spans_keep_word_boundaries_in_display_and_tts():
    text = ('<vi>Con biết câu hỏi thăm rất hay.</vi><en>How are you</en>'
            '<vi> là cách hỏi bạn bè. Con có thể dùng từ</vi>'
            '<en>Hello</en><vi>nhé.</vi><en>Say hello.</en>')
    assert plain_speech_text(text) == (
        'Con biết câu hỏi thăm rất hay. How are you là cách hỏi bạn bè. '
        'Con có thể dùng từ Hello nhé. Say hello.')
    assert tts_speech_text(text) == (
        'Con biết câu hỏi thăm rất hay How are you là cách hỏi bạn bè '
        'Con có thể dùng từ Hello nhé Say hello')


def test_visible_speech_keeps_only_double_star_emphasis_and_spoken_punctuation():
    text = '<en>[long pause] "*HELLO*"! Say **Hi** @Luna.</en>'
    assert plain_speech_text(text).strip() == '**HELLO**. Say **Hi** Luna.'
    assert tts_speech_text(text) == 'HELLO Say Hi Luna'


def test_tts_omits_nonspoken_symbols_without_joining_words():
    text = '<en>Hi! I\'m Luna — your tutor, #1 @ $5%... Ready?</en>'
    assert tts_speech_text(text) == "Hi I'm Luna your tutor 1 5 Ready"


def test_legacy_and_multiline_speech_keep_their_text():
    assert parse_speech_segments('Cô nói trước.\nCon nói sau.') == (
        SpeechSegment('vi', 'Cô nói trước.\nCon nói sau.'),
    )
    assert parse_speech_segments('<en>Listen first!\nHELLO</en><vi>  </vi>') == (
        SpeechSegment('en', 'Listen first!\nHELLO'),
    )


@pytest.mark.parametrize('text', [
    '<vi>Xin chào', '<en>Hello</vi>', '<vi>Xin <en>Hello</en></vi>', '</en>Hello',
    '<EN>Hello</EN>', '<en lang="x">Hello</en>', '<fr>Bonjour</fr>',
])
def test_rejects_malformed_authored_markup(text):
    with pytest.raises(ValueError, match='language tag'):
        parse_speech_segments(text)


def test_generated_malformed_markup_falls_back_to_vi_without_tags():
    assert parse_speech_segments('<en>Hello</vi> con', strict=False) == (
        SpeechSegment('vi', 'Hello con'),
    )
    assert parse_speech_segments('<EN>Hello</EN> con', strict=False) == (
        SpeechSegment('vi', 'Hello con'),
    )
    assert plain_speech_text('<EN>Hello</EN>') == 'Hello'


def test_generated_teacher_accepts_double_star_bold_and_plain_sentence_punctuation():
    validate_tagged_teacher_speech('<vi>Con nói **Hello**.</vi><en>Are you ready? I\'m ready.</en>')


@pytest.mark.parametrize('text', [
    '<en>Great!</en>',
    '<vi>Con nói @Hello.</vi>',
    '<en>Say *Hello*.</en>',
    '<en>Say **Hello*.</en>',
    '<en>Use (Hello).</en>',
])
def test_generated_teacher_rejects_disallowed_symbols(text):
    with pytest.raises(ValueError, match='unsupported speech symbols'):
        validate_tagged_teacher_speech(text)
