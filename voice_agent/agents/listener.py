"""Call agents — Gemini-first semantic analysis. Regex is emergency fallback only.

Business context (company info, product, pricing, objections, guardrails)
is injected from config/business_context.py. Edit that file to change what
the agent knows about your business — no prompt editing needed.
"""

from __future__ import annotations

import json
import logging
import os

from voice_agent.state.schema import (
    Authority,
    CallStage,
    CallState,
    Decision,
    Sentiment,
    Timeline,
)
from voice_agent.scoring.scoring import (
    extract_authority_from_text,
    extract_budget_from_text,
    extract_timeline_from_text,
)

logger = logging.getLogger(__name__)

# ── Prompt builders (inject business context at runtime) ──────────────────

def _build_analysis_prompt(state: CallState, biz) -> str:
    """Build the semantic analysis prompt with business context."""
    budget_str = f"${int(state.budget)}" if state.budget else "unknown"
    tl_str = state.timeline.value if hasattr(state.timeline, 'value') else str(state.timeline)
    auth_str = state.authority.value if hasattr(state.authority, 'value') else str(state.authority)
    sent_str = state.sentiment.value if hasattr(state.sentiment, 'value') else str(state.sentiment)
    stage_str = state.stage.value if hasattr(state.stage, 'value') else str(state.stage)

    return f"""You are analyzing a live sales call for {biz.company_name}, a company that {biz.company_description[:200]}.

The agent is selling: {biz.product_name} — {biz.value_proposition[:200]}

PREVIOUS STATE:
- Stage: {stage_str}
- Sentiment: {sent_str}
- Engagement: {state.engagement}
- Budget extracted: {budget_str}
- Timeline extracted: {tl_str}
- Authority extracted: {auth_str}
- Need level: {state.need_level}

FULL TRANSCRIPT:
{state.transcript[-2000:]}

LAST USER MESSAGE: "{state.history[-1]['text'] if state.history else ''}"

Analyze the conversation and return a JSON object with these EXACT keys:
- sentiment: "positive", "neutral", or "negative"
- engagement: float 0.0-1.0
- stage: "greeting", "discovery", "qualification", "objection", "booking", or "closing"
- budget: number or null (dollar amount mentioned)
- timeline: "immediate", "1-3 months", "3-6 months", "6+ months", or "unknown"
- authority: "decision_maker", "influencer", "researcher", or "unknown"
- need_level: float 0.0-1.0
- objection: "" or objection type ("not_interested", "price", "timing", "competitor", "gatekeeper")

Only output valid JSON. No markdown, no explanation."""


def _build_response_prompt(state: CallState, biz) -> str:
    """Build the conversational response prompt with business context."""
    budget_str = f"${int(state.budget)}" if state.budget else "unknown"
    tl_str = state.timeline.value if hasattr(state.timeline, 'value') else str(state.timeline)
    auth_str = state.authority.value if hasattr(state.authority, 'value') else str(state.authority)
    sent_str = state.sentiment.value if hasattr(state.sentiment, 'value') else str(state.sentiment)
    stage_str = state.stage.value if hasattr(state.stage, 'value') else str(state.stage)
    dec_str = state.decision.value if hasattr(state.decision, 'value') else str(state.decision)

    decision_guidance = {
        Decision.BOOK_MEETING: "Goal: Move toward booking. Be direct, suggest a specific day/time.",
        Decision.STRONG_FOLLOWUP: "Goal: Secure follow-up commitment. Build urgency around their needs.",
        Decision.NURTURE: "Goal: Keep it warm. Ask discovery questions that reveal pain points.",
        Decision.DROP: "Goal: End politely. Don't push. Keep the door open.",
    }.get(state.decision, "")

    objection_note = ""
    if state.objection:
        obj_guidance = biz.objection_responses.get(state.objection, "")
        objection_note = f"\nObjection: {state.objection}. Guidance: {obj_guidance}"

    guardrails = "\n".join(f"  - {g}" for g in biz.do_not_say)

    return f"""You are {biz.agent_name}, a sales agent for {biz.company_name}.

{biz.company_description}

You are selling: {biz.product_name}
Value prop: {biz.value_proposition}

PRICING (mention only when asked or relevant):
{chr(10).join(f"  {t['name']}: {t['price']} — {t['includes']}" for t in biz.pricing_tiers)}
{biz.pricing_note}

IDEAL PROFILE: {biz.ideal_customer_profile[:200]}

BOOKING: {biz.meeting_duration} calls, {biz.available_days}, {biz.available_times}

CURRENT CALL STATE:
- Lead: {state.name or 'Unknown'} at {state.company or 'Unknown'}
- Score: {state.lead_score:.0f}/100 → {dec_str}
- Stage: {stage_str}
- Budget: {budget_str} | Timeline: {tl_str} | Authority: {auth_str}
- Sentiment: {sent_str} | Engagement: {state.engagement:.2f}

{decision_guidance}
{objection_note}

RECENT TRANSCRIPT:
{state.transcript[-800:]}

NEVER:
{guardrails}

Generate your response (max 2 sentences, natural tone, helpful not pushy):"""


# ── Gemini client ───────────────────────────────────────────────────────

class GeminiClient:
    """Thin wrapper around Gemini for consistent prompt → response flow.
    When GEMINI_API_KEY is unset, returns empty strings so callers
    fall back to basic regex extraction and default responses.
    """

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            self.model = None
            return
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def generate(self, prompt: str, temperature: float = 0.3) -> str:
        if self.model is None:
            return ""
        try:
            resp = self.model.generate_content(
                prompt,
                generation_config={"temperature": temperature, "max_output_tokens": 512},
            )
            return resp.text or ""
        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            return ""

    @property
    def available(self) -> bool:
        return self.model is not None


# ── Unified Analyzer (replaces listener + extraction + objection) ────────

class UnifiedAnalyzer:
    """One Gemini call per turn — analyzes sentiment, engagement, stage,
    extracts budget/timeline/authority/need, and detects objections.
    Injects full business context (product, pricing, objections, guardrails).
    Falls back to regex only when Gemini is unavailable."""

    def __init__(self, gemini: GeminiClient) -> None:
        self.gemini = gemini
        from voice_agent.config.business_context import get_business_context
        self.biz = get_business_context()

    def analyze(self, state: CallState) -> CallState:
        """Run full semantic analysis on the current call state.
        Mutates state in place, returns it for graph chaining."""

        if not state.history:
            return state

        # ── Primary: Gemini semantic analysis ──
        if self.gemini.available:
            result = self._analyze_with_gemini(state)
            if result:
                self._apply_analysis(state, result)
                return state

        # ── Fallback: regex extraction (degraded mode) ──
        last_user = next(
            (t["text"] for t in reversed(state.history) if t["speaker"] == "user"),
            "",
        )
        if last_user:
            self._analyze_with_regex(state, last_user)
        return state

    def _analyze_with_gemini(self, state: CallState) -> dict | None:
        """Call Gemini for full semantic analysis using business context."""
        prompt = _build_analysis_prompt(state, self.biz)
        raw = self.gemini.generate(prompt, temperature=0.2)
        if not raw:
            return None

        try:
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                if raw.endswith("```"):
                    raw = raw[:-3]
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(f"Gemini JSON parse failed: {e} | raw: {raw[:200]}")
            return None

    def _apply_analysis(self, state: CallState, result: dict) -> None:
        """Apply Gemini analysis results to state."""
        # Sentiment
        try:
            state.sentiment = Sentiment(result.get("sentiment", "neutral"))
        except ValueError:
            pass

        # Engagement
        eng = result.get("engagement")
        if eng is not None:
            state.engagement = max(0.0, min(1.0, float(eng)))

        # Stage
        stage_str = result.get("stage", "")
        try:
            if stage_str in CallStage.__members__.values():
                state.stage = CallStage(stage_str)
        except ValueError:
            pass

        # Budget
        budget = result.get("budget")
        if budget is not None and budget != 0:
            state.budget = float(budget)

        # Timeline
        tl = result.get("timeline", "")
        try:
            if tl in Timeline.__members__.values():
                state.timeline = Timeline(tl)
        except ValueError:
            pass

        # Authority
        auth = result.get("authority", "")
        try:
            if auth in Authority.__members__.values():
                state.authority = Authority(auth)
        except ValueError:
            pass

        # Need level
        need = result.get("need_level")
        if need is not None:
            state.need_level = max(0.0, min(1.0, float(need)))

        # Objection
        objection = result.get("objection", "")
        if objection and objection != "None":
            state.objection = str(objection)

        # Persist
        state.extracted_fields.update({
            "budget": state.budget,
            "timeline": state.timeline.value if hasattr(state.timeline, 'value') else str(state.timeline),
            "authority": state.authority.value if hasattr(state.authority, 'value') else str(state.authority),
            "need_level": state.need_level,
        })

    def _analyze_with_regex(self, state: CallState, text: str) -> None:
        """Emergency fallback: regex extraction when Gemini is unavailable.
        This is degraded mode — use Gemini for production."""
        text_lower = text.lower()
        user_turns = sum(1 for t in state.history if t.get("speaker") == "user")

        # ── Extraction (regex) ──
        b = extract_budget_from_text(text)
        if b is not None:
            state.budget = b

        tl = extract_timeline_from_text(text)
        if tl != Timeline.UNKNOWN:
            state.timeline = tl

        auth = extract_authority_from_text(text)
        if auth != Authority.UNKNOWN:
            state.authority = auth

        has_info = (
            extract_budget_from_text(state.transcript) is not None
            or extract_timeline_from_text(state.transcript) != Timeline.UNKNOWN
            or extract_authority_from_text(state.transcript) != Authority.UNKNOWN
        )

        # ── Sentiment (regex) ──
        positive_signals = ["great", "interesting", "sounds good", "let's", "love",
                           "perfect", "exactly", "tell me more", "set up"]
        negative_signals = ["not interested", "stop calling", "don't call", "go away",
                           "waste of time", "leave me"]
        pos = sum(1 for s in positive_signals if s in text_lower)
        neg = sum(1 for s in negative_signals if s in text_lower)
        if neg > pos:
            state.sentiment = Sentiment.NEGATIVE
        elif pos > 0:
            state.sentiment = Sentiment.POSITIVE

        # ── Engagement (regex) ──
        eng_signals = ["tell me more", "how does", "what about", "pricing", "cost",
                      "budget", "timeline", "interested", "set up", "meet", "schedule",
                      "looking for", "need", "call", "great", "sounds good", "yes"]
        eng_hits = sum(1 for s in eng_signals if s in text_lower)
        state.engagement = max(state.engagement, min(1.0, eng_hits * 0.15))

        # Need level (regex)
        need_signals = ["need", "looking for", "pain point", "problem", "challenge",
                       "urgent", "asap", "crucial", "critical", "budget", "timeline"]
        need_hits = sum(1 for s in need_signals if s in text_lower)
        state.need_level = max(state.need_level, min(1.0, need_hits * 0.15))

        # ── Stage progression (regex) ──
        booking_signals = ["set up a call", "let's meet", "schedule", "book", "calendar",
                          "next week", "next tuesday", "thursday", "friday", "meeting"]
        objection_signals = ["not interested", "stop calling", "don't call", "don't need"]

        if any(s in text_lower for s in objection_signals):
            state.stage = CallStage.OBJECTION
            state.objection = "not_interested"
        elif any(s in text_lower for s in booking_signals):
            state.stage = CallStage.BOOKING
        elif has_info:
            state.stage = CallStage.QUALIFICATION
        elif user_turns >= 2 and state.stage == CallStage.GREETING:
            state.stage = CallStage.DISCOVERY


# ── Response Generator ──────────────────────────────────────────────────

class ResponseGenerator:
    """Generates contextual sales responses using business-aware Gemini prompts."""

    def __init__(self, gemini: GeminiClient) -> None:
        self.gemini = gemini
        from voice_agent.config.business_context import get_business_context
        self.biz = get_business_context()

    def generate(self, state: CallState) -> str:
        """Generate the next agent response with full business context."""

        if self.gemini.available:
            prompt = _build_response_prompt(state, self.biz)
            response = self.gemini.generate(prompt, temperature=0.7)
            if response:
                return response.strip()

        # ── Emergency fallback responses (Gemini unavailable) ──
        return self._fallback(state)

    def _fallback(self, state: CallState) -> str:
        """Emergency fallback when Gemini is unavailable — uses biz context."""
        biz = self.biz
        if state.stage == CallStage.GREETING:
            return f"Hi {state.name or 'there'}, this is {biz.agent_name} from {biz.company_name}. How are you doing today?"
        if state.decision == Decision.BOOK_MEETING:
            return f"Based on what you've shared, I think it'd be worth setting up a quick call. How does {biz.available_days.split(' through')[0]} look?"
        if state.decision == Decision.STRONG_FOLLOWUP:
            return f"That's great to hear. Let me follow up with more details on how {biz.company_name} can help."
        if state.decision == Decision.DROP:
            return "Understood, I appreciate your time. Feel free to reach out if anything changes. Take care!"
        if state.stage == CallStage.BOOKING:
            return f"Great, let's get something on the calendar. How does next {biz.available_days.split(' through')[0]} look?"
        return f"Could you tell me a bit more about what you're looking for? I want to make sure {biz.company_name} is the right fit."
