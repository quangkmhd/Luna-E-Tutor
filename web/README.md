# Luna web client

## Getting started

From the repository root, start the complete local stack:

```bash
./scripts/run-local.sh
```

Open [http://localhost:3090/speaking](http://localhost:3090/speaking).

## Speaking voice architecture

The speaking room uses the official `@pipecat-ai/client-react` integration. Its provider owns the Pipecat client context, media state, conversation aggregation, and bot audio playback. Application components use Pipecat hooks; they do not construct browser audio elements, media streams, or a second WebRTC client.

The REST API stores curriculum state and durable lesson history. It is synchronized after a completed assistant message, but it is not polled or used to replace the live transcript/TTS conversation.

SmallWebRTC connects to `${NEXT_PUBLIC_SPEAKING_VOICE_URL}/start`. If `NEXT_PUBLIC_SPEAKING_VOICE_URL` is unset, the client uses the page hostname on port `7860`; for example, a page opened at `http://server:3090` connects to `http://server:7860/start`.

For remote browser access, the voice endpoint must also be reachable. Forward both ports (`3090` for web and `7860` for Pipecat voice), or expose one public origin and reverse-proxy the voice endpoint. If a proxy gives voice a separate URL, set `NEXT_PUBLIC_SPEAKING_VOICE_URL` before building or running Next.js.

The curriculum REST API defaults to `http://localhost:8000`; override it with `NEXT_PUBLIC_TUTOR_API_URL` when the API is served elsewhere.

## Web-only development

```bash
npm run dev --workspace web
```
