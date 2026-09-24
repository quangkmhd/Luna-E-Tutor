"""Throwaway Pipecat 1.11.0 probe for a browser-controlled Voice turn.

Run with: voice/server/.venv/bin/python voice/server/experiments/manual_submit_turn_probe.py

This probes Pipecat turn-stop strategy events and its Soniox finalize signal.
It does not open a browser, connect to Soniox, or change Luna's Voice pipeline.
"""

import asyncio

from pipecat.frames.frames import (
    Frame,
    InterimTranscriptionFrame,
    ProposedUserStartedSpeakingFrame,
    ProposedUserStoppedSpeakingFrame,
    TranscriptionFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.processors.frameworks.rtvi.frames import RTVIClientMessageFrame
from pipecat.services.soniox.stt import SonioxSTTService
from pipecat.turns.types import ProcessFrameResult
from pipecat.turns.user_stop import BaseUserTurnStopStrategy
from websockets.protocol import State


class ManualSubmitStopStrategy(BaseUserTurnStopStrategy):
    """Bridge Pipecat's client-message frame to its turn-stop event.

    Soniox may finalize a segment at a pause. A segment alone must not end the
    learner's button-controlled turn. Pipecat's user aggregator remains the
    owner of the complete transcript and LLM context; this class stores no text.
    """

    def __init__(self):
        super().__init__()
        self._submitted = False
        self._saw_final = False
        self._pending_interim = False
        self._speaking = False
        self._closed = False

    @property
    def resolves_proposed_turn_stop_frames(self) -> bool:
        # Soniox's automatic endpoint is a segment boundary, not the button.
        return True

    async def handle_user_turn_started(self):
        self._submitted = False
        self._saw_final = False
        self._pending_interim = False
        self._speaking = False
        self._closed = False

    async def handle_user_turn_stopped(self):
        self._closed = True

    async def process_frame(self, frame: Frame) -> ProcessFrameResult:
        if self._closed:
            return ProcessFrameResult.CONTINUE
        if isinstance(frame, (VADUserStartedSpeakingFrame, ProposedUserStartedSpeakingFrame)):
            self._speaking = True
        elif isinstance(frame, (VADUserStoppedSpeakingFrame, ProposedUserStoppedSpeakingFrame)):
            self._speaking = False
        elif isinstance(frame, InterimTranscriptionFrame):
            self._pending_interim = bool(frame.text.strip())
        elif isinstance(frame, TranscriptionFrame) and frame.finalized and frame.text.strip():
            self._saw_final = True
            self._pending_interim = False
        elif isinstance(frame, RTVIClientMessageFrame) and frame.type == "luna.submit-turn":
            self._submitted = True
        if self._submitted and self._saw_final and not self._pending_interim and not self._speaking:
            self._closed = True
            await self.trigger_user_turn_stopped()
        return ProcessFrameResult.CONTINUE


def final(text: str) -> TranscriptionFrame:
    return TranscriptionFrame(text=text, user_id="learner", timestamp="probe", finalized=True)


def interim(text: str) -> InterimTranscriptionFrame:
    return InterimTranscriptionFrame(text=text, user_id="learner", timestamp="probe")


def submit() -> RTVIClientMessageFrame:
    return RTVIClientMessageFrame(msg_id="probe", type="luna.submit-turn")


async def run_case(name: str, frames: list[Frame], expected_timeline: list[int]):
    strategy = ManualSubmitStopStrategy()
    stops: list[object] = []

    async def on_stopped(_strategy, params):
        stops.append(params)

    strategy.add_event_handler("on_user_turn_stopped", on_stopped)
    await strategy.handle_user_turn_started()
    assert strategy.resolves_proposed_turn_stop_frames
    assert len(frames) == len(expected_timeline)
    for frame, expected_stops in zip(frames, expected_timeline, strict=True):
        await strategy.process_frame(frame)
        assert len(stops) == expected_stops, (
            f"{name} after {type(frame).__name__}: expected {expected_stops}, got {len(stops)}"
        )
    print(f"PASS {name}: {len(stops)} turn-stop event(s)")


async def main():
    await run_case(
        "final before Send",
        [
            ProposedUserStartedSpeakingFrame(),
            final("My name"),
            ProposedUserStoppedSpeakingFrame(),
            submit(),
            submit(),
        ],
        [0, 0, 0, 1, 1],
    )
    await run_case(
        "Send before final",
        [
            VADUserStartedSpeakingFrame(),
            interim("My name"),
            submit(),
            VADUserStoppedSpeakingFrame(),
            final("My name is Quang"),
        ],
        [0, 0, 0, 0, 1],
    )
    await run_case(
        "final and Send before speech-stop signal",
        [
            ProposedUserStartedSpeakingFrame(),
            final("My name is Quang"),
            submit(),
            ProposedUserStoppedSpeakingFrame(),
        ],
        [0, 0, 0, 1],
    )
    await run_case(
        "pause then continue",
        [
            ProposedUserStartedSpeakingFrame(),
            final("My name"),
            ProposedUserStoppedSpeakingFrame(),
            ProposedUserStartedSpeakingFrame(),
            interim("is Quang"),
            submit(),
            final("is Quang"),
            ProposedUserStoppedSpeakingFrame(),
        ],
        [0, 0, 0, 0, 0, 0, 0, 1],
    )
    await run_case("Send without final remains pending", [interim("My"), submit()], [0, 0])

    class FakeWebSocket:
        state = State.OPEN

        def __init__(self):
            self.sent: list[str] = []

        async def send(self, message: str):
            self.sent.append(message)

    for pipecat_endpointing, expected in [(True, ['{"type": "finalize"}']), (False, [])]:
        service = SonioxSTTService(
            api_key="probe-only", vad_force_turn_endpoint=pipecat_endpointing
        )
        fake_socket = FakeWebSocket()
        service._websocket = fake_socket  # Probe the installed Pipecat service without network I/O.
        await service.process_frame(VADUserStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM)
        assert fake_socket.sent == expected
        print(f"PASS Pipecat endpointing={pipecat_endpointing}: {fake_socket.sent}")


if __name__ == "__main__":
    asyncio.run(main())
