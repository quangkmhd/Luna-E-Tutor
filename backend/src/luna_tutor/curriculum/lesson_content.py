"""Authoring contract for a Grade 3 scripted lesson."""

from pathlib import Path
from typing import Annotated, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from luna_tutor.speech.language_segments import parse_speech_segments, plain_speech_text


class _Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class _SpokenItem(_Strict):
    say: str = Field(min_length=1)
    image_url: str | None = None

    @field_validator('say')
    @classmethod
    def valid_speech(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('say must not be blank')
        parse_speech_segments(value)
        if not plain_speech_text(value).strip():
            raise ValueError('say has no speakable text after removing TTS cues')
        return value


class PracticeItem(_SpokenItem):
    type: Literal['practice']
    learner_goal: str = Field(min_length=1)

    @field_validator('learner_goal')
    @classmethod
    def valid_goal(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('learner_goal must not be blank')
        return value


class NarrationItem(_SpokenItem):
    type: Literal['narration']


class EndItem(_SpokenItem):
    type: Literal['end']


ScriptItem = Annotated[PracticeItem | NarrationItem | EndItem, Field(discriminator='type')]


class VocabularyCard(_Strict):
    word: str = Field(min_length=1)
    pronunciation: str | None = None
    meaning_vi: str | None = None
    image_url: str | None = None


class ScriptedLesson(_Strict):
    lesson: int = Field(ge=1)
    title: str = Field(min_length=1)
    items: list[ScriptItem] = Field(min_length=2)
    cards: list[VocabularyCard] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_sequence(self) -> Self:
        if not isinstance(self.items[-1], EndItem):
            raise ValueError('last item must be end')
        if any(isinstance(item, EndItem) for item in self.items[:-1]):
            raise ValueError('end must occur only at the end')
        if not any(isinstance(item, PracticeItem) for item in self.items):
            raise ValueError('lesson needs a practice item')
        return self


def load_scripted_lesson(path: Path) -> ScriptedLesson:
    try:
        return ScriptedLesson.model_validate(yaml.safe_load(path.read_text(encoding='utf-8')))
    except (ValueError, yaml.YAMLError) as error:
        raise ValueError(f'Invalid scripted lesson {path}: {error}') from error
