"""Compact authoring contract for one Grade 3 lesson session."""

from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from luna_tutor.speech.language_segments import parse_speech_segments

from luna_tutor.curriculum.models import Text


class _Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Exchange(_Strict):
    say: Text
    accept: Text | None = None
    image_url: str | None = None

    @field_validator('say')
    @classmethod
    def check_language_tags(cls, value: str) -> str:
        parse_speech_segments(value)
        return value


class Greeting(_Strict):
    order: int = Field(ge=1)
    say: Text
    accept: Text
    image_url: str | None = None

    @field_validator('say')
    @classmethod
    def check_language_tags(cls, value: str) -> str:
        parse_speech_segments(value)
        return value


class TeachingStep(Exchange):
    order: int = Field(ge=2)
    target: Text | list[Text] | None = None
    attempts: int = Field(default=2, ge=1, le=5)
    more: list[Exchange] = Field(default_factory=list)


class LessonVocabularyCard(_Strict):
    word: Text
    pronunciation: str | None = None
    meaning_vi: str | None = None
    image_url: str | None = None


class StationScript(_Strict):
    id: Literal['vocabulary', 'patterns', 'conversation']
    steps: list[TeachingStep] = Field(min_length=1)


class LessonScript(_Strict):
    lesson: int = Field(ge=1)
    title: Text
    greeting: Greeting
    words: list[Text] = Field(default_factory=list)
    cards: list[LessonVocabularyCard] = Field(default_factory=list)
    patterns: dict[str, Text] = Field(default_factory=dict)
    stations: list[StationScript] = Field(min_length=3, max_length=3)

    @model_validator(mode='after')
    def check_script(self) -> Self:
        if self.greeting.order != 1:
            raise ValueError('Greeting must be order 1')
        if [station.id for station in self.stations] != ['vocabulary', 'patterns', 'conversation']:
            raise ValueError('Stations must be vocabulary, patterns, conversation')
        steps = [step for station in self.stations for step in station.steps]
        if [step.order for step in steps] != list(range(2, len(steps) + 2)):
            raise ValueError('Teaching item order must be consecutive across the lesson')
        targets = set(self.words) | set(self.patterns)
        for step in steps:
            selected = ([step.target] if isinstance(step.target, str) else step.target or [])
            if not set(selected) <= targets:
                raise ValueError(f'Unknown teaching target: {step.target}')
        if len(self.words) != len(set(self.words)):
            raise ValueError('Duplicate words')
        if len({card.word for card in self.cards}) != len(self.cards):
            raise ValueError('Duplicate vocabulary card words')
        if any(card.word not in self.words for card in self.cards):
            raise ValueError('Vocabulary cards must reference lesson words')
        if any(not any(exchange.accept for step in station.steps
                       for exchange in (step, *step.more)) for station in self.stations):
            raise ValueError('Each station needs a learner opportunity')
        return self

    def steps(self) -> tuple[TeachingStep, ...]:
        return tuple(step for station in self.stations for step in station.steps)

    def image_for_activity(self, activity_id: str | None) -> str | None:
        if not activity_id:
            return None
        if activity_id == f'lesson-{self.lesson:02d}.exchange-01':
            return self.greeting.image_url
        for step in self.steps():
            prefix = f'lesson-{step.order:02d}.exchange-'
            if not activity_id.startswith(prefix):
                continue
            suffix = activity_id.removeprefix(prefix)
            if not suffix.isdigit():
                return None
            index = int(suffix) - 1
            exchanges = (step, *step.more)
            return exchanges[index].image_url if 0 <= index < len(exchanges) else None
        return None


def load_lesson_script(path: Path) -> LessonScript:
    return LessonScript.model_validate(yaml.safe_load(path.read_text(encoding='utf-8')))
