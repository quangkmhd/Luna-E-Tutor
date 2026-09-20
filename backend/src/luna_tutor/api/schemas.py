from typing import Literal

from pydantic import Field

from luna_tutor.domain.contracts import Contract, Identifier, Text
from luna_tutor.domain.decisions import TeachingDecision
from luna_tutor.domain.evidence import EvaluatorResult
from luna_tutor.domain.state import ObjectiveProgress, ReviewItem


class CreateSessionRequest(Contract):
    unit_id: Identifier


class UnitView(Contract):
    id: str
    grade: int
    unit: int
    title: str


class TurnRequest(Contract):
    turn_id: Text
    expected_state_version: int = Field(ge=0)
    learner_text: Text = Field(max_length=8000)


class VersionRequest(Contract):
    expected_state_version: int = Field(ge=0)


class ReviewRequest(Contract):
    learner_text: Text = Field(max_length=8000)


class MessageView(Contract):
    role: Literal['learner', 'teacher']
    text: str
    turn_id: str | None = None
    delivery_intent: str | None = None


class SummaryView(Contract):
    demonstrated: list[str]
    supported: list[str]
    needs_review: list[str]
    not_yet_observed: list[str]


class SessionView(Contract):
    session_id: str
    unit_id: str
    unit: UnitView
    state_version: int
    stage_id: str
    activity_id: str | None
    objective_id: str | None
    status: str
    messages: list[MessageView]
    review_queue: list[ReviewItem]
    objective_progress: list[ObjectiveProgress]
    last_evidence: EvaluatorResult | None = None
    last_decision: TeachingDecision | None = None
    summary: SummaryView | None = None


class TurnResponse(Contract):
    turn_id: str
    session: SessionView


class ErrorDetail(Contract):
    code: str
    message: str
    retryable: bool = False
