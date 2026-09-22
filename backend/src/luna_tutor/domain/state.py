"""Immutable session snapshots; completed activities do not imply mastery."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from luna_tutor.domain.contracts import AttemptCount, Contract, Identifier, SnapshotItems, Text, Version
from luna_tutor.domain.evidence import ContextTurn, SupportGiven
from luna_tutor.domain.privacy import SanitizedText

SupportLevel = Literal['independent', 'context_hint', 'choices', 'sentence_starter', 'model']


class ObjectiveProgress(Contract):
    objective_id: Identifier
    introduced: bool = False
    attempted: bool = False
    supported_uses: int = Field(default=0, ge=0)
    independent_uses: int = Field(default=0, ge=0)
    needs_review: bool = False


class ActivityProgress(Contract):
    activity_id: Identifier
    status: Literal['not_started', 'in_progress', 'completed', 'support_limit_reached'] = 'not_started'
    attempt_count: AttemptCount = 0
    successful_learner_repetitions: int = Field(default=0, ge=0)
    demonstrated_meaning_ids: SnapshotItems[Identifier] = ()
    no_response_count: int = Field(default=0, ge=0)
    model_repetitions_delivered: int = Field(default=0, ge=0, le=2)
    response_opportunity_given: bool = False
    feedback_delivered: bool = False
    learner_asked_teacher: bool = False
    completion_reason: Text | None = None

    @model_validator(mode='after')
    def support_limit_reason(self) -> Self:
        if self.status == 'support_limit_reached' and self.completion_reason is None:
            raise ValueError('Support-limit completion needs a reason')
        return self


class ReviewItem(Contract):
    objective_id: Identifier
    difficulty: Literal['meaning', 'word_recall', 'target_form']
    evidence_quote: SanitizedText | None = None
    support_level: SupportLevel = 'independent'
    last_seen_turn_id: Text | None = None
    learner_context: SanitizedText = ''


class LessonState(Contract):
    session_id: Text
    unit_id: Identifier
    state_version: Version = 0
    stage_id: Identifier
    activity_id: Identifier | None = None
    objective_id: Identifier | None = None
    status: Literal['active', 'paused', 'completed', 'abandoned'] = 'active'
    attempt_count: AttemptCount = 0
    support_given: SupportGiven = Field(default_factory=SupportGiven)
    activity_progress: SnapshotItems[ActivityProgress] = ()
    objective_progress: SnapshotItems[ObjectiveProgress] = ()
    review_queue: SnapshotItems[ReviewItem] = ()
    completed_stage_ids: SnapshotItems[Identifier] = ()
    applied_turn_ids: SnapshotItems[Text] = ()
    last_teacher_turn: SanitizedText = ''
    recent_context: SnapshotItems[ContextTurn] = Field(default=(), max_length=6)
    opening_message: SanitizedText | None = None
    closing_message: SanitizedText | None = None
    elapsed_seconds: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 0.0
    last_success_at_seconds: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None = None
    stop_requested: bool = False
    privacy_event: bool = False

    @model_validator(mode='after')
    def consistent_snapshot(self) -> Self:
        groups = [self.applied_turn_ids, self.completed_stage_ids,
                  tuple(item.activity_id for item in self.activity_progress),
                  tuple(item.objective_id for item in self.objective_progress),
                  tuple(item.objective_id for item in self.review_queue)]
        if any(len(group) != len(set(group)) for group in groups):
            raise ValueError('State IDs must be unique within each collection')
        if self.last_success_at_seconds is not None and self.last_success_at_seconds > self.elapsed_seconds:
            raise ValueError('Last success cannot be later than session elapsed time')
        return self
