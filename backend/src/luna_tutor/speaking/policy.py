from luna_tutor.speaking.models import Decision, Evidence, SpeakingState


def decide(state: SpeakingState, evidence: Evidence) -> Decision:
    if evidence.kind == 'finish':
        return Decision(action='finish', level=state.level,
                        independent_streak=0, difficulty_streak=0)
    if evidence.kind == 'unclear':
        return Decision(action='clarify', level=state.level,
                        independent_streak=0, difficulty_streak=state.difficulty_streak)
    if evidence.kind == 'help':
        return Decision(action='offer_choices', level=state.level,
                        independent_streak=0, difficulty_streak=0)

    independent = state.independent_streak + 1 if evidence.independent else 0
    difficulty = state.difficulty_streak + 1 if evidence.difficulty else 0
    level = state.level
    action = 'continue'
    if independent >= 3:
        level, independent, action = min(2, level + 1), 0, 'expand'
    elif difficulty >= 2:
        level, difficulty, action = max(0, level - 1), 0, 'offer_choices'
    return Decision(action=action, level=level,
                    independent_streak=independent, difficulty_streak=difficulty)
