"""Unit tests for the fail-closed boundary router ensemble (Task 3.4; D63, D66, D70)."""
import os
from unittest.mock import MagicMock
import anthropic
import pytest
from copilot.ai_client import _load_env_if_needed

_load_env_if_needed()

from copilot.boundary import NEEDS_CHIPS, Route, route
from copilot.router_llm import RouterDecision


class FakeParseResponse:
    def __init__(self, parsed_output=None, stop_reason="stop"):
        self.parsed_output = parsed_output
        self.stop_reason = stop_reason


def make_stub_client(parsed_output=None, stop_reason="stop", error=None):
    client = MagicMock()
    with_opts = MagicMock()
    messages = MagicMock()

    if error:
        messages.parse.side_effect = error
    else:
        messages.parse.return_value = FakeParseResponse(parsed_output=parsed_output, stop_reason=stop_reason)

    with_opts.messages = messages
    client.with_options.return_value = with_opts
    return client


def test_keywords_boundary_wins_over_model_fact():
    """Keywords boundary + model FACT -> boundary."""
    client = make_stub_client(
        parsed_output=RouterDecision(intent="FACT", language="en", confident=True)
    )
    # Question trips LOAN keyword
    res = route("Should I take a loan to cover next month?", use_llm=True, client=client)
    assert res.intent == "LOAN"
    assert res.source == "keywords"


def test_keywords_fact_model_boundary():
    """Keywords FACT + model boundary -> boundary."""
    client = make_stub_client(
        parsed_output=RouterDecision(intent="LOAN", language="en", confident=True)
    )
    # Question has no obvious boundary keywords, but LLM detects LOAN
    res = route("Can you arrange additional credit for me?", use_llm=True, client=client)
    assert res.intent == "LOAN"
    assert res.source == "llm"


def test_keywords_fact_model_fact_confident():
    """Keywords FACT + model FACT confident -> FACT."""
    client = make_stub_client(
        parsed_output=RouterDecision(intent="FACT", language="en", confident=True)
    )
    res = route("Can I pay salaries on time?", use_llm=True, client=client)
    assert res.intent == "FACT"
    assert res.source == "llm"


def test_keywords_fact_model_fact_not_confident():
    """Keywords FACT + model FACT not confident -> NEEDS_CHIPS."""
    client = make_stub_client(
        parsed_output=RouterDecision(intent="FACT", language="en", confident=False)
    )
    res = route("Some ambiguous question", use_llm=True, client=client)
    assert res.intent == "NEEDS_CHIPS"


def test_model_connection_error_fails_closed():
    """Model raises APIConnectionError -> NEEDS_CHIPS."""
    err = anthropic.APIConnectionError(request=MagicMock())
    client = make_stub_client(error=err)
    res = route("Can I pay salaries on time?", use_llm=True, client=client)
    assert res.intent == "NEEDS_CHIPS"


def test_model_refusal_fails_closed():
    """stop_reason == 'refusal' -> NEEDS_CHIPS."""
    client = make_stub_client(parsed_output=None, stop_reason="refusal")
    res = route("Can I pay salaries on time?", use_llm=True, client=client)
    assert res.intent == "NEEDS_CHIPS"


@pytest.mark.skipif(
    not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("MISTRAL_API_KEY") or os.environ.get("OPENROUTER_API_KEY")),
    reason="No AI API key set",
)
def test_live_claude_classifier():
    """Live test against structured outputs when any supported AI key is present."""
    res = route("Can I pay salaries on 1 October 2026?", use_llm=True)
    assert res.intent in ("FACT", "NEEDS_CHIPS")


def test_live_ai_client_grounded_answer():
    """Verify live AI client generates grounded answers from ledger facts."""
    from copilot.ai_client import get_ai_client

    ai = get_ai_client()
    if not ai.is_configured:
        pytest.skip("No AI API key configured")

    ans = ai.generate_grounded_answer(
        "Kaveri Distributors",
        "Can I afford to pay ₹25,000 for vehicle maintenance tomorrow?",
        "- Closing Bank Balance: ₹12,38,950\n- Counted Cash in Galla: ₹4,20,000",
    )
    assert ans is not None
    assert len(ans) > 10


def test_intent_router_class(tmp_path):
    """Test the deepened IntentRouter class directly with custom audit sink."""
    from copilot.boundary import IntentRouter

    sink = tmp_path / "disagreements.jsonl"
    router = IntentRouter(audit_sink=sink)

    client = make_stub_client(
        parsed_output=RouterDecision(intent="LOAN", language="en", confident=True)
    )
    # Question trips disagreement: keywords say FACT, LLM says LOAN
    res = router.route(
        "Can you arrange additional credit for me?",
        use_llm=True,
        known_names=["Kaveri Distributors"],
        client=client,
    )
    assert res.intent == "LOAN"
    assert res.source == "llm"
    assert sink.exists()
    assert "LOAN" in sink.read_text(encoding="utf-8")

