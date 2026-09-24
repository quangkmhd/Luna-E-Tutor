"""One active lesson's shared Jev, Teacher, and delivery boundary."""

import asyncio
from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Literal

from luna_tutor.curriculum.lesson_content import ScriptedLesson
from luna_tutor.teaching.lesson_progression import (
    Say,
    ScriptedLessonSession,
    TeacherInstruction,
)


@dataclass(frozen=True)
class Spoken:
    text: str
    kind: Literal['say', 'teacher']
    image_url: str | None = None


class ScriptedConversation:
    def __init__(self, lesson: ScriptedLesson, evaluator, teacher,
                 *, mode: Literal['text', 'voice']):
        self.controller = ScriptedLessonSession(lesson)
        self.evaluator = evaluator
        self.teacher = teacher
        self.mode = mode
        self._pending: list[Spoken] = []
        self._result_by_id: dict[str, list[Spoken]] = {}
        self._lock = asyncio.Lock()

    def start(self) -> list[Spoken]:
        output = self._publish_says(self.controller.start())
        if self.mode == 'text':
            self.delivery_finished()
        return output

    async def submit(self, turn_id: str, query: str) -> list[Spoken]:
        async with self._lock:
            if turn_id in self._result_by_id:
                return self._result_by_id[turn_id] if self.mode == 'text' else []
            if not turn_id or not query.strip():
                raise ValueError('A learner turn needs an ID and text')
            goal = self.controller.learner_goal
            history = self.teacher.jev_history()
            evaluation = await self.evaluator.evaluate_turn(
                learner_goal=goal,
                learner_query=query,
                history=history,
                turn_id=turn_id,
            )
            proposed = deepcopy(self.controller)
            commands = proposed.handle_turn(turn_id, query, evaluation)
            if not commands:
                return []
            if isinstance(commands[0], TeacherInstruction):
                snapshot = self.teacher.snapshot()
                try:
                    self.teacher.record_query(query)
                    instruction = commands[0]
                    if self.mode == 'text':
                        instruction = replace(
                            instruction,
                            description=instruction.description + (
                                '\n\nKênh hiện tại là Text: học sinh gõ câu trả lời và chỉ thấy chữ Luna hiển thị. '
                                'Không bảo học sinh nghe cô đọc, nói theo tiếng cô hoặc nhìn miệng cô; '
                                'khi đưa mẫu, viết mẫu bằng chữ. Chỉ mời học sinh trả lời lại bằng chữ '
                                'nếu rule của lượt này yêu cầu thử lại; nếu rule yêu cầu kết thúc lượt, '
                                'không mời học sinh thử lại.'
                            ),
                        )
                    response = await self.teacher.respond(instruction)
                except Exception:
                    self.teacher.restore(snapshot)
                    raise
                self.controller = proposed
                output = [Spoken(response, 'teacher')]
                self._pending = output
            else:
                self.teacher.record_query(query)
                self.controller = proposed
                output = self._publish_says(commands)
            if self.mode == 'text':
                next_output = self.delivery_finished()
                while next_output:
                    output.extend(next_output)
                    next_output = self.delivery_finished()
            self._result_by_id[turn_id] = output
            return output

    def _publish_says(self, commands: list[Say]) -> list[Spoken]:
        result = [Spoken(command.text, 'say', command.image_url) for command in commands]
        self._pending = result
        return result

    def delivery_finished(self) -> list[Spoken]:
        if not self._pending:
            raise RuntimeError('No output is pending delivery')
        for output in self._pending:
            if output.kind == 'say':
                self.teacher.record_say(output.text)
            else:
                self.teacher.record_output(output.text)
        self._pending = []
        commands = self.controller.delivery_finished()
        return self._publish_says(commands) if commands else []
