"""Run two evaluator pipelines from the same lesson-state snapshot."""

import asyncio
from time import perf_counter

from luna_tutor.domain.contracts import Contract
from luna_tutor.domain.decisions import TeachingDecision
from luna_tutor.domain.evidence import EvaluatorResult


class ComparisonBranch(Contract):
    evaluator_model: str
    teacher_output: str
    evidence: EvaluatorResult
    decision: TeachingDecision
    planning_latency_ms: int
    teacher_latency_ms: int
    total_latency_ms: int


class ComparisonResult(Contract):
    state_version: int
    stage_id: str
    activity_id: str | None
    learner_text: str
    teacher_model: str = 'google/gemini-3.5-flash-lite'
    gemini: ComparisonBranch
    jev: ComparisonBranch


class ComparisonService:
    def __init__(self, gemini_turn_service, jev_turn_service):
        self._gemini = gemini_turn_service
        self._jev = jev_turn_service

    @staticmethod
    async def _run(service, state, learner_text: str, turn_id: str,
                   evaluator_model: str) -> ComparisonBranch:
        started = perf_counter()
        plan = await service.plan(state, learner_text, turn_id)
        planned = perf_counter()
        utterance = await service.respond(plan.teacher_request)
        finished = perf_counter()
        return ComparisonBranch(
            evaluator_model=evaluator_model,
            teacher_output=utterance.spoken_text,
            evidence=plan.evidence,
            decision=plan.decision,
            planning_latency_ms=round((planned - started) * 1000),
            teacher_latency_ms=round((finished - planned) * 1000),
            total_latency_ms=round((finished - started) * 1000),
        )

    async def compare(self, state, learner_text: str, comparison_id: str) -> ComparisonResult:
        gemini, jev = await asyncio.gather(
            self._run(self._gemini, state, learner_text, f'{comparison_id}-gemini',
                      'google/gemini-3.5-flash-lite'),
            self._run(self._jev, state, learner_text, f'{comparison_id}-jev',
                      '~typesafe/jev-latest'),
        )
        return ComparisonResult(
            state_version=state.state_version,
            stage_id=state.stage_id,
            activity_id=state.activity_id,
            learner_text=learner_text,
            gemini=gemini,
            jev=jev,
        )
