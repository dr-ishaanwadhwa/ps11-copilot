"""Adversarial stress-testing harness for Requirement R2 (teamwork_challenger_2).

Empirically tests:
1. Deterministic Ledger State Grounding (Mathematical Certitude on SME-1 metrics)
2. Vernacular Variations & Transliteration Robustness
3. Customer 'उधारी' vs Bank Loan intent classification
4. Privacy Boundary & Cloud Leakage (Zero unmasked informal records leak)
5. Offline / Local-First Resilience (Deterministic handlers must function without LLM/network)
6. Section 18 False Refusal under LLM classifier
"""
import os
from unittest.mock import MagicMock, patch
import pytest

from copilot.answers import Copilot
from copilot.boundary import keyword_route, is_known_fact_question, route
from copilot.load import load_pack
from copilot.vault import VaultDB


@pytest.fixture(scope="module")
def pack():
    return load_pack()


@pytest.fixture(scope="module")
def seeded_vault(pack):
    v = VaultDB(in_memory=True)
    v.seed_from_pack(pack, pin="0000")
    return v


@pytest.fixture(scope="module")
def copilot_inst(pack, seeded_vault):
    return Copilot(pack, vault=seeded_vault)


# ============================================================================
# 1. MATHEMATICAL CERTITUDE ON DETERMINISTIC HANDLERS (SME-1)
# ============================================================================

def test_sme1_mathematical_certitude(copilot_inst):
    """Verify exact numerical grounding for SME-1 across all core financial metrics."""
    # 1. Aaj Ka Hisaab
    hisaab = copilot_inst.aaj_ka_hisaab("SME-1")
    assert hisaab.intent == "FACT"
    assert hisaab.numbers["bank_balance"] == pytest.approx(1238950.15, rel=1e-3)
    assert hisaab.numbers["credit_limit"] == 2500000.0
    assert hisaab.numbers["headroom"] == pytest.approx(3738950.15, rel=1e-3)
    assert hisaab.numbers["galla_cash"] == 420000.0
    assert hisaab.numbers["runway_days"] == 21
    assert hisaab.numbers["runway_inr"] == pytest.approx(784974.15, rel=1e-3)
    assert hisaab.numbers["can_pay_salaries"] is True
    assert hisaab.numbers["section_18_count"] == 1
    assert "Matoshree Supermarket" in hisaab.numbers["section_18_parties"]
    assert hisaab.numbers["section_18_amount"] == 114000.0

    # 2. Runway
    runway = copilot_inst.cash_runway("SME-1")
    assert runway.numbers["runway_days"] == 21
    assert runway.numbers["runway_inr"] == pytest.approx(784974.15, rel=1e-3)

    # 3. Headroom
    headroom = copilot_inst.credit_headroom("SME-1")
    assert headroom.numbers["headroom"] == pytest.approx(3738950.15, rel=1e-3)

    # 4. Section 18 Debts
    s18 = copilot_inst.section_18_debts("SME-1")
    assert s18.numbers["critical_count"] == 1
    assert s18.numbers["critical_amount"] == 114000.0
    assert "Matoshree Supermarket" in s18.numbers["parties"]

    # 5. Top Debtor (31 invoices, ₹7,82,910)
    top = copilot_inst.who_owes_most("SME-1")
    assert top.numbers["customer"] == "Laxmi Super Mart, Bibwewadi"
    assert top.numbers["outstanding"] == pytest.approx(782910.0, rel=1e-3)
    assert top.numbers["invoices"] == 31


# ============================================================================
# 2. ROUTER ROBUSTNESS: "उधारी" VS BANK LOAN CLASSIFICATION
# ============================================================================

def test_udhari_never_misclassified_as_loan():
    """Verify customer credit / udhari queries in Hindi and Hinglish route to FACT or non-LOAN."""
    udhari_queries = [
        "उधारी कितनी है?",
        "दुकान की उधारी बताओ",
        "मार्केट उधारी",
        "बाजार उधारी का क्या हिसाब है?",
        "purani udhari kaun si hai",
        "udhaari kitni hai",
        "udhari kitni baki hai",
        "ramesh ki udhari",
        "laxmi mart ki udhari kitni hai",
        "kaccha udhari ka hisaab",
        "30 महीने से पुरानी उधारी",
    ]
    for q in udhari_queries:
        r = keyword_route(q)
        assert r.intent != "LOAN", f"Query '{q}' was wrongly classified as LOAN!"


def test_bank_loan_queries_correctly_classified_as_loan():
    """Verify actual bank financing and borrowing queries are caught as LOAN."""
    loan_queries = [
        "क्या मुझे बैंक से लोन या कर्ज़ लेना चाहिए?",
        "Should I take a bank loan to cover this month?",
        "बैंक से कर्ज़ लेना है",
        "should I take an overdraft loan?",
        "nbfc se loan mil sakta hai kya?",
    ]
    for q in loan_queries:
        r = keyword_route(q)
        assert r.intent == "LOAN", f"Bank loan query '{q}' was NOT classified as LOAN!"


# ============================================================================
# 3. REMEDIATION VERIFICATION A: OFFLINE / RESILIENCE
# ============================================================================

def test_remediated_offline_copilot_ask_succeeds_with_fact(copilot_inst):
    """REMEDIATION VERIFICATION:
    When offline (no LLM API key / network down), Copilot.ask() evaluates
    deterministic queries locally on-device, succeeding with FACT and exact ledger metrics.
    """
    with patch.dict("os.environ", {"MISTRAL_API_KEY": "", "OPENROUTER_API_KEY": "", "ANTHROPIC_API_KEY": ""}, clear=True):
        ans = copilot_inst.ask("SME-1", "आज का हिसाब")
        assert ans.intent == "FACT"
        assert ans.numbers["runway_days"] == 21
        assert ans.numbers["credit_limit"] == 2500000.0


# ============================================================================
# 4. REMEDIATION VERIFICATION B: ZERO UNMASKED INFORMAL RECORD TRANSMISSION
# ============================================================================

def test_remediated_informal_party_never_leaks_unmasked_to_cloud(copilot_inst):
    """REMEDIATION VERIFICATION:
    Zero bytes of unmasked informal records leak to cloud endpoints (ADR-001).
    Deterministic queries are handled locally with 0 cloud payloads, and open-ended
    queries mask informal vault parties before invoking external LLMs.
    """
    captured_payloads = []

    def mock_post(url, *args, **kwargs):
        captured_payloads.append(kwargs.get("json", {}))
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"intent": "FACT", "language": "hi", "confident": true}'}}]
        }
        return mock_resp

    with patch.dict("os.environ", {"MISTRAL_API_KEY": "test-key"}):
        with patch("copilot.ai_client.requests.post", side_effect=mock_post):
            # 1. Deterministic query is evaluated locally with 0 network calls
            ans = copilot_inst.ask("SME-1", "Matoshree Supermarket ki purani udhari kitni hai?")
            assert ans.intent == "FACT"
            assert len(captured_payloads) == 0, "Deterministic query unexpectedly called cloud LLM!"

            # 2. Open-ended query transmits ONLY masked counterparty tokens
            copilot_inst.ask("SME-1", "Matoshree Supermarket ke bare mein batao")
            assert len(captured_payloads) >= 1
            for payload in captured_payloads:
                for msg in payload.get("messages", []):
                    content = msg.get("content", "")
                    assert "Matoshree Supermarket" not in content, (
                        f"Unmasked informal party leaked in payload: {content}"
                    )


# ============================================================================
# 5. REMEDIATION VERIFICATION C: SECTION 18 NOT MISROUTED TO TAX_ACTION
# ============================================================================

def test_remediated_section_18_limitation_alert_not_misrouted(copilot_inst):
    """REMEDIATION VERIFICATION:
    Section 18 Limitation Act inquiries regarding commercial debt aging are evaluated
    locally as FACT by section_18_debts() and never misrouted to TAX_ACTION.
    """
    def mock_post(url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"intent": "TAX_ACTION", "language": "en", "confident": true}'}}]
        }
        return mock_resp

    with patch.dict("os.environ", {"MISTRAL_API_KEY": "test-key"}):
        with patch("copilot.ai_client.requests.post", side_effect=mock_post):
            ans = copilot_inst.ask("SME-1", "section 18 limitation alert")
            assert ans.intent == "FACT"
            assert ans.numbers["critical_count"] == 1
            assert "Matoshree Supermarket" in ans.numbers["parties"]
            assert "Section 18" in ans.text


# ============================================================================
# 6. REMEDIATION VERIFICATION D: TRANSLITERATION STEM ROBUSTNESS
# ============================================================================

def test_remediated_aaj_ka_hisab_transliteration(copilot_inst):
    """Verify 'aaj ka hisab' (single 'a') triggers aaj_ka_hisaab deterministically."""
    ans = copilot_inst.ask("SME-1", "aaj ka hisab")
    assert ans.intent == "FACT"
    assert ans.numbers["runway_days"] == 21

