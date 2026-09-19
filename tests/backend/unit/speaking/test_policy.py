import pytest
from pydantic import ValidationError

from luna_tutor.speaking.models import Evidence, SessionConfig, SpeakingState, TurnInput
from luna_tutor.speaking.policy import decide


def state():
    return SpeakingState.initial('s1', SessionConfig(grade=5, topic='Animals', words=('rabbit',)))


def test_unclear_does_not_lower_level():
    result = decide(state(), Evidence(kind='unclear'))
    assert (result.level, result.action) == (1, 'clarify')


def test_three_independent_turns_raise_one_level():
    current = state()
    for _ in range(3):
        decision = decide(current, Evidence(kind='answer', independent=True))
        current = current.with_decision(decision)
    assert current.level == 2
    assert current.independent_streak == 0


def test_two_difficult_turns_lower_one_level():
    current = state()
    for _ in range(2):
        decision = decide(current, Evidence(kind='answer', difficulty=True))
        current = current.with_decision(decision)
    assert current.level == 0


def test_help_and_finish_are_immediate():
    assert decide(state(), Evidence(kind='help')).action == 'offer_choices'
    assert decide(state(), Evidence(kind='finish')).action == 'finish'


def test_duplicate_words_are_normalized():
    config = SessionConfig(grade=5, topic='  Food ', words=(' Juice ', 'juice', 'sandwich'))
    assert config.topic == 'Food'
    assert config.words == ('juice', 'sandwich')


@pytest.mark.parametrize('payload', [
    {'grade': 4, 'topic': 'Food', 'words': ('juice',)},
    {'grade': 5, 'topic': 'Food', 'words': ()},
    {'grade': 5, 'topic': 'Food', 'words': ('a', 'b', 'c', 'd', 'e', 'f')},
])
def test_invalid_session_config_is_rejected(payload):
    with pytest.raises(ValidationError):
        SessionConfig(**payload)


def test_turn_input_rejects_unknown_fields_and_long_text():
    with pytest.raises(ValidationError):
        TurnInput(turn_id='t1', text='hello', expected_version=0, surprise=True)
    with pytest.raises(ValidationError):
        TurnInput(turn_id='t1', text='x' * 2001, expected_version=0)
