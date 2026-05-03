"""Main entry point for AI Sales Call Agent."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from voice_agent.state.schema import CallState, Decision, CallStage, Sentiment, Timeline, Authority
from voice_agent.scoring.scoring import compute_score, decide

# ── Logging ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-24s %(levelname)-8s %(message)s",
)
logger = logging.getLogger("call-agent")


# ── Config ──────────────────────────────────────────────────────────────

WS_HOST = os.getenv("WS_HOST", "0.0.0.0")
WS_PORT = int(os.getenv("WS_PORT", "8080"))
WS_BASE_URL = os.getenv("WS_BASE_URL", f"wss://{os.getenv('PUBLIC_HOST', 'localhost')}:{WS_PORT}")


# ── Call orchestrator ───────────────────────────────────────────────────

class CallAgent:
    """Top-level orchestrator: fetch leads → call → log results."""

    def __init__(self) -> None:
        from voice_agent.telephony.twilio_handler import TwilioCallManager
        from voice_agent.db.models import Database

        self.twilio = TwilioCallManager()
        try:
            self.db = Database()
        except RuntimeError:
            logger.warning("Database not configured — running without persistence")
            self.db = None

    def call_lead(self, lead: dict) -> dict | None:
        """Call a single lead and return call info."""
        to_number = lead.get("phone") or lead.get("Phone") or ""
        if not to_number:
            logger.warning("Lead %s has no phone number — skipping", lead.get("id"))
            return None

        result = self.twilio.make_call(
            to_number=to_number,
            lead_id=lead.get("id", "unknown"),
            ws_base_url=WS_BASE_URL,
        )
        return result

    def batch_call(self, limit: int = 10) -> list[dict]:
        """Fetch pending leads and call them."""
        if not self.db:
            logger.error("Cannot batch call: no database configured")
            return []

        leads = self.db.get_leads_to_call(limit)
        logger.info("Calling %d leads", len(leads))

        results = []
        for lead in leads:
            result = self.call_lead(lead)
            if result:
                results.append(result)
                logger.info("  → %s: %s", lead.get("name", lead.get("id")), result["status"])

        return results


# ── Dry-run / testing ───────────────────────────────────────────────────

def dry_run_sample() -> dict:
    """Run the scoring engine against a sample lead without making a call."""
    state = CallState(
        lead_id="test-001",
        name="Sarah Chen",
        company="DataPipes Inc.",
        budget=60000,
        timeline="immediate",
        authority="decision_maker",
        need_level=0.9,
        engagement=0.8,
        sentiment="positive",
    )

    score = compute_score(state)
    decision = decide(state)
    state.lead_score = score
    state.decision = decision

    return {
        "lead": state.name,
        "company": state.company,
        "budget": state.budget,
        "timeline": state.timeline,
        "authority": state.authority,
        "need": state.need_level,
        "score": state.lead_score,
        "decision": state.decision.value if hasattr(state.decision, 'value') else str(state.decision),
    }


def simulate_conversation() -> list[dict]:
    """Simulate a call through the LangGraph engine (no audio/telephony)."""
    from voice_agent.graph.graph_builder import get_call_graph

    state = CallState(lead_id="test-002", name="Mark Rivera")

    graph = get_call_graph()

    test_utterances = [
        "Hi, who's this?",
        "Yeah, I handle procurement for our team. We've been looking for something like this.",
        "Our budget is around 75k and we need it live within 2 months.",
        "That sounds interesting, tell me more.",
        "Actually, what's the pricing breakdown look like?",
        "Okay, let's set up a call for next week.",
    ]

    turns = []
    for i, utterance in enumerate(test_utterances):
        state.add_turn("user", utterance)
        state.call_active = True

        try:
            result = graph.invoke(state)
            # LangGraph may return a dict or the dataclass itself
            if isinstance(result, CallState):
                state = result
            elif isinstance(result, dict) and "history" in result:
                # Reconstruct state from dict — convert string enums back
                for key, val in result.items():
                    if key == "stage" and isinstance(val, str):
                        try:
                            state.stage = CallStage(val)
                        except ValueError:
                            pass
                    elif key == "decision" and isinstance(val, str):
                        try:
                            state.decision = Decision(val)
                        except ValueError:
                            pass
                    elif key == "sentiment" and isinstance(val, str):
                        try:
                            state.sentiment = Sentiment(val)
                        except ValueError:
                            pass
                    elif key == "timeline" and isinstance(val, str):
                        try:
                            state.timeline = Timeline(val)
                        except ValueError:
                            pass
                    elif key == "authority" and isinstance(val, str):
                        try:
                            state.authority = Authority(val)
                        except ValueError:
                            pass
                    elif key in ("lead_score", "budget", "need_level", "engagement"):
                        setattr(state, key, val)
                    elif key == "objection":
                        state.objection = val or ""
                if "history" in result:
                    state.history = result["history"]
            else:
                # Fallback: run scoring manually on accumulated transcript
                from voice_agent.scoring.scoring import (
                    extract_budget_from_text,
                    extract_timeline_from_text,
                    extract_authority_from_text,
                    update_state_score,
                )
                b = extract_budget_from_text(state.transcript)
                if b is not None:
                    state.budget = b
                state.timeline = extract_timeline_from_text(state.transcript)
                state.authority = extract_authority_from_text(state.transcript)
                if "interested" in state.transcript.lower():
                    state.engagement = 0.7
                    state.need_level = 0.6
                update_state_score(state)
        except Exception as e:
            logger.error("Graph error on turn %d: %s", i, e)
            break

        last = state.history[-1] if state.history else {}
        turns.append({
            "turn": i + 1,
            "user": utterance,
            "agent": last.get("text", "") if last.get("speaker") == "agent" else "",
            "score": state.lead_score,
            "decision": state.decision.value if hasattr(state.decision, 'value') else str(state.decision),
            "stage": state.stage.value if hasattr(state.stage, 'value') else str(state.stage),
        })

    return turns


# ── CLI ─────────────────────────────────────────────────────────────────

def main() -> None:
    """Main entry point — supports 'serve', 'test', 'simulate' modes."""
    mode = sys.argv[1] if len(sys.argv) > 1 else "serve"

    if mode == "test":
        print("\n=== DRY RUN (scoring engine) ===\n")
        result = dry_run_sample()
        for k, v in result.items():
            print(f"  {k}: {v}")
        print(f"\n  → Decision: {result['decision']}")
        print("\n✓ Scoring engine works.")

    elif mode == "simulate":
        print("\n=== SIMULATED CONVERSATION ===\n")
        turns = simulate_conversation()
        for t in turns:
            print(f"\n[Turn {t['turn']}]")
            print(f"  User:    {t['user']}")
            print(f"  Agent:   {t['agent'][:120]}")
            print(f"  Score:   {t['score']:.1f} → {t['decision']} ({t['stage']})")
        print("\n✓ LangGraph conversation engine works.")

    elif mode == "serve":
        from voice_agent.telephony.websocket_server import start_server

        logger.info("Starting AI Sales Call Agent server...")
        start_server(host=WS_HOST, port=WS_PORT)
        logger.info("WebSocket media stream server running on %s:%d", WS_HOST, WS_PORT)

        # Keep alive
        def _shutdown(sig, frame):
            logger.info("Shutting down...")
            sys.exit(0)

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        try:
            signal.pause()
        except AttributeError:
            # Windows — just sleep
            import time
            while True:
                time.sleep(1)

    else:
        print(f"Usage: python main.py [serve|test|simulate]")
        print(f"  serve    — Start the WebSocket server for live calls")
        print(f"  test     — Test the scoring engine with sample data")
        print(f"  simulate — Simulate a full conversation through LangGraph")


if __name__ == "__main__":
    main()
