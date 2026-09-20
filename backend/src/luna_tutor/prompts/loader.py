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
