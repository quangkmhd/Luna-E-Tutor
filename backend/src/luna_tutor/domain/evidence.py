"""What the learner demonstrated, without authority over teaching progression."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from luna_tutor.domain.contracts import AttemptCount, Contract, Identifier, Text, Version
from luna_tutor.domain.privacy import SanitizedText

MeaningStatus = Literal['satisfied', 'partially_satisfied', 'wrong_semantic_category',
                        'not_demonstrated', 'uncertain']
TargetFormStatus = Literal['correct_target_form', 'valid_alternative',
                           'error_in_target_form', 'not_used', 'uncertain']
ResponseKind = Literal['answer', 'asks_meaning', 'asks_teacher', 'off_topic',
                       'does_not_know', 'insufficient_data', 'no_response']
InputEvent = Literal['transcript', 'no_response']
TranscriptStatus = Literal['final', 'incomplete', 'uncertain']


class SupportGiven(Contract):
    model_spoken_recently: bool = False
    choices_given: bool = False
    sentence_starter_given: bool = False


class ActiveObjective(Contract):
    objective_id: Identifier
    communicative_goal: Text
    target_patterns: list[Text] = Field(default_factory=list)
    target_words: list[Text] = Field(default_factory=list)
    acceptable_alternatives: list[Text] = Field(default_factory=list)
    evidence_criteria: Text


class ContextTurn(Contract):
    role: Literal['teacher', 'learner']
    text: Annotated[SanitizedText, Field(max_length=2000)]


class EvaluatorRequest(Contract):
    turn_id: Text
    state_version: Version
    teacher_turn: Annotated[SanitizedText, Field(max_length=4000)]
    activity_type: Text
    # Unit 1 Free Talk revisits all 27 objectives; keep a finite unit-sized bound.
    active_objectives: list[ActiveObjective] = Field(max_length=64)
    support_given: SupportGiven
    transcript_status: TranscriptStatus
    input_event: InputEvent = 'transcript'
    learner_transcript: Annotated[SanitizedText, Field(max_length=8000)]
    recent_context: list[ContextTurn] = Field(default_factory=list, max_length=6)
    attempt_count: AttemptCount = 0
    stt_issue: bool = False
    audio_issue: bool = False

    @model_validator(mode='after')
    def unique_objectives(self) -> Self:
        ids = [item.objective_id for item in self.active_objectives]
        if len(ids) != len(set(ids)):
            raise ValueError('Active objective IDs must be unique')
        return self


class ObjectiveEvidence(Contract):
    objective_id: Identifier
    meaning_status: MeaningStatus
    target_form_status: TargetFormStatus
    evidence_quote: SanitizedText | None
    recast_needed: bool
    corrected_form: Annotated[SanitizedText, Field(min_length=1, pattern=r'\S')] | None

    @model_validator(mode='after')
    def consistent_evidence(self) -> Self:
        quote_required = (
            self.meaning_status not in {'not_demonstrated', 'uncertain'}
            or self.target_form_status not in {'not_used', 'uncertain'}
        )
        if quote_required and not (self.evidence_quote and self.evidence_quote.strip()):
            raise ValueError('Demonstrated evidence requires a non-empty quote')
        if self.corrected_form is not None and not self.recast_needed:
            raise ValueError('A corrected form is only allowed when recast is needed')
        if self.recast_needed and (
            self.target_form_status != 'error_in_target_form'
            or self.meaning_status not in {'satisfied', 'partially_satisfied'}
        ):
            raise ValueError('Recast requires a demonstrated form error with known meaning')
        return self


class EvaluatorResult(Contract):
    turn_id: Text
    state_version: Version
    response_kind: ResponseKind
    emotional_signals: list[Text]
    objective_evidence: list[ObjectiveEvidence]
    needs_clarification: bool
    ambiguity_reason: Text | None

    @classmethod
    def observed_no_response(cls, turn_id: str, state_version: int) -> 'EvaluatorResult':
        return cls(turn_id=turn_id, state_version=state_version, response_kind='no_response',
                   emotional_signals=[], objective_evidence=[], needs_clarification=False,
                   ambiguity_reason=None)

    @classmethod
    def contact_removed(cls, turn_id: str, state_version: int) -> 'EvaluatorResult':
        """Local privacy outcome shared by production and evaluation."""
        return cls(
            turn_id=turn_id, state_version=state_version,
            response_kind='insufficient_data', emotional_signals=[],
            objective_evidence=[], needs_clarification=True,
            ambiguity_reason='Contact information was removed locally.',
        )

    @model_validator(mode='after')
    def consistent_result(self) -> Self:
        if self.needs_clarification and self.ambiguity_reason is None:
            raise ValueError('Clarification requires an ambiguity reason')
        ids = [item.objective_id for item in self.objective_evidence]
        if len(ids) != len(set(ids)):
            raise ValueError('Objective evidence IDs must be unique')
        return self
