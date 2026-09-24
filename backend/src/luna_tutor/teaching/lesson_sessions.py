"""Ephemeral Grade 3 sessions shared by Text and Voice entry points."""

import asyncio
from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

from luna_tutor.curriculum.lesson_catalog import GRADE3_UNIT_ID, ScriptedCatalog
from luna_tutor.teaching.lesson_conversation import ScriptedConversation, Spoken


@dataclass
class ScriptedSession:
    id: str
    unit_id: str
    lesson_id: int
    lesson_title: str
    conversation: ScriptedConversation
    version: int = 0
    messages: list[dict] = field(default_factory=list)
    pending: list[Spoken] = field(default_factory=list)
    opening: list[Spoken] = field(default_factory=list)
    voice_replay_pending: bool = False
    voice_replay_output: list[Spoken] = field(default_factory=list)
    turn_ids: set[str] = field(default_factory=set)
    turn_outputs: dict[str, list[Spoken]] = field(default_factory=dict)
    submit_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    @property
    def status(self) -> Literal['active', 'completed']:
        return 'completed' if self.conversation.controller.phase == 'completed' else 'active'


class ScriptedSessionStore:
    def __init__(self, catalog: ScriptedCatalog, evaluator_factory, teacher_factory):
        self.catalog = catalog
        self.evaluator_factory = evaluator_factory
        self.teacher_factory = teacher_factory
        self._sessions: dict[str, ScriptedSession] = {}

    def create(self, unit_id: str, lesson_id: int) -> ScriptedSession:
        if unit_id != GRADE3_UNIT_ID:
            raise LookupError(unit_id)
        lesson = self.catalog.load(unit_id, lesson_id)
        conversation = ScriptedConversation(
            lesson, self.evaluator_factory(), self.teacher_factory(), mode='text')
        session = ScriptedSession(
            id=str(uuid4()), unit_id=unit_id, lesson_id=lesson_id,
            lesson_title=lesson.title, conversation=conversation,
        )
        self._sessions[session.id] = session
        opening = conversation.start()
        session.opening = opening
        session.messages.extend(self._teacher_messages(opening))
        return session

    def get(self, session_id: str) -> ScriptedSession:
        try:
            return self._sessions[session_id]
        except KeyError:
            raise LookupError(session_id) from None

    async def close(self, session_id: str) -> None:
        session = self.get(session_id)
        async with session.submit_lock:
            if self._sessions.pop(session_id, None) is None:
                raise LookupError(session_id)
            close = getattr(session.conversation.teacher, 'close', None)
            if close is not None:
                await close()

    def list_active(self) -> list[ScriptedSession]:
        return [session for session in self._sessions.values() if session.status == 'active']

    async def start_voice(self, session_id: str) -> list[Spoken]:
        session = self.get(session_id)
        async with session.submit_lock:
            return self._start_voice_locked(session)

    def _start_voice_locked(self, session: ScriptedSession) -> list[Spoken]:
        controller = session.conversation.controller
        if session.voice_replay_pending:
            session.conversation.mode = 'voice'
            return session.voice_replay_output
        if session.pending:
            session.conversation.mode = 'voice'
            return session.pending
        if controller.phase != 'ready':
            raise RuntimeError('Session is not ready for Voice')
        session.conversation.mode = 'voice'
        session.voice_replay_pending = True
        item = session.conversation.controller.lesson.items[controller.item_index]
        session.voice_replay_output = (
            session.opening if not session.turn_ids
            else [Spoken(item.say, 'say', item.image_url)]
        )
        return session.voice_replay_output

    async def submit(self, session_id: str, turn_id: str, query: str,
                     expected_version: int, *, source: str = 'text') -> list[Spoken]:
        session = self.get(session_id)
        async with session.submit_lock:
            return await self._submit_locked(session, turn_id, query,
                                             expected_version, source)

    async def _submit_locked(self, session: ScriptedSession, turn_id: str,
                             query: str, expected_version: int,
                             source: str) -> list[Spoken]:
        if turn_id in session.turn_ids:
            return session.turn_outputs[turn_id]
        if session.version != expected_version:
            raise RuntimeError('Session version conflict')
        if session.voice_replay_pending:
            raise RuntimeError('Voice delivery is still in progress')
        if source not in {'text', 'voice'}:
            raise ValueError('Unknown learner input source')
        if session.pending:
            raise RuntimeError('Previous Voice delivery is still in progress')
        old_mode = session.conversation.mode
        session.conversation.mode = source
        try:
            output = await session.conversation.submit(turn_id, query)
        except Exception:
            session.conversation.mode = old_mode
            raise
        session.turn_ids.add(turn_id)
        session.turn_outputs[turn_id] = output
        session.messages.append({'role': 'learner', 'text': query, 'turn_id': turn_id})
        if session.conversation.mode == 'text':
            session.messages.extend(self._teacher_messages(output))
        else:
            session.pending = output
        session.version += 1
        return output

    async def finish_voice_delivery(self, session_id: str) -> list[Spoken]:
        session = self.get(session_id)
        async with session.submit_lock:
            return self._finish_voice_delivery_locked(session)

    def _finish_voice_delivery_locked(self, session: ScriptedSession) -> list[Spoken]:
        if session.voice_replay_pending:
            session.voice_replay_pending = False
            session.voice_replay_output = []
            return []
        if not session.pending:
            raise RuntimeError('No Voice delivery is pending')
        session.messages.extend(self._teacher_messages(session.pending))
        next_output = session.conversation.delivery_finished()
        session.pending = next_output
        session.version += 1
        return next_output

    @staticmethod
    def _teacher_messages(output: list[Spoken]) -> list[dict]:
        return [{'role': 'teacher', 'text': item.text,
                 **({'image_url': item.image_url} if item.image_url else {})}
                for item in output]
