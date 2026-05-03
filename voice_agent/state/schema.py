"""State schema for AI Sales Call Agent — the single source of truth."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CallStage(str, Enum):
    GREETING = "greeting"
    DISCOVERY = "discovery"
    QUALIFICATION = "qualification"
    OBJECTION = "objection"
    BOOKING = "booking"
    CLOSING = "closing"
    DONE = "done"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Decision(str, Enum):
    BOOK_MEETING = "BOOK_MEETING"
    STRONG_FOLLOWUP = "STRONG_FOLLOWUP"
    NURTURE = "NURTURE"
    DROP = "DROP"


class Authority(str, Enum):
    DECISION_MAKER = "decision_maker"
    INFLUENCER = "influencer"
    RESEARCHER = "researcher"
    UNKNOWN = "unknown"


class Timeline(str, Enum):
    IMMEDIATE = "immediate"
    ONE_TO_THREE_MONTHS = "1-3 months"
    THREE_TO_SIX_MONTHS = "3-6 months"
    SIX_PLUS_MONTHS = "6+ months"
    UNKNOWN = "unknown"


@dataclass
class CallState:
    """Full conversational state for a single sales call."""

    # ── Identity ──
    lead_id: str = ""
    name: str = ""
    phone: str = ""
    company: str = ""

    # ── Extracted fields ──
    budget: float | None = None
    timeline: Timeline = Timeline.UNKNOWN
    authority: Authority = Authority.UNKNOWN
    need_level: float = 0.0       # 0.0 — 1.0
    engagement: float = 0.0       # 0.0 — 1.0
    sentiment: Sentiment = Sentiment.NEUTRAL

    # ── Computed ──
    lead_score: float = 0.0        # 0–100
    decision: Decision = Decision.NURTURE
    objection: str = ""

    # ── Flow control ──
    stage: CallStage = CallStage.GREETING
    history: list[dict[str, str]] = field(default_factory=list)
    extracted_fields: dict[str, Any] = field(default_factory=dict)

    # ── Call metadata ──
    call_sid: str = ""
    twilio_stream_sid: str = ""
    call_active: bool = True
    tts_playing: bool = False

    def add_turn(self, speaker: str, text: str) -> None:
        """Record a conversation turn."""
        self.history.append({"speaker": speaker, "text": text})

    @property
    def transcript(self) -> str:
        return "\n".join(f"{t['speaker']}: {t['text']}" for t in self.history)

    @property
    def is_qualified(self) -> bool:
        return self.lead_score >= 40

    @property
    def is_hot(self) -> bool:
        return self.lead_score >= 80

    def to_dict(self) -> dict:
        return {
            "lead_id": self.lead_id,
            "name": self.name,
            "budget": self.budget,
            "timeline": self.timeline.value if isinstance(self.timeline, Timeline) else self.timeline,
            "authority": self.authority.value if isinstance(self.authority, Authority) else self.authority,
            "need_level": self.need_level,
            "engagement": self.engagement,
            "sentiment": self.sentiment.value if isinstance(self.sentiment, Sentiment) else self.sentiment,
            "lead_score": self.lead_score,
            "decision": self.decision.value if isinstance(self.decision, Decision) else self.decision,
            "stage": self.stage.value if isinstance(self.stage, CallStage) else self.stage,
            "objection": self.objection,
        }
