from typing import Any, Literal

from pydantic import Field, model_validator

from luna_tutor.domain.contracts import Contract, Identifier, Text


class SourceRef(Contract):
    file: Text
    heading: Text
    line: int = Field(ge=1)
    numbered: bool = False


class InitialScenarioState(Contract):
    stage_id: Identifier
    activity_id: Identifier | None = None
    objective_id: Identifier | None = None
    attempt_count: int = Field(default=0, ge=0, le=2)
    support: Literal['independent', 'hint', 'choices', 'starter', 'model'] = 'independent'
    prior_activities_handled: bool = False
    model_repetitions_delivered: int = Field(default=0, ge=0, le=2)
    response_opportunity_given: bool = False
    activity_completed: bool = False


class EvaluatorGold(Contract):
    response_kind: Text
    meaning_status: Text = 'not_demonstrated'
    target_form_status: Text = 'not_used'
    recast_needed: bool = False
    emotional_signals: list[Text] = Field(default_factory=list)
    needs_clarification: bool = False


class StateSnapshot(Contract):
    after_turn: int = Field(ge=1)
    expected: dict[str, Any]


class ScenarioTurn(Contract):
    teacher_turn: Text = ''
    learner_text: Text
    input_event: Literal['transcript', 'no_response'] = 'transcript'
    transcript_status: Literal['final', 'incomplete', 'uncertain'] = 'final'
    evaluator_gold: EvaluatorGold
    allowed_feedback_actions: list[Text] = Field(min_length=1)
    forbidden_behaviors: list[Text] = Field(min_length=1)
    expected_state_effects: dict[str, Any]
    teacher_criteria: list[Text] = Field(min_length=1)


class Scenario(Contract):
    id: Identifier
    set: Literal['development', 'holdout']
    source: SourceRef
    initial_state: InitialScenarioState
    objective_ids: list[Identifier] = Field(default_factory=list)
    rule_ids: list[Text] = Field(default_factory=list)
    branch_ids: list[Identifier] = Field(default_factory=list)
    turns: list[ScenarioTurn] = Field(min_length=1)
    state_snapshots: list[StateSnapshot] = Field(default_factory=list)

    @model_validator(mode='after')
    def snapshots_reference_turns(self):
        if any(item.after_turn > len(self.turns) for item in self.state_snapshots):
            raise ValueError('State snapshot references a missing turn')
        return self


class CoverageManifest(Contract):
    source_file: Text
    numbered_scenario_ids: list[Identifier]
    required_rule_ids: list[Text]
    required_branch_ids: list[Identifier]
    required_objective_ids: list[Identifier]
    rule_scenarios: dict[Text, list[Identifier]]
    branch_scenarios: dict[Identifier, list[Identifier]]


class CoverageResult(Contract):
    numbered_scenarios: int
    missing_source_refs: list[Identifier]
    covered_rule_ids: set[Text]
    missing_branch_ids: list[Identifier]
    missing_objective_ids: list[Identifier]
