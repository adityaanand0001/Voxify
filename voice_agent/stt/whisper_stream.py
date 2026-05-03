"""Streaming Speech-to-Text using local Whisper."""

from __future__ import annotations

import logging
import os

import numpy as np

logger = logging.getLogger(__name__)


class WhisperStreamTranscriber:
    """Streams audio chunks through Whisper for real-time transcription."""

    def __init__(self, model_name: str = "base") -> None:
        import whisper
        self.model = whisper.load_model(model_name)
        self.buffer: list[np.ndarray] = []
        self.sample_rate = 16000

    def add_audio(self, audio_bytes: bytes) -> None:
        """Add raw PCM audio bytes to buffer."""
        # Convert 16-bit PCM bytes → numpy array
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        self.buffer.append(audio_np)

    def transcribe(self, clear_buffer: bool = True) -> str:
        """Transcribe current buffer contents."""
        if not self.buffer:
            return ""

        audio = np.concatenate(self.buffer)
        if clear_buffer:
            self.buffer = []

        if len(audio) < self.sample_rate * 0.3:  # Minimum 300ms of audio
            return ""

        try:
            result = self.model.transcribe(audio, language="en", fp16=False)
            return result.get("text", "").strip()
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            return "" if clear_buffer else ""

    def transcribe_and_clear(self) -> str:
        """Transcribe and clear buffer."""
        text = self.transcribe(clear_buffer=True)
        # Re-shove if transcription failed (non-empty buffer needed)
        return text
