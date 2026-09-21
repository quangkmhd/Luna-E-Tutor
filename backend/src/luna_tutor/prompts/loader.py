"""Load independent system prompts from packaged YAML files."""

from importlib.resources import files
import yaml


def load_prompt_data(name: str) -> dict:
    data = yaml.safe_load(files('luna_tutor.prompts').joinpath(name).read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'Invalid prompt document: {name}')
    return data


def load_system_prompt(name: str) -> str:
    data = load_prompt_data(name)
    text = data['description_en']
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f'Empty or invalid system prompt: {name}')
    return text


def load_grade_system_prompt(grade: int, role: str) -> str:
    """Assemble one validated system message for a supported grade and role."""
    if role not in {'teacher', 'evaluator'}:
        raise ValueError(f'Unsupported system prompt role: {role}')
    name = f'grades/grade-{grade:02d}/{role}.yaml'
    try:
        grade_text = load_system_prompt(name)
        shared_text = load_system_prompt(f'shared/{role}.yaml')
    except (FileNotFoundError, KeyError, ValueError) as error:
        raise ValueError(f'Missing or invalid grade-{grade:02d} {role} system prompt') from error
    return f'{grade_text}\n\n{shared_text}'
