"""Keep interrupted TTS captions out of the next spoken turn."""

from loguru import logger
from pipecat.frames.frames import InterruptionFrame
from pipecat.observers.base_observer import FramePushed
from pipecat.processors.frameworks.rtvi import RTVIObserver, RTVIObserverParams, RTVIProcessor


class LunaRTVIObserver(RTVIObserver):
    async def on_push_frame(self, data: FramePushed):
        if isinstance(data.frame, InterruptionFrame) and data.frame.id not in self._frames_seen:
            # Pipecat queues text announcements until BotStartedSpeakingFrame.
            # When a greeting is interrupted before its first audio frame, the
            # next utterance's start must not publish that greeting as spoken.
            if self._queued_aggregated_text_frames:
                logger.info(
                    "Discarded {} unspoken TTS caption(s) on interruption",
                    len(self._queued_aggregated_text_frames),
                )
                self._queued_aggregated_text_frames.clear()
            self._bot_is_speaking = False
        await super().on_push_frame(data)


class LunaRTVIProcessor(RTVIProcessor):
    def create_rtvi_observer(self, *, params: RTVIObserverParams | None = None, **kwargs):
        return LunaRTVIObserver(self, params=params, **kwargs)
