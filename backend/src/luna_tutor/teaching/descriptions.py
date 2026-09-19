"""Read editable Teacher instructions; routing conditions remain Python code."""

from pathlib import Path
import yaml

CATALOG_PATH = Path(__file__).resolve().parents[1] / 'prompts/teacher-description-catalog.yaml'


class TeacherDescriptions:
    def __init__(self, path: Path | None = None):
        path = CATALOG_PATH if path is None else path
        self.data = yaml.safe_load(path.read_text(encoding='utf-8'))
        self.branches = {item['order']: item['description_en']
                         for item in self.data['planner_branches']}
        if set(self.branches) != set(range(1, 17)) or len(self.data['planner_branches']) != 16:
            raise ValueError('Teacher catalog must contain unique branches 1–16')
        self.activities = {item['activity_id']: item['description_en']
                           for item in self.data['activity_instructions']}

    def instruction(self, activity):
        return self.activities.get(activity.id, activity.instruction)

    def branch(self, number, *, target=None, current=None):
        text = self.branches[number]
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
