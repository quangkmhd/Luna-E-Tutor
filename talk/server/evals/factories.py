"""Provider factories used only by the behavioral eval harness."""

import os

from pipecat.services.openai.llm import OpenAILLMService


def build_gemini_judge(config: dict) -> OpenAILLMService:
    """Build an OpenAI-compatible Gemini judge for semantic criteria."""
    return OpenAILLMService(
        api_key=os.environ["GEMINI_API_KEY"],
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        settings=OpenAILLMService.Settings(model=config["model"]),
    )
