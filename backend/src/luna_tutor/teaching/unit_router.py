"""Route persisted lesson state to the matching per-unit service."""

from collections.abc import Mapping

from luna_tutor.curriculum.registry import UnknownUnitError


class UnitTurnRouter:
    def __init__(self, services: Mapping[str, object]):
        self._services = dict(services)

    def _service(self, unit_id: str):
        try:
            return self._services[unit_id]
        except KeyError as error:
            raise UnknownUnitError(unit_id) from error

    async def process(self, state, learner_text: str, turn_id: str, **kwargs):
        return await self._service(state.unit_id).process(
            state, learner_text, turn_id, **kwargs
        )

    async def plan(self, state, learner_text: str, turn_id: str, **kwargs):
        return await self._service(state.unit_id).plan(
            state, learner_text, turn_id, **kwargs
        )

    async def respond(self, request):
        return await self._service(request.unit_id).respond(request)

    def complete(self, state, plan, utterance):
        return self._service(state.unit_id).complete(state, plan, utterance)


class UnitComparisonRouter(UnitTurnRouter):
    async def compare(self, state, learner_text: str, comparison_id: str):
        return await self._service(state.unit_id).compare(
            state, learner_text, comparison_id
        )


class LessonTurnRouter:
    """Select the authored lesson while retaining legacy stored sessions."""

    def __init__(self, services: Mapping[int | None, object]):
        self._services = dict(services)

    def _service(self, lesson_id: int | None):
        try:
            return self._services[lesson_id]
        except KeyError as error:
            raise UnknownUnitError(f'Unknown lesson {lesson_id}') from error

    async def process(self, state, learner_text: str, turn_id: str, **kwargs):
        return await self._service(state.lesson_id).process(state, learner_text, turn_id, **kwargs)

    async def plan(self, state, learner_text: str, turn_id: str, **kwargs):
        return await self._service(state.lesson_id).plan(state, learner_text, turn_id, **kwargs)

    async def respond(self, request):
        return await self._service(request.lesson_id).respond(request)

    def complete(self, state, plan, utterance):
        return self._service(state.lesson_id).complete(state, plan, utterance)
