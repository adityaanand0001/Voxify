"""Streaming Text-to-Speech using ElevenLabs."""

from __future__ import annotations

import logging
import os

from elevenlabs.client import ElevenLabs
from elevenlabs import play, stream

logger = logging.getLogger(__name__)


class ElevenLabsStreamer:
    """Streams TTS audio via ElevenLabs API."""

    def __init__(self) -> None:
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not api_key:
            raise RuntimeError("ELEVENLABS_API_KEY environment variable is required")
        self.client = ElevenLabs(api_key=api_key)
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default: Rachel
        self.model = os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5")

    def stream_audio(self, text: str) -> bytes:
        """Generate TTS audio and return as raw bytes."""
        if not text.strip():
            return b""

        try:
            audio_iter = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id=self.model,
                output_format="pcm_16000",
            )

            # Collect all chunks into bytes
            audio_bytes = b""
            for chunk in audio_iter:
                if isinstance(chunk, bytes):
                    audio_bytes += chunk
            return audio_bytes
        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {e}")
            return b""

    def stream_to_bytes_iterator(self, text: str):
        """Stream TTS and yield audio chunks as bytes for WebSocket forwarding."""
        if not text.strip():
            yield b""
            return

        try:
            audio_iter = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id=self.model,
                output_format="pcm_16000",
            )
            for chunk in audio_iter:
                if isinstance(chunk, bytes):
                    yield chunk
        except Exception as e:
            logger.error(f"ElevenLabs streaming failed: {e}")
            yield b""
