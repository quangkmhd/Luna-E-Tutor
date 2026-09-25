"""Session-local Pipecat Teacher context for scripted exceptions."""

import asyncio

from luna_tutor.speech.language_segments import validate_tagged_teacher_speech
from luna_tutor.teaching.lesson_progression import (
    TEACHER_SYSTEM_PROMPT,
    TeacherInstruction,
)
from pipecat.frames.frames import LLMFullResponseStartFrame
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_context_summarizer import LLMContextSummarizer
from pipecat.services.openrouter.llm import OpenRouterLLMService
from pipecat.utils.asyncio.task_manager import TaskManager
from pipecat.utils.base_object import BaseObject
from pipecat.utils.context.llm_context_summarization import (
    LLMAutoContextSummarizationConfig,
    LLMContextSummaryConfig,
)

TEACHER_MODEL = 'google/gemini-3.5-flash-lite'


class InvalidTeacherOutputError(RuntimeError):
    """Teacher did not return usable speech for the pending lesson turn."""


def build_teacher_service(api_key: str) -> OpenRouterLLMService:
    service = OpenRouterLLMService(
        api_key=api_key,
        settings=OpenRouterLLMService.Settings(
            model=TEACHER_MODEL,
            system_instruction=TEACHER_SYSTEM_PROMPT,
        ),
    )
    service.supports_developer_role = True
    return service


class ScriptedTeacherContext:
    def __init__(self, llm: OpenRouterLLMService):
        self.llm = llm
        self.context = LLMContext()
        self._tasks = TaskManager()
        self._summarizer = LLMContextSummarizer(
            context=self.context,
            config=LLMAutoContextSummarizationConfig(
                summary_config=LLMContextSummaryConfig(llm=llm),
            ),
            auto_trigger=True,
        )
        self._summarizer_ready = False

    def snapshot(self):
        return list(self.context.get_messages())

    def restore(self, messages) -> None:
        self.context.set_messages(messages)

    def record_say(self, text: str) -> None:
        self.context.add_message({'role': 'assistant', 'content': text})

    def record_query(self, text: str) -> None:
        self.context.add_message({'role': 'user', 'content': text})

    def record_output(self, text: str) -> None:
        self.context.add_message({'role': 'assistant', 'content': text})

    def jev_history(self) -> list[dict[str, str]]:
        messages = [
            {'role': message['role'], 'content': message['content']}
            for message in self.context.get_messages()
            if message['role'] in {'assistant', 'user'}
            and isinstance(message['content'], str)
        ]
        return messages

    async def respond(self, instruction: TeacherInstruction) -> str:
        if not self._summarizer_ready:
            # The out-of-pipeline Teacher has no PipelineWorker. The summarizer
            # only needs BaseObject's managed-task setup in this arrangement.
            await BaseObject.setup(self._summarizer, self._tasks)
            self._summarizer_ready = True
        # A prior turn's rule must not become part of Pipecat's summary.
        conversation = [message for message in self.context.get_messages()
                        if message['role'] != 'developer']
        self.context.set_messages(conversation)
        # Pipecat owns the summary threshold and the conversation reduction.
        await self._summarizer.process_frame(LLMFullResponseStartFrame())
        if tasks := self._tasks.current_tasks():
            await asyncio.gather(*tasks)
        conversation = list(self.context.get_messages())
        self.context.set_messages([
            {'role': 'developer', 'content': instruction.description},
            *conversation,
        ])
        result = await self.llm.run_inference(self.context)
        for attempt in range(2):
            try:
                if not isinstance(result, str):
                    raise TypeError('Teacher speech needs valid language markup and speakable text')
                validate_tagged_teacher_speech(result.strip())
                return result.strip()
            except (TypeError, ValueError) as error:
                if attempt:
                    raise InvalidTeacherOutputError(str(error)) from error
                messages = list(self.context.get_messages())
                self.context.add_message({
                    'role': 'developer',
                    'content': ('Your previous reply had invalid language markup or no spoken text. '
                                'Reply again with only complete <vi>...</vi> and <en>...</en> '
                                'segments around the corresponding spoken languages. '
                                'Use only letters, numbers, spaces, . , ?, apostrophes inside words, '
                                'and paired ** for visual emphasis. No other symbols.'),
                })
                try:
                    result = await self.llm.run_inference(self.context)
                finally:
                    self.context.set_messages(messages)
        raise AssertionError('Unreachable Teacher retry state')

    async def close(self) -> None:
        if self._tasks.current_tasks():
            await asyncio.gather(*self._tasks.current_tasks())
        if self._summarizer_ready:
            await self._summarizer.cleanup()
