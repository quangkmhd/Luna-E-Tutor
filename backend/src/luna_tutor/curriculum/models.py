"""Provider-independent, validated curriculum contracts."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, pattern=r'\S')]
Identifier = Annotated[str, Field(min_length=1, pattern=r'^[a-z0-9][a-z0-9._-]*$')]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class VocabularyItem(StrictModel):
    id: Identifier
    text: Text
    usage: Literal['taught', 'supporting'] = 'taught'


class Pattern(StrictModel):
    id: Identifier
    text: Text
    acceptable_alternatives: list[Text] = Field(default_factory=list)


class Objective(StrictModel):
    id: Identifier
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
    meaning_objective_ids: list[Identifier] = Field(default_factory=list)
    require_all_meanings: bool = False


class Activity(StrictModel):
    id: Identifier
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
        if not set(rule.meaning_objective_ids) <= set(self.objective_ids):
            raise ValueError('Completion meaning targets must belong to the activity')
        if rule.require_all_meanings and not rule.meaning_objective_ids:
            raise ValueError('All-meaning completion requires explicit targets')
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
            if not (rule.mode == 'vocabulary_turn' and rule.model_repetitions == 2):
                raise ValueError('Vocabulary completion requires two models')
        if self.kind in {'guided_response', 'comprehension', 'review', 'ask_teacher'}:
            if not self.objective_ids:
                raise ValueError('Practice requires objectives')
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


class Stage(StrictModel):
    id: Identifier
    title: Text
    exits: list[Identifier] = Field(min_length=1)
    prerequisite_stage_ids: list[Identifier] = Field(default_factory=list)
    completion_rule: Literal['all_required_activities_handled', 'user_end']
    role: Role | None = None
    review: ReviewSelection | None = None


class UnitCurriculum(StrictModel):
    id: Identifier
    grade: int = Field(ge=1, le=5)
    unit: int = Field(ge=1)
    title: Text
    greeting: Text
    vocabulary: list[VocabularyItem]
    patterns: list[Pattern]
    objectives: list[Objective] = Field(min_length=1)
    activities: list[Activity] = Field(min_length=1)
    stages: list[Stage] = Field(min_length=1)

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
        # Track completed stages per route: separate branches cannot jointly
        # satisfy prerequisites that a learner must handle in one session.
        stage_map = {stage.id: stage for stage in self.stages}
        pending = [(self.stages[0].id, frozenset())]
        visited = set()
        accessible = set()
        while pending:
            stage_id, completed = pending.pop()
            if (stage_id, completed) in visited:
                continue
            visited.add((stage_id, completed))
            if stage_id == 'finish':
                accessible.add(stage_id)
                continue
            stage = stage_map[stage_id]
            if not set(stage.prerequisite_stage_ids) <= completed:
                continue
            accessible.add(stage_id)
            handled = completed | {stage_id}
            pending.extend((exit_id, handled) for exit_id in stage.exits)
        inaccessible = (stage_ids | {'finish'}) - accessible
        if inaccessible:
            raise ValueError(
                'Stages unreachable from entry with prerequisites satisfied: '
                f'{sorted(inaccessible)}'
            )


class ContentFragment(StrictModel):
    stage: Stage
    vocabulary: list[VocabularyItem] = Field(default_factory=list)
    patterns: list[Pattern] = Field(default_factory=list)
    objectives: list[Objective] = Field(default_factory=list)
    activities: list[Activity]


class UnitManifest(StrictModel):
    id: Identifier
    grade: int = Field(ge=1, le=5)
    unit: int = Field(ge=1)
    title: Text
    greeting: Text
    content_files: list[Text] = Field(min_length=1)
    opening: ContentFragment
    closing: ContentFragment


class ImportedLesson(StrictModel):
    lesson: int = Field(ge=1)
    objective_ids: list[Identifier]


class ImportedUnit(StrictModel):
    grade: int = Field(ge=1, le=5)
    unit: int = Field(ge=1)
    title: Text
    vocabulary: list[VocabularyItem]
    patterns: list[Pattern]
    objectives: list[Objective]
    lessons: list[ImportedLesson]

    def vocabulary_ids(self) -> set[str]:
        return {item.id for item in self.vocabulary if item.usage == 'taught'}
