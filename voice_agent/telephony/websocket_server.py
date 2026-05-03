"""WebSocket server — bridges Twilio media stream ↔ call agent."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import threading

from voice_agent.state.schema import CallState
from voice_agent.graph.graph_builder import get_call_graph

logger = logging.getLogger(__name__)


class MediaStreamHandler:
    """Handles a single Twilio Media Stream WebSocket connection."""

    def __init__(self, lead_id: str, websocket) -> None:
        from voice_agent.stt.whisper_stream import WhisperStreamTranscriber
        from voice_agent.tts.elevenlabs_stream import ElevenLabsStreamer

        self.lead_id = lead_id
        self.ws = websocket
        self.state = CallState(lead_id=lead_id)
        self.transcriber = WhisperStreamTranscriber()
        self.tts = ElevenLabsStreamer()
        self.graph = get_call_graph()
        self._tts_lock = asyncio.Lock()
        self._last_agent_text = ""

    async def handle_message(self, message: dict) -> None:
        """Process a single Twilio media stream message."""
        event = message.get("event", "")

        if event == "connected":
            logger.info("Media stream connected for lead %s", self.lead_id)
            # Kick off with greeting
            from voice_agent.config.business_context import get_business_context
            biz = get_business_context()
            await self._speak_and_send(
                f"Hi, this is {biz.agent_name} from {biz.company_name}. "
                f"Am I speaking with the right person?"
            )

        elif event == "start":
            # Stream started — save stream SID
            self.state.twilio_stream_sid = message.get("streamSid", "")
            logger.info("Stream started: %s", self.state.twilio_stream_sid)

        elif event == "media":
            # Audio payload from Twilio
            payload_b64 = message.get("media", {}).get("payload", "")
            if not payload_b64:
                return

            # Decode µ-law → PCM bytes
            audio_bytes = base64.b64decode(payload_b64)

            # Feed to transcriber
            self.transcriber.add_audio(audio_bytes)

            # Transcribe every ~1 second worth of audio
            if len(self.transcriber.buffer) >= 5:
                text = self.transcriber.transcribe_and_clear()
                if text:
                    logger.info("Heard: %s", text)
                    await self._process_user_text(text)

        elif event == "stop":
            logger.info("Stream stopped for lead %s", self.lead_id)
            await self._end_call()

    async def _process_user_text(self, text: str) -> None:
        """Run user text through the call graph and respond."""
        self.state.add_turn("user", text)
        self.state.call_active = True

        # Run through LangGraph
        try:
            result = self.graph.invoke(self.state)
            # result is the updated state
            if hasattr(result, "history"):
                self.state = result
        except Exception as e:
            logger.error("Graph invocation failed: %s", e)

        # Check for agent response in history
        agent_turns = [t for t in self.state.history if t["speaker"] == "agent"]
        if agent_turns:
            response_text = agent_turns[-1]["text"]
            if response_text != self._last_agent_text:
                await self._speak_and_send(response_text)
                self._last_agent_text = response_text

        # Check if call should end
        if not self.state.call_active:
            await self._end_call()

    async def _speak_and_send(self, text: str) -> None:
        """Generate TTS audio and stream it to Twilio."""
        state = self.state

        # Generate audio
        audio_iter = self.tts.stream_to_bytes_iterator(text)
        self._last_agent_text = text

        # Stream chunks back to Twilio
        for chunk in audio_iter:
            if not chunk:
                continue
            payload = base64.b64encode(chunk).decode("ascii")
            message = {
                "event": "media",
                "streamSid": state.twilio_stream_sid,
                "media": {"payload": payload},
            }
            try:
                await self.ws.send(json.dumps(message))
                await asyncio.sleep(0.02)  # Small chunk pacing
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket closed during TTS send")
                break

    async def _end_call(self) -> None:
        """Clean up and close the WebSocket."""
        self.state.stage = self.state.stage  # keep last stage
        self.state.call_active = False
        logger.info(
            "Call ended for %s — score: %.1f, decision: %s",
            self.state.name or self.state.lead_id,
            self.state.lead_score,
            self.state.decision.value if hasattr(self.state.decision, 'value') else self.state.decision,
        )
        try:
            await self.ws.close()
        except Exception:
            pass


async def handle_connection(websocket) -> None:
    """WebSocket connection handler — one per call."""
    # Extract lead_id from query params
    path = websocket.request.path if hasattr(websocket, 'request') else ""
    lead_id = "unknown"

    if "?" in path:
        from urllib.parse import parse_qs, urlparse
        qs = parse_qs(urlparse(path).query)
        lead_id = qs.get("lead_id", ["unknown"])[0]

    logger.info("New media stream connection for lead %s", lead_id)

    handler = MediaStreamHandler(lead_id, websocket)

    try:
        async for raw_message in websocket:
            try:
                message = json.loads(raw_message)
                await handler.handle_message(message)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from WebSocket")
    except websockets.exceptions.ConnectionClosed:
        logger.info("WebSocket closed for lead %s", lead_id)
    finally:
        # Persist call result
        logger.info(
            "Call complete — lead=%s score=%.1f decision=%s",
            lead_id,
            handler.state.lead_score,
            handler.state.decision.value if hasattr(handler.state.decision, 'value') else handler.state.decision,
        )


def start_server(host: str = "0.0.0.0", port: int = 8080):
    """Start the WebSocket server."""
    import websockets

    logger.info("Starting media stream server on %s:%d", host, port)
    async def _serve():
        async with websockets.serve(handle_connection, host, port):
            await asyncio.Future()  # Run forever

    threading.Thread(target=lambda: asyncio.run(_serve()), daemon=True).start()
