from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class SessionConfig(StrictModel):
    grade: Literal[5]
    topic: str = Field(min_length=1, max_length=120)
    words: tuple[str, ...]

    @field_validator('topic')
    @classmethod
    def normalize_topic(cls, value: str) -> str:
        value = ' '.join(value.split())
        if not value:
            raise ValueError('topic is required')
        return value

    @field_validator('words')
    @classmethod
    def normalize_words(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = []
        for raw in values:
            value = ' '.join(raw.split()).casefold()
            if not value or len(value) > 40:
                raise ValueError('each word must contain 1-40 characters')
            if value not in normalized:
                normalized.append(value)
        if not 1 <= len(normalized) <= 5:
            raise ValueError('choose 1-5 distinct words')
        return tuple(normalized)


class WordUse(StrictModel):
    word: str
    quote: str
    independent: bool = False


class Evidence(StrictModel):
    kind: Literal['answer', 'help', 'unclear', 'finish']
    independent: bool = False
    difficulty: bool = False
    word_uses: tuple[WordUse, ...] = ()


class Decision(StrictModel):
    action: Literal['finish', 'clarify', 'offer_choices', 'continue', 'expand']
    level: int = Field(ge=0, le=2)
    independent_streak: int = Field(ge=0)
    difficulty_streak: int = Field(ge=0)


class TurnInput(StrictModel):
    turn_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=2000)
    expected_version: int = Field(ge=0)
    quality: Literal['final', 'unclear'] = 'final'
    input_mode: Literal['text', 'voice'] = 'text'

    @field_validator('text')
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = ' '.join(value.split())
        if not value:
            raise ValueError('text is required')
        return value


class SpeakingState(StrictModel):
    session_id: str
    config: SessionConfig
    version: int = 0
    status: Literal['active', 'completed'] = 'active'
    level: int = Field(default=1, ge=0, le=2)
    independent_streak: int = 0
    difficulty_streak: int = 0
    word_evidence: tuple[WordUse, ...] = ()
    last_delivered_text: str = ''
    opening_message: str = ''
    messages: tuple['ConversationMessage', ...] = ()

    @classmethod
    def initial(cls, session_id: str, config: SessionConfig) -> 'SpeakingState':
        return cls(session_id=session_id, config=config)

    def with_decision(self, decision: Decision) -> 'SpeakingState':
        return self.model_copy(update={
            'level': decision.level,
            'independent_streak': decision.independent_streak,
            'difficulty_streak': decision.difficulty_streak,
        })


class Reply(StrictModel):
    text: str = Field(min_length=1, max_length=500)
    support_kind: str = 'none'


class ConversationMessage(StrictModel):
    role: Literal['learner', 'teacher']
    text: str
    turn_id: str | None = None


class TurnResult(StrictModel):
    state: SpeakingState
    reply: Reply


class Summary(StrictModel):
    state: SpeakingState
    independent: tuple[str, ...]
    supported: tuple[str, ...]
    unseen: tuple[str, ...]
    next_practice: str


class SuggestedWord(StrictModel):
    word: str
    meaning_vi: str
    example: str


class Suggestions(StrictModel):
    topic: str
    words: tuple[SuggestedWord, ...] = Field(max_length=8)
    clarification: str | None = None
