"""Controller decisions, bounded expression requests, and atomic turn envelopes."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from luna_tutor.domain.contracts import Contract, Identifier, SnapshotItems, Text, Version
from luna_tutor.domain.evidence import ActiveObjective, ContextTurn, EvaluatorResult
from luna_tutor.domain.privacy import SanitizedText
from luna_tutor.domain.state import LessonState, ObjectiveProgress

FeedbackAction = Literal['acknowledge_and_continue', 'recast', 'explain_meaning',
                         'answer_teacher_question', 'reassure', 'redirect', 'offer_support',
                         'clarify', 'privacy_redirect', 'stop', 'none']
ProgressionAction = Literal['stay', 'reduce_difficulty', 'move_to_next_objective',
                            'move_to_next_stage', 'save_and_stop', 'finish']
SpokenText = Annotated[SanitizedText, Field(min_length=1, max_length=4000, pattern=r'\S')]


class TeachingDecision(Contract):
    feedback_action: FeedbackAction
    progression_action: ProgressionAction
    corrected_form: SpokenText | None = None
    emotional_support: bool = False
    next_objective_id: Identifier | None = None
    next_activity_id: Identifier | None = None
    next_stage_id: Identifier | None = None
    review_queue_add: list[Identifier] = Field(default_factory=list)
    review_queue_remove: list[Identifier] = Field(default_factory=list)
    # Historical public name from the plan: these are evidence updates, never
    # a mastery score or a claim that one correct answer proves mastery.
    mastery_updates: list[ObjectiveProgress] = Field(default_factory=list)
    count_attempt: bool = False
    support_limit_exit: bool = False

    @model_validator(mode='after')
    def consistent_correction(self) -> Self:
        if self.corrected_form is not None and self.feedback_action != 'recast':
            raise ValueError('A corrected form is only allowed for a recast decision')
        if set(self.review_queue_add) & set(self.review_queue_remove):
            raise ValueError('A review item cannot be both added and removed')
        return self


class TeacherConstraints(Contract):
    max_questions: int = Field(default=1, ge=0, le=1)
    require_repetition: bool = False
    allow_pronunciation_claims: Literal[False] = False
    plain_spoken_text: Literal[True] = True
    encouragement_required: bool = False
    additional: SnapshotItems[Text] = ()


class TeacherActivityContext(Contract):
    """Curriculum content for expression, never authority to change state."""

    stage_id: Identifier
    activity_id: Identifier
    kind: Text
    objectives: SnapshotItems[Text] = ()
    target_words: SnapshotItems[Text] = ()
    target_patterns: SnapshotItems[Text] = ()
    examples: SnapshotItems[Text] = ()
    model_repetitions: int = Field(default=0, ge=0, le=2)
    remaining_model_repetitions: int = Field(default=0, ge=0, le=2)
    needs_response_invitation: bool = False
    delivery_only: bool = False
    role_name: Text | None = None
    role_country: Text | None = None


class TeacherTurnRequest(Contract):
    turn_id: Text
    unit_id: Identifier
    feedback_action: FeedbackAction
    corrected_form: SpokenText | None = None
    learner_meaning: Annotated[SanitizedText, Field(max_length=2000)]
    next_teaching_move: SpokenText
    emotional_support: bool = False
    previous_teacher_turn: Annotated[SanitizedText, Field(max_length=4000)] = ''
    activity_context: TeacherActivityContext | None = None
    review_objective: ActiveObjective | None = None
    recent_context: SnapshotItems[ContextTurn] = Field(default=(), max_length=6)
    constraints: TeacherConstraints = Field(default_factory=TeacherConstraints)

    @model_validator(mode='after')
    def consistent_correction(self) -> Self:
        if self.corrected_form is not None and self.feedback_action != 'recast':
            raise ValueError('A corrected form is only allowed for a recast request')
        return self


class TeacherUtterance(Contract):
    spoken_text: SpokenText
    delivery_intent: Literal['warm', 'reassuring', 'encouraging', 'neutral', 'roleplay']
    generation_mode: Literal['model', 'fallback'] = 'model'


class PlannedTurn(Contract):
    """A proposal only: Teacher wording and persistence are not yet authorized.

    Nested contracts are revalidated, copying caller-owned lists on entry.
    Evaluator/decision lists retain their ordinary public list API; callers
    must treat this snapshot as read-only during orchestration.
    """

    turn_id: Text
    state_version: Version
    learner_text: SanitizedText
    privacy_event: bool
    evidence: EvaluatorResult
    decision: TeachingDecision
    teacher_request: TeacherTurnRequest
    proposed_next_state: LessonState

    @model_validator(mode='after')
    def correlated_components(self) -> Self:
        if self.evidence.turn_id != self.turn_id or self.teacher_request.turn_id != self.turn_id:
            raise ValueError('Turn IDs must match')
        if self.evidence.state_version != self.state_version:
            raise ValueError('Evidence must match the input state version')
        if self.proposed_next_state.state_version != self.state_version + 1:
            raise ValueError('Proposed state must advance exactly one version')
        if self.turn_id not in self.proposed_next_state.applied_turn_ids:
            raise ValueError('Proposed state must record the applied turn ID')
        for item in self.evidence.objective_evidence:
            if item.evidence_quote and item.evidence_quote not in self.learner_text:
                raise ValueError('Evidence quote must occur in sanitized learner text')
        if (self.teacher_request.feedback_action != self.decision.feedback_action
                or self.teacher_request.corrected_form != self.decision.corrected_form
                or self.teacher_request.emotional_support != self.decision.emotional_support):
            raise ValueError('Teacher request must express the approved decision')
        return self


class CompletedTurn(Contract):
    """Persistence candidate after Teacher validation, never a partial proposal.

    Schema validation covers structure. The TurnService must also validate
    spoken wording against the requested teaching constraints before building
    this object; persistence must compare the original state version atomically.
    """

    plan: PlannedTurn
    teacher_utterance: TeacherUtterance
    next_state: LessonState

    @model_validator(mode='after')
    def matches_proposal(self) -> Self:
        proposal = self.plan.proposed_next_state
        if self.next_state.model_dump(exclude={'last_teacher_turn'}) != proposal.model_dump(exclude={'last_teacher_turn'}):
            raise ValueError('Persistable state must match the validated proposal')
        # Text delivery can record the completed wording. Voice delivery may
        # retain the prior actual utterance until playback has been confirmed.
        if self.next_state.last_teacher_turn not in {proposal.last_teacher_turn, self.teacher_utterance.spoken_text}:
            raise ValueError('Recorded teacher text must match validated wording')
        return self
