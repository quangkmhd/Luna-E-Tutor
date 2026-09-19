"""Provider-independent, validated curriculum contracts."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, pattern=r'\S')]
Identifier = Annotated[str, Field(min_length=1, pattern=r'^[a-z0-9][a-z0-9._-]*$')]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Source(StrictModel):
    file: Text
    section: Text


class SourcedItem(StrictModel):
    id: Identifier
    source: Source


class VocabularyItem(SourcedItem):
    text: Text
    usage: Literal['taught', 'supporting'] = 'taught'


class Pattern(SourcedItem):
    text: Text
    examples: list[Text] = Field(default_factory=list)
    acceptable_alternatives: list[Text] = Field(default_factory=list)


class Objective(SourcedItem):
    description: Text
    vocabulary_ids: list[Identifier] = Field(default_factory=list)
    pattern_ids: list[Identifier] = Field(default_factory=list)
    evidence_criteria: Text

    @model_validator(mode='after')
    def check_target(self) -> Self:
        if not self.vocabulary_ids and not self.pattern_ids:
            raise ValueError('Objective needs a learning target')
        return self


class CompletionRule(StrictModel):
    mode: Literal['delivered', 'interaction', 'vocabulary_turn', 'communicative_turn', 'ask_teacher', 'user_end']
    model_repetitions: int = Field(default=0, ge=0, le=2)
    response_opportunity_required: bool = False
    feedback_required: bool = False
    allow_support_limit_exit: bool = False
    mastery_required: Literal[False] = False


class Activity(SourcedItem):
    stage_id: Identifier
    kind: Literal['greeting', 'emotion_check', 'bridge', 'vocabulary_introduction',
                  'comprehension', 'guided_response', 'review', 'ask_teacher',
                  'roleplay', 'summary']
    objective_ids: list[Identifier]
    required: bool
    max_attempts: int = Field(ge=1, le=2)
    completion_rule: CompletionRule
    instruction: Text
    examples: list[Text] = Field(default_factory=list)

    @model_validator(mode='after')
    def check_completion(self) -> Self:
        rule = self.completion_rule
        expected_modes = {
            'greeting': 'delivered', 'bridge': 'delivered', 'summary': 'delivered',
            'emotion_check': 'interaction', 'vocabulary_introduction': 'vocabulary_turn',
            'comprehension': 'communicative_turn', 'guided_response': 'communicative_turn',
            'review': 'communicative_turn', 'ask_teacher': 'ask_teacher', 'roleplay': 'user_end',
        }
        if rule.mode != expected_modes[self.kind]:
            raise ValueError(f'Invalid completion mode for {self.kind}')
        if self.kind == 'vocabulary_introduction':
            if len(self.objective_ids) != 1:
                raise ValueError('Vocabulary introduction needs exactly one objective')
            if not (rule.mode == 'vocabulary_turn' and rule.model_repetitions == 2
                    and rule.response_opportunity_required and rule.feedback_required):
                raise ValueError('Vocabulary completion requires two models, an opportunity, and feedback')
        if self.kind in {'guided_response', 'comprehension', 'review', 'ask_teacher'}:
            if not self.objective_ids or not rule.response_opportunity_required:
                raise ValueError('Practice requires objectives and a response opportunity')
        if self.max_attempts == 2 and not rule.allow_support_limit_exit:
            raise ValueError('Retryable activity must exit after the support limit')
        return self


class Role(StrictModel):
    name: Text
    country: Text
    announce_start: Literal[True]
    announce_end: Literal[True]


class ReviewSelection(StrictModel):
    rank_by: list[Literal['contextual_relevance', 'importance', 'required_support', 'recency']] = Field(min_length=1)
    max_items_per_turn: Literal[1]
    cancel_if_independently_demonstrated: Literal[True]
    allow_unresolved_on_exit: Literal[True]


class Stage(SourcedItem):
    title: Text
    level: int = Field(ge=0, le=3)
    lesson: int | None = Field(default=None, ge=1)
    exits: list[Identifier] = Field(min_length=1)
    prerequisite_stage_ids: list[Identifier] = Field(default_factory=list)
    completion_rule: Literal['all_required_activities_handled', 'user_end']
    role: Role | None = None
    review: ReviewSelection | None = None


class TeachingPolicy(StrictModel):
    schema_version: Literal[1]
    source: Source
    max_attempts: Literal[2]
    recast_requires_repetition: Literal[False]
    warm_up_vocabulary_teaching: Literal[False]
    silence_hint_seconds: int = Field(gt=0)
    success_window_seconds: int = Field(gt=0)
    reduce_difficulty_after_seconds: int = Field(gt=0)
    learner_speaking_share: float = Field(ge=0, le=1)
    free_talk_learner_speaking_share: float = Field(ge=0, le=1)
    phone_numbers: Literal['words_or_fictional_only']
    allow_stop_and_save: Literal[True]
    free_talk_may_end_with_open_review: Literal[True]
    operational_or_meaning_questions_count_as_attempts: Literal[False]


class SpeechStyle(StrictModel):
    schema_version: Literal[1]
    source: Source
    tone: Text
    address_teacher: Text
    address_student: Text
    plain_spoken_text: Literal[True]
    feedback_order: list[Text]
    follow_praise_with_bridge: Literal[True]
    pronunciation_claims_require_audio_evidence: Literal[True]


class GradeProfile(SourcedItem):
    grades: list[Annotated[int, Field(ge=1, le=5)]] = Field(min_length=1)
    english_share_min: float = Field(ge=0, le=1)
    english_share_max: float = Field(ge=0, le=1)
    max_english_sentence_words: int | None = Field(default=None, ge=1)
    guidance: Text


class GradeProfiles(StrictModel):
    schema_version: Literal[1]
    profiles: list[GradeProfile] = Field(min_length=1)


class UnitCurriculum(SourcedItem):
    schema_version: Literal[1]
    grade: int = Field(ge=1, le=5)
    unit: int = Field(ge=1)
    title: Text
    vocabulary: list[VocabularyItem]
    patterns: list[Pattern]
    objectives: list[Objective] = Field(min_length=1)
    activities: list[Activity] = Field(min_length=1)
    stages: list[Stage] = Field(min_length=1)
    teacher_prompt: Text
    teaching_policy: TeachingPolicy
    speech_style: SpeechStyle
    grade_profiles: GradeProfiles

    def vocabulary_ids(self) -> set[str]:
        return {item.id for item in self.vocabulary if item.usage == 'taught'}

    @model_validator(mode='after')
    def check_references(self) -> Self:
        self.validate_references()
        return self

    def validate_references(self) -> None:
        """Reject dangling references, missing coverage, or stages with no way out."""
        def unique(items, label):
            ids = [item.id for item in items]
            if len(ids) != len(set(ids)):
                raise ValueError(f'Duplicate {label} IDs')
            return set(ids)

        vocabulary = unique(self.vocabulary, 'vocabulary')
        patterns = unique(self.patterns, 'pattern')
        objectives = unique(self.objectives, 'objective')
        unique(self.activities, 'activity')
        stage_ids = unique(self.stages, 'stage')

        def references(ids, known, label):
            if len(ids) != len(set(ids)):
                raise ValueError(f'Duplicate {label} references')
            missing = set(ids) - known
            if missing:
                raise ValueError(f'Unknown {label} references: {sorted(missing)}')

        for objective in self.objectives:
            references(objective.vocabulary_ids, vocabulary, 'vocabulary')
            references(objective.pattern_ids, patterns, 'pattern')
        vocabulary_targets = {v for o in self.objectives for v in o.vocabulary_ids}
        pattern_targets = {p for o in self.objectives for p in o.pattern_ids}
        if self.vocabulary_ids() - vocabulary_targets or patterns - pattern_targets:
            raise ValueError('Missing objective coverage for taught vocabulary or patterns')
        objective_map = {o.id: o for o in self.objectives}
        for activity in self.activities:
            references(activity.objective_ids, objectives, 'objective')
            references([activity.stage_id], stage_ids, 'stage')
            if activity.kind == 'vocabulary_introduction':
                target = objective_map[activity.objective_ids[0]]
                if (len(target.vocabulary_ids) != 1 or target.pattern_ids
                        or target.vocabulary_ids[0] not in self.vocabulary_ids()):
                    raise ValueError('Word introduction must reference one taught vocabulary target')
        covered = {oid for activity in self.activities for oid in activity.objective_ids}
        if objectives - covered:
            raise ValueError(f'Missing objective coverage: {sorted(objectives - covered)}')
        for stage in self.stages:
            references(stage.exits, stage_ids | {'finish'}, 'exit')
            references(stage.prerequisite_stage_ids, stage_ids, 'prerequisite')
            if stage.id in stage.prerequisite_stage_ids:
                raise ValueError('A stage cannot be its own prerequisite')
            activities = [a for a in self.activities if a.stage_id == stage.id]
            if not any(a.required for a in activities):
                raise ValueError(f'Stage {stage.id} needs required activities')
            if stage.id == 'warm-up' and any(a.kind not in {'greeting', 'emotion_check', 'bridge'} or a.objective_ids for a in activities):
                raise ValueError('Warm-up only greets, checks emotion, and bridges')
            if stage.id == 'free-talk' and (stage.role is None or stage.review is None):
                raise ValueError('Free Talk needs a role and review selection rules')
        # Fixed-point reachability detects multi-stage closed cycles, not just empty exits.
        reachable = {'finish'}
        while True:
            newly_reachable = {s.id for s in self.stages if set(s.exits) & reachable}
            if newly_reachable <= reachable:
                break
            reachable |= newly_reachable
        if stage_ids - reachable:
            raise ValueError(f'Stages lack a terminal exit: {sorted(stage_ids - reachable)}')
        positions = {stage.id: i for i, stage in enumerate(self.stages)}
        if [positions[a.stage_id] for a in self.activities] != sorted(positions[a.stage_id] for a in self.activities):
            raise ValueError('Activities must follow stage order')
        for stage in self.stages:
            if any(positions[p] >= positions[stage.id] for p in stage.prerequisite_stage_ids):
                raise ValueError('Stage prerequisites must precede the stage')


class ContentFragment(StrictModel):
    schema_version: Literal[1]
    stage: Stage
    vocabulary: list[VocabularyItem] = Field(default_factory=list)
    patterns: list[Pattern] = Field(default_factory=list)
    objectives: list[Objective] = Field(default_factory=list)
    activities: list[Activity]


class UnitManifest(SourcedItem):
    schema_version: Literal[1]
    grade: int = Field(ge=1, le=5)
    unit: int = Field(ge=1)
    title: Text
    content_files: list[Text] = Field(min_length=1)
    shared_dir: Text
    opening: ContentFragment
    closing: ContentFragment


class ImportedLesson(StrictModel):
    lesson: int = Field(ge=1)
    objective_ids: list[Identifier]
    source: Source


class ImportedUnit(StrictModel):
    grade: int = Field(ge=1, le=5)
    unit: int = Field(ge=1)
    title: Text
    source: Source
    vocabulary: list[VocabularyItem]
    patterns: list[Pattern]
    objectives: list[Objective]
    lessons: list[ImportedLesson]

    def vocabulary_ids(self) -> set[str]:
        return {item.id for item in self.vocabulary if item.usage == 'taught'}
