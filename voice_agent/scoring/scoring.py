"""Lead scoring engine — computes dynamic lead quality score during calls."""

from __future__ import annotations

from voice_agent.state.schema import (
    Authority,
    CallState,
    Decision,
    Sentiment,
    Timeline,
)

# ── Individual scoring functions ──────────────────────────────────────────

def score_budget(budget: float | None) -> float:
    """Map dollar budget to 0.0–1.0."""
    if budget is None:
        return 0.3
    if budget >= 50000:
        return 1.0
    if budget >= 20000:
        return 0.6
    if budget >= 5000:
        return 0.4
    return 0.2


def score_timeline(timeline: Timeline) -> float:
    """Map urgency to 0.0–1.0."""
    mapping = {
        Timeline.IMMEDIATE: 1.0,
        Timeline.ONE_TO_THREE_MONTHS: 0.7,
        Timeline.THREE_TO_SIX_MONTHS: 0.4,
        Timeline.SIX_PLUS_MONTHS: 0.2,
        Timeline.UNKNOWN: 0.3,
    }
    return mapping.get(timeline, 0.3)


def score_authority(authority: Authority) -> float:
    """Map decision-making authority to 0.0–1.0."""
    mapping = {
        Authority.DECISION_MAKER: 1.0,
        Authority.INFLUENCER: 0.6,
        Authority.RESEARCHER: 0.2,
        Authority.UNKNOWN: 0.3,
    }
    return mapping.get(authority, 0.3)


def score_sentiment(sentiment: Sentiment) -> float:
    """Map sentiment to 0.0–1.0."""
    mapping = {
        Sentiment.POSITIVE: 1.0,
        Sentiment.NEUTRAL: 0.5,
        Sentiment.NEGATIVE: 0.1,
    }
    return mapping.get(sentiment, 0.5)


# ── Composite scoring ─────────────────────────────────────────────────────

# Weight distribution:
#   budget     * 0.25
#   timeline   * 0.20
#   authority  * 0.15
#   need       * 0.20
#   engagement * 0.10
#   sentiment  * 0.10

WEIGHTS = {
    "budget": 0.25,
    "timeline": 0.20,
    "authority": 0.15,
    "need": 0.20,
    "engagement": 0.10,
    "sentiment": 0.10,
}


def compute_score(state: CallState) -> float:
    """Calculate composite lead score 0–100 from current state."""
    raw = (
        score_budget(state.budget) * WEIGHTS["budget"]
        + score_timeline(state.timeline) * WEIGHTS["timeline"]
        + score_authority(state.authority) * WEIGHTS["authority"]
        + state.need_level * WEIGHTS["need"]
        + state.engagement * WEIGHTS["engagement"]
        + score_sentiment(state.sentiment) * WEIGHTS["sentiment"]
    )
    return round(raw * 100, 1)


def decide(state: CallState) -> Decision:
    """Decision engine: map score → action.

    DROP only fires when:
    - Score < 40 AND we've had enough conversation (≥4 user turns), OR
    - An objection was detected (explicit rejection), OR
    - Sentiment is explicitly negative AND engagement is very low
    """
    score = state.lead_score
    user_turns = sum(1 for t in state.history if t.get("speaker") == "user")

    # Guard: never DROP in the first few turns unless explicit rejection
    if user_turns < 4 and not state.objection:
        if score >= 80:
            return Decision.BOOK_MEETING
        if score >= 60:
            return Decision.STRONG_FOLLOWUP
        return Decision.NURTURE  # Keep the conversation going

    # Explicit rejection or very negative sentiment → DROP regardless
    if state.objection and score < 40:
        return Decision.DROP
    if state.sentiment == Sentiment.NEGATIVE and state.engagement < 0.2:
        return Decision.DROP

    if score >= 80:
        return Decision.BOOK_MEETING
    if score >= 60:
        return Decision.STRONG_FOLLOWUP
    if score >= 40:
        return Decision.NURTURE
    return Decision.DROP


def apply_objection_penalty(state: CallState, objection: str) -> None:
    """Apply penalty for detected objections."""
    if objection:
        state.objection = objection
        state.lead_score = max(0, state.lead_score - 15)
        state.decision = decide(state)


def update_state_score(state: CallState) -> None:
    """Recalculate score and decision for current state."""
    state.lead_score = compute_score(state)
    state.decision = decide(state)


def extract_budget_from_text(text: str) -> float | None:
    """Best-effort budget extraction from natural language."""
    import re

    text_lower = text.lower()

    # Direct "$X" or "Xk" patterns
    dollar_match = re.search(r'\$?\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(k|thousand|m|million)?', text_lower)
    if dollar_match:
        value = float(dollar_match.group(1).replace(",", ""))
        unit = dollar_match.group(2)
        if unit in ("k", "thousand"):
            value *= 1000
        elif unit in ("m", "million"):
            value *= 1000000
        return value

    # Phrases like "budget is around 60k"
    budget_phrase = re.search(r'budget\s+(?:is\s+)?(?:around\s+)?\$?\s?(\d{1,3}(?:,\d{3})*)\s*(k|thousand)?', text_lower)
    if budget_phrase:
        value = float(budget_phrase.group(1).replace(",", ""))
        if budget_phrase.group(2):
            value *= 1000
        return value

    return None


def extract_timeline_from_text(text: str) -> Timeline:
    """Best-effort timeline extraction from natural language."""
    text_lower = text.lower()

    immediate = ["immediately", "asap", "right now", "urgent", "today", "this week", "tomorrow"]
    short = ["1 month", "one month", "2 months", "two months", "3 months", "three months",
             "soon", "next month", "within a month", "quickly", "1-3", "couple weeks"]
    medium = ["3-6", "4 months", "5 months", "6 months", "six months", "few months",
              "quarter", "next quarter"]

    for phrase in immediate:
        if phrase in text_lower:
            return Timeline.IMMEDIATE
    for phrase in short:
        if phrase in text_lower:
            return Timeline.ONE_TO_THREE_MONTHS
    for phrase in medium:
        if phrase in text_lower:
            return Timeline.THREE_TO_SIX_MONTHS

    if any(w in text_lower for w in ["later", "next year", "someday", "not sure when", "no rush"]):
        return Timeline.SIX_PLUS_MONTHS

    return Timeline.UNKNOWN


def extract_authority_from_text(text: str) -> Authority:
    """Best-effort authority extraction from natural language."""
    text_lower = text.lower()

    decision_maker = ["i decide", "i handle", "i'm the", "i am the", "my decision",
                      "i make the", "final say", "i own", "ceo", "founder", "owner"]
    influencer = ["recommend", "suggest", "influence", "vet", "evaluate", "my team",
                  "i'll need to", "run it by", "talk to my"]
    researcher = ["researching", "looking around", "comparing", "just browsing",
                  "checking options", "seeing what", "exploring"]

    for phrase in decision_maker:
        if phrase in text_lower:
            return Authority.DECISION_MAKER
    for phrase in influencer:
        if phrase in text_lower:
            return Authority.INFLUENCER
    for phrase in researcher:
        if phrase in text_lower:
            return Authority.RESEARCHER

    return Authority.UNKNOWN
