"""Deterministic progression for one Grade 3 scripted lesson session."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml
from luna_tutor.curriculum.lesson_content import (
    EndItem,
    PracticeItem,
    ScriptedLesson,
)
from luna_tutor.llm.jev_turn_evaluator import TurnEvaluation

_PROMPTS = yaml.safe_load((Path(__file__).resolve().parents[1]
                           / 'prompts/grade3_teacher_rules.yaml').read_text(encoding='utf-8'))
TEACHER_SYSTEM_PROMPT: str = _PROMPTS['system']


@dataclass(frozen=True)
class Say:
    text: str
    image_url: str | None = None


@dataclass(frozen=True)
class TeacherInstruction:
    code: TurnEvaluation
    learner_goal: str
    description: str
    attempt: int | None = None


OutputCommand = Say | TeacherInstruction
Phase = Literal['new', 'ready', 'delivering_teacher', 'delivering_script', 'completed']


class ScriptedLessonSession:
    """Own transitions, not language generation or transport delivery."""

    def __init__(self, lesson: ScriptedLesson):
        self.lesson = lesson
        self.phase: Phase = 'new'
        self.item_index = -1
        self.attempt_count = 0
        self.applied_turn_ids: set[str] = set()
        self._next_item_index: int | None = None
        self._advance_after_teacher = False

    @property
    def learner_goal(self) -> str:
        if self.phase != 'ready' or not isinstance(
            self.lesson.items[self.item_index], PracticeItem
        ):
            raise RuntimeError('No active learner goal')
        return self.lesson.items[self.item_index].learner_goal

    def start(self) -> list[Say]:
        if self.phase != 'new':
            raise RuntimeError('Lesson already started')
        return self._queue_script_from(0)

    def _queue_script_from(self, start: int) -> list[Say]:
        lines = []
        for index in range(start, len(self.lesson.items)):
            item = self.lesson.items[index]
            lines.append(Say(item.say, item.image_url))
            if isinstance(item, (PracticeItem, EndItem)):
                self._next_item_index = index
                self.phase = 'delivering_script'
                return lines
        raise RuntimeError('Script must end with an end item')

    def handle_turn(
        self, turn_id: str, query: str, evaluation: TurnEvaluation,
    ) -> list[OutputCommand]:
        if turn_id in self.applied_turn_ids:
            return []
        if self.phase != 'ready':
            raise RuntimeError('Lesson is not ready for a learner turn')
        if not turn_id or not query.strip():
            raise ValueError('A learner turn needs an ID and text')
        if not isinstance(evaluation, TurnEvaluation):
            raise ValueError('Invalid TurnEvaluation')

        goal = self.learner_goal
        self.applied_turn_ids.add(turn_id)
        if evaluation is TurnEvaluation.PASSED:
            return self._queue_script_from(self.item_index + 1)

        attempt = None
        if evaluation is TurnEvaluation.ATTEMPT_FAILED:
            self.attempt_count += 1
            attempt = self.attempt_count
            if attempt > 4:
                raise RuntimeError('No fifth failed attempt is allowed')

        rule = _PROMPTS['rules'][evaluation.value]
        if attempt is not None:
            rule = rule[attempt]
        self._advance_after_teacher = evaluation is TurnEvaluation.PASSED_WITH_REPLY or attempt == 4
        self.phase = 'delivering_teacher'
        return [TeacherInstruction(
            code=evaluation,
            learner_goal=goal,
            description=f'learner_goal hiện tại: {goal}\n\n{rule}',
            attempt=attempt,
        )]

    def delivery_finished(self) -> list[Say]:
        if self.phase == 'delivering_teacher':
            if self._advance_after_teacher:
                self._advance_after_teacher = False
                return self._queue_script_from(self.item_index + 1)
            self.phase = 'ready'
            return []
        if self.phase == 'delivering_script':
            assert self._next_item_index is not None
            self.item_index = self._next_item_index
            self._next_item_index = None
            if isinstance(self.lesson.items[self.item_index], EndItem):
                self.phase = 'completed'
            else:
                self.attempt_count = 0
                self.phase = 'ready'
            return []
        raise RuntimeError('Nothing is being delivered')
