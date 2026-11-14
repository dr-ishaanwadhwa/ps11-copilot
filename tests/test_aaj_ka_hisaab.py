"""Tests for Milestone 2: Conversational Hindi Audio Q&A ('Aaj Ka Hisaab') and Ledger Grounding."""
import pytest
from unittest.mock import MagicMock, patch

from copilot.answers import Copilot
from copilot.boundary import keyword_route, is_known_fact_question, route
from copilot.load import load_pack
from copilot.vault import VaultDB


@pytest.fixture(scope="module")
def seeded_vault(pack):
    v = VaultDB(in_memory=True)
    v.seed_from_pack(pack, pin="0000")
    return v


@pytest.fixture(scope="module")
def deep_copilot(pack, seeded_vault):
    return Copilot(pack, vault=seeded_vault)


def test_boundary_trade_credit_not_loan():
    """Verify that trade credit (उधारी / udhaari) queries do not trip LOAN intent."""
    r1 = keyword_route("30 महीने से पुरानी उधारी कौन सी है?")
    assert r1.intent != "LOAN"
    assert is_known_fact_question("30 महीने से पुरानी उधारी कौन सी है?") is True

    r2 = keyword_route("मुझ पर सबसे ज्यादा उधारी किसकी है?")
    assert r2.intent != "LOAN"

    r3 = keyword_route("बाजार उधारी का क्या हिसाब है?")
    assert r3.intent != "LOAN"

    # Actual bank loans should still trip LOAN
    r_loan = keyword_route("Should I take a bank loan to cover this month?")
    assert r_loan.intent == "LOAN"

    r_loan_hi = keyword_route("क्या मुझे बैंक से लोन या कर्ज़ लेना चाहिए?")
    assert r_loan_hi.intent == "LOAN"


def test_is_known_fact_question_hindi_stems():
    """Verify that Hindi and Hinglish factual query stems are recognized."""
    hindi_queries = [
        "आज का हिसाब क्या है?",
        "aaj ka hisaab batao",
        "मुझ पर सबसे ज्यादा बकाया किसका है?",
        "सैलरी दे सकते हैं क्या?",
        "कैश रनवे कितने दिन का है?",
        "क्रेडिट लिमिट कितनी बची है?",
        "30 महीने से पुरानी उधारी",
        "section 18 limitation alert",
    ]
    for q in hindi_queries:
        assert is_known_fact_question(q) is True, f"Failed to match stem in: {q}"


def test_aaj_ka_hisaab_handler(deep_copilot):
    """Verify aaj_ka_hisaab returns exact ledger-grounded metrics for SME-1."""
    ans = deep_copilot.aaj_ka_hisaab("SME-1")
    assert ans.intent == "FACT"
    assert "आज का हिसाब" in ans.text

    # SME-1 exact ground-truth values
    assert ans.numbers["bank_balance"] == pytest.approx(1238950.15, rel=1e-3)
    assert ans.numbers["credit_limit"] == 2500000.0
    assert ans.numbers["headroom"] == pytest.approx(3738950.15, rel=1e-3)
    assert ans.numbers["galla_cash"] == 420000.0
    assert ans.numbers["runway_days"] == 21
    assert ans.numbers["runway_inr"] == pytest.approx(784974.15, rel=1e-3)
    assert ans.numbers["can_pay_salaries"] is True
    assert ans.numbers["section_18_count"] == 1
    assert "Matoshree Supermarket" in ans.numbers["section_18_parties"]
    assert ans.numbers["section_18_amount"] == 114000.0


def test_cash_runway_handler(deep_copilot):
    """Verify cash_runway handler computes days, INR buffer, and daily burn."""
    ans = deep_copilot.cash_runway("SME-1")
    assert ans.intent == "FACT"
    assert "runway buffer" in ans.text.lower()
    assert ans.numbers["runway_days"] == 21
    assert ans.numbers["runway_inr"] == pytest.approx(784974.15, rel=1e-3)
    assert ans.numbers["daily_burn"] > 0
    assert ans.numbers["commitments"] > 0


def test_credit_headroom_handler(deep_copilot):
    """Verify credit_headroom handler returns limit, drawn, and available liquidity."""
    ans = deep_copilot.credit_headroom("SME-1")
    assert ans.intent == "FACT"
    assert ans.numbers["credit_limit"] == 2500000.0
    assert ans.numbers["closing_balance"] == pytest.approx(1238950.15, rel=1e-3)
    assert ans.numbers["cc_drawn"] == 0.0
    assert ans.numbers["headroom"] == pytest.approx(3738950.15, rel=1e-3)


def test_section_18_debts_handler(deep_copilot):
    """Verify section_18_debts flags 30-month khata cliff for SME-1."""
    ans = deep_copilot.section_18_debts("SME-1")
    assert ans.intent == "FACT"
    assert ans.numbers["critical_count"] == 1
    assert "Matoshree Supermarket" in ans.numbers["parties"]
    assert ans.numbers["critical_amount"] == 114000.0
    assert "Section 18" in ans.text
    assert "WhatsApp" in ans.text


def test_section_18_debts_clean_sme2(deep_copilot):
    """Verify SME-2 has 0 Section 18 debts."""
    ans = deep_copilot.section_18_debts("SME-2")
    assert ans.intent == "FACT"
    assert ans.numbers["critical_count"] == 0
    assert "No open receivables currently exceed" in ans.text


def test_vernacular_ask_routing(deep_copilot):
    """Verify Copilot.ask routes vernacular Hindi and Hinglish queries deterministically."""
    # 1. Aaj ka hisaab
    a1 = deep_copilot.ask("SME-1", "आज का हिसाब")
    assert a1.intent == "FACT"
    assert a1.numbers["runway_days"] == 21

    a1_hinglish = deep_copilot.ask("SME-1", "aaj ka hisaab")
    assert a1_hinglish.intent == "FACT"
    assert a1_hinglish.numbers["runway_days"] == 21

    # 2. Top debtor
    a2 = deep_copilot.ask("SME-1", "मुझ पर सबसे ज्यादा बकाया किसका है?")
    assert a2.intent == "FACT"
    assert a2.numbers["customer"] == "Laxmi Super Mart, Bibwewadi"

    # 3. Payroll
    a3 = deep_copilot.ask("SME-1", "क्या मैं 1 अक्टूबर को सैलरी दे सकता हूँ?")
    assert a3.intent == "FACT"
    assert a3.numbers["yes"] is True

    # 4. Runway
    a4 = deep_copilot.ask("SME-1", "कैश रनवे कितने दिन का है?")
    assert a4.intent == "FACT"
    assert a4.numbers["runway_days"] == 21

    # 5. Headroom
    a5 = deep_copilot.ask("SME-1", "क्रेडिट लिमिट कितनी बची है?")
    assert a5.intent == "FACT"
    assert a5.numbers["headroom"] == pytest.approx(3738950.15, rel=1e-3)

    # 6. Section 18
    a6 = deep_copilot.ask("SME-1", "30 महीने से पुरानी उधारी कौन सी है?")
    assert a6.intent == "FACT"
    assert a6.numbers["critical_count"] == 1
    assert "Matoshree Supermarket" in a6.numbers["parties"]


def test_ai_client_antihallucination_prompt():
    """Verify AIClient.generate_grounded_answer system prompt enforces anti-hallucination constraint."""
    from copilot.ai_client import AIClient
    client = AIClient()

    captured_payloads = []
    def fake_post(url, headers=None, json=None, timeout=None):
        captured_payloads.append(json)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Ledger-grounded answer"}}]
        }
        return mock_resp

    with patch.dict("os.environ", {"MISTRAL_API_KEY": "test-key"}):
        with patch("copilot.ai_client.requests.post", side_effect=fake_post):
            res = client.generate_grounded_answer(
                "Shree Ganesh Enterprises",
                "Who owes me?",
                "- Verified balance: ₹12,38,950",
            )
            assert res == "Ledger-grounded answer"
            assert len(captured_payloads) == 1
            sys_msg = captured_payloads[0]["messages"][0]["content"]
            assert "DO NOT invent or hallucinate customer names" in sys_msg
            assert "Zero unmasked informal records" in sys_msg
