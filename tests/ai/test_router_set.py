"""The router test set (AI-ML-AGENTS-PLAN.md §4.1): integrity checks, plus the week-1 gate.

The integrity tests must always pass. The gate tests describe the target for the LLM router (D66):
the keyword router in `boundary.py` doesn't meet them yet, so they're marked xfail(strict=True).
When the new router passes, pytest reports XPASS as a failure, which forces removing the marker.
"""
from collections import Counter

import pytest

from copilot.boundary import route
from copilot.evals.router_cases import BOUNDARY_INTENTS, CASES, INTENTS, PACK_EXPECTED

ROUTER_NOT_BUILT = pytest.mark.xfail(strict=True, reason="LLM intent router is week-1 work (D66); keyword router fails")


def _ok(case, intent: str) -> bool:
    return intent == case.expect or intent in case.also_ok


def _pack_cases(pack):
    q = pack.questions.set_index("question_id")
    boundary = [(qid, q.loc[qid, "question"], want) for qid, want in PACK_EXPECTED.items()]
    facts = [(qid, r.question, "FACT") for qid, r in q.iterrows()
             if qid not in PACK_EXPECTED and not str(r.question_type).startswith("Behaviour")]
    return boundary, facts


# ── integrity: the set itself is sound ────────────────────────────────────────────────────────
def test_every_label_is_a_known_intent():
    assert {c.expect for c in CASES} <= INTENTS
    assert all(c.also_ok <= INTENTS for c in CASES)
    assert set(PACK_EXPECTED.values()) <= INTENTS


def test_no_duplicate_questions():
    dupes = [t for t, n in Counter(c.text.strip().lower() for c in CASES).items() if n > 1]
    assert not dupes, dupes


def test_coverage_per_boundary_type_and_language():
    """Plan §4.1: at least 10 English paraphrases per boundary type, and Hindi for every type."""
    by = Counter((c.expect, c.lang) for c in CASES if c.source == "paraphrase")
    for intent in BOUNDARY_INTENTS:
        assert by[(intent, "en")] >= 10, (intent, "en", by[(intent, "en")])
        assert by[(intent, "hi")] + by[(intent, "hinglish")] >= 5, (intent, "hi")


def test_wrong_refusal_checks_exist():
    near = [c for c in CASES if c.source == "near_miss"]
    assert len(near) >= 30 and {c.lang for c in near} == {"en", "hi", "hinglish"}


def test_pack_questions_are_referenced_by_id_only(pack):
    """Pack questions come from the local pack at test time; none of the 67 is copied into this set."""
    q = pack.questions
    assert set(q[q.question_type.str.startswith("Behaviour")].question_id) == set(PACK_EXPECTED)
    committed = {c.text.strip().lower() for c in CASES}
    leaked = [r.question_id for r in q.itertuples() if r.question.strip().lower() in committed]
    assert not leaked, leaked


# ── the gate (D66) ────────────────────────────────────────────────────────────────────────────
@ROUTER_NOT_BUILT
def test_gate_every_boundary_case_routes_to_its_intent(pack):
    boundary, _ = _pack_cases(pack)
    misses = [(c.text, c.expect, route(c.text).intent) for c in CASES
              if c.expect in BOUNDARY_INTENTS and not _ok(c, route(c.text).intent)]
    misses += [(qid, want, route(text).intent) for qid, text, want in boundary if route(text).intent != want]
    assert not misses, f"{len(misses)} boundary misses, e.g. {misses[:5]}"


@ROUTER_NOT_BUILT
def test_gate_fact_questions_are_not_refused(pack):
    _, facts = _pack_cases(pack)
    fact_cases = [c for c in CASES if c.expect == "FACT"]
    wrong = [c.text for c in fact_cases if not _ok(c, route(c.text).intent)]
    wrong += [qid for qid, text, _ in facts if route(text).intent != "FACT"]
    total = len(fact_cases) + len(facts)
    assert len(wrong) / total <= 0.02, f"{len(wrong)} of {total} FACT questions refused, e.g. {wrong[:5]}"
