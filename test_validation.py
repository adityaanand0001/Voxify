"""Validation test suite for AI Sales Call Agent."""

import sys
sys.path.insert(0, "A:/Voxify")

from voice_agent.state.schema import CallState, Timeline, Authority, Sentiment, Decision
from voice_agent.scoring.scoring import (
    compute_score, decide, update_state_score,
    extract_budget_from_text, extract_timeline_from_text, extract_authority_from_text,
    apply_objection_penalty,
)

passed = 0
failed = 0


def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  [PASS] {name}: {actual}")
        passed += 1
    else:
        print(f"  [FAIL] {name}: got {actual}, expected {expected}")
        failed += 1


# ── Scoring ──────────────────────────────────────────────────

print("=== Scoring Engine ===")

s1 = CallState(budget=60000, timeline=Timeline.IMMEDIATE, authority=Authority.DECISION_MAKER,
               need_level=0.9, engagement=0.8, sentiment=Sentiment.POSITIVE)
update_state_score(s1)
check("Hot lead (60k, immediate, decision maker)", s1.decision.value, "BOOK_MEETING")
check("Hot lead score >= 80", s1.lead_score >= 80, True)

s2 = CallState(budget=25000, timeline=Timeline.ONE_TO_THREE_MONTHS, authority=Authority.INFLUENCER,
               need_level=0.6, engagement=0.5, sentiment=Sentiment.NEUTRAL)
update_state_score(s2)
check("Warm lead decision", s2.decision.value, "STRONG_FOLLOWUP")

s3 = CallState(budget=None, timeline=Timeline.SIX_PLUS_MONTHS, authority=Authority.RESEARCHER,
               need_level=0.1, engagement=0.2, sentiment=Sentiment.NEGATIVE)
update_state_score(s3)
check("Cold lead decision", s3.decision.value, "DROP")

# ── Budget extraction ───────────────────────────────────────

print("\n=== Budget Extraction ===")

bt = extract_budget_from_text("We have a budget of 50k for this")
check("50k budget", bt, 50000)

bt2 = extract_budget_from_text("Around 25 thousand dollars is what we have")
check("25 thousand", bt2, 25000)

bt3 = extract_budget_from_text("Budget is around $75,000")
check("$75,000", bt3, 75000)

bt4 = extract_budget_from_text("No budget mentioned here")
check("No budget", bt4, None)

# ── Timeline extraction ─────────────────────────────────────

print("\n=== Timeline Extraction ===")

check("ASAP", extract_timeline_from_text("we need this ASAP"), Timeline.IMMEDIATE)
check("next month", extract_timeline_from_text("probably next month"), Timeline.ONE_TO_THREE_MONTHS)
check("no rush", extract_timeline_from_text("no rush at all"), Timeline.SIX_PLUS_MONTHS)
check("within a month", extract_timeline_from_text("we want it within a month"), Timeline.ONE_TO_THREE_MONTHS)

# ── Authority extraction ────────────────────────────────────

print("\n=== Authority Extraction ===")

check("I decide", extract_authority_from_text("I decide on these things"), Authority.DECISION_MAKER)
check("CEO", extract_authority_from_text("I am the CEO here"), Authority.DECISION_MAKER)
check("run it by", extract_authority_from_text("I will run it by my boss"), Authority.INFLUENCER)
check("just browsing", extract_authority_from_text("just browsing for now"), Authority.RESEARCHER)
check("unknown", extract_authority_from_text("hello how are you"), Authority.UNKNOWN)

# ── Objection penalty ───────────────────────────────────────

print("\n=== Objection Handling ===")

s_obj = CallState(budget=60000, timeline=Timeline.IMMEDIATE, authority=Authority.DECISION_MAKER,
                  need_level=0.9, engagement=0.8, sentiment=Sentiment.POSITIVE)
update_state_score(s_obj)
original_score = s_obj.lead_score
apply_objection_penalty(s_obj, "not_interested")
check("Score drops after objection", s_obj.lead_score < original_score, True)
check("Objection recorded", s_obj.objection, "not_interested")

# ── Decision thresholds ─────────────────────────────────────

print("\n=== Decision Thresholds ===")

thresholds = [(85, "BOOK_MEETING"), (70, "STRONG_FOLLOWUP"), (50, "NURTURE"), (25, "DROP")]
for score_val, expected in thresholds:
    s = CallState(lead_score=score_val)
    check(f"Score {score_val}", decide(s).value, expected)

# ── Graph compilation ───────────────────────────────────────

print("\n=== LangGraph Compilation ===")

try:
    from voice_agent.graph.graph_builder import build_call_graph
    graph = build_call_graph()
    nodes = list(graph.nodes.keys())
    check("Graph compiles", len(nodes) >= 7, True)
    check("Has listener node", "listener" in nodes, True)
    check("Has response node", "response" in nodes, True)
    check("Has scoring node", "scoring" in nodes, True)
except Exception as e:
    print(f"  [FAIL] Graph compilation: {e}")
    failed += 1

# ── Summary ─────────────────────────────────────────────────

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print(f"{failed} TESTS FAILED")
    sys.exit(1)
