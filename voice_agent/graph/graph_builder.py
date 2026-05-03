"""LangGraph graph builder — unified semantic analysis pipeline.

Architecture per turn:
  analyze (Gemini) → scoring → response → action

The UnifiedAnalyzer replaces the old listener + extraction + objection nodes
with a single Gemini call that handles sentiment, engagement, stage detection,
field extraction (budget/timeline/authority/need), and objection detection.
"""

from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import StateGraph, END

from voice_agent.state.schema import CallState, CallStage, Decision
from voice_agent.scoring.scoring import (
    apply_objection_penalty,
    update_state_score,
)
from voice_agent.agents.listener import (
    UnifiedAnalyzer,
    ResponseGenerator,
    GeminiClient,
)

logger = logging.getLogger(__name__)

# ── Shared LLM client ────────────────────────────────────────────────────

_gemini: GeminiClient | None = None

def _get_gemini() -> GeminiClient:
    global _gemini
    if _gemini is None:
        _gemini = GeminiClient()
    return _gemini


# ── Node implementations ─────────────────────────────────────────────────

def analyze_node(state: CallState) -> CallState:
    """Unified semantic analysis: sentiment, engagement, stage,
    field extraction (budget/timeline/authority/need), and objection detection.
    One Gemini call per turn. Falls back to regex when Gemini unavailable.
    """
    analyzer = UnifiedAnalyzer(_get_gemini())
    state = analyzer.analyze(state)

    # Apply objection penalty if detected by analyzer
    if state.objection:
        apply_objection_penalty(state, state.objection)
        logger.info("Objection: %s → score %.1f", state.objection, state.lead_score)

    logger.info(
        "Analysis: stage=%s sentiment=%s eng=%.2f budget=%s timeline=%s auth=%s need=%.2f",
        state.stage.value if hasattr(state.stage, 'value') else state.stage,
        state.sentiment.value if hasattr(state.sentiment, 'value') else state.sentiment,
        state.engagement,
        state.budget,
        state.timeline.value if hasattr(state.timeline, 'value') else state.timeline,
        state.authority.value if hasattr(state.authority, 'value') else state.authority,
        state.need_level,
    )
    return state


def scoring_node(state: CallState) -> CallState:
    """Compute lead score and decision from extracted fields."""
    update_state_score(state)
    logger.info(
        "Scored: %s → %.1f (%s)",
        state.name or state.lead_id,
        state.lead_score,
        state.decision.value if hasattr(state.decision, 'value') else state.decision,
    )
    return state


def response_node(state: CallState) -> CallState:
    """Generate agent response via Gemini (or fallback)."""
    gen = ResponseGenerator(_get_gemini())
    response = gen.generate(state)
    state.add_turn("agent", response)
    return state


def action_node(state: CallState) -> CallState:
    """Execute post-response actions. Only ends call on DROP after
    sufficient conversation or explicit objection."""
    user_turns = sum(1 for t in state.history if t.get("speaker") == "user")

    if state.decision == Decision.BOOK_MEETING and state.stage == CallStage.BOOKING:
        logger.info("Booking flow triggered for %s", state.name)

    if state.decision == Decision.DROP:
        if user_turns >= 4 or state.objection:
            state.stage = CallStage.CLOSING
            state.call_active = False
            logger.info("Ending call: DROP after %d turns", user_turns)
        else:
            logger.info("Delaying DROP: %d turns, continuing", user_turns)

    return state


# ── Routing ──────────────────────────────────────────────────────────────

def should_continue(state: CallState) -> Literal["end", "respond"]:
    if not state.call_active or state.stage == CallStage.DONE:
        return "end"
    return "respond"


# ── Graph builder ────────────────────────────────────────────────────────

def build_call_graph() -> StateGraph:
    """Construct the LangGraph state graph: analyze → score → respond → act."""

    workflow = StateGraph(CallState)

    workflow.add_node("analyze", analyze_node)
    workflow.add_node("scoring", scoring_node)
    workflow.add_node("response", response_node)
    workflow.add_node("action", action_node)

    workflow.set_entry_point("analyze")

    workflow.add_edge("analyze", "scoring")
    workflow.add_edge("scoring", "response")
    workflow.add_edge("response", "action")

    workflow.add_conditional_edges(
        "action",
        should_continue,
        {"end": END, "respond": END},
    )

    return workflow.compile()


_call_graph = None

def get_call_graph():
    global _call_graph
    if _call_graph is None:
        _call_graph = build_call_graph()
    return _call_graph
