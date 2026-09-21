"""Read editable Teacher instructions; routing conditions remain Python code."""

from pathlib import Path
import yaml

CATALOG_PATH = Path(__file__).resolve().parents[1] / 'prompts/teacher-description-catalog.yaml'
BRANCH_NAMES = {
    'privacy_redirect', 'clarify', 'explain_meaning',
    'answer_teacher_question_then_move', 'answer_teacher_question',
    'no_response_stay', 'no_response_move_to_delivery',
    'no_response_move_with_support', 'free_talk', 'support_ask_teacher',
    'support_new_vocabulary', 'offer_support', 'finish',
    'retry_vocabulary', 'retry_target_form', 'retry_meaning',
    'support_limit_then_move',
    'move_to_ask_teacher', 'move_to_next_activity', 'current_activity',
}


class TeacherDescriptions:
    def __init__(self, path: Path | None = None):
        path = CATALOG_PATH if path is None else path
        self.data = yaml.safe_load(path.read_text(encoding='utf-8'))
        self.branches = {name: item['description_en']
                         for name, item in self.data['planner_branches'].items()}
        if set(self.branches) != BRANCH_NAMES:
            raise ValueError('Teacher catalog branch names do not match Planner branches')
    def instruction(self, activity):
        return activity.instruction

    def branch(self, name, *, target=None, current=None):
        text = self.branches[name]
        for name, activity in [('target', target), ('current', current)]:
            if activity is not None:
                text = text.replace('{' + name + '.instruction}', self.instruction(activity))
        return text

    def remaining(self, descriptions):
        return self.data['override_after_branch_selection']['description_en'].replace(
            '{remaining_objective_descriptions}', '; '.join(descriptions))

    @property
    def constraints(self):
        return tuple(item['description_en'] for item in self.data['additional_constraints'])
