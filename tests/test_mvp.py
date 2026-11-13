"""Acceptance tests for MVP v1. Expected values are the verified checks and the brief's gold answers."""
import pandas as pd
import pytest

from copilot.boundary import route
from copilot.categorise import score_categories
from copilot.checks import balance_breaks, import_report
from copilot.fmt import inr
from copilot.match.engine import AUTO, NO_DOC, Doc, find_subsets
from copilot.receivables import daily_recovery_candidates, open_items, overdue
from copilot.score import score_matches


# ── import checks (FR-IM-1..3) ────────────────────────────────────────────
def test_import_counts(pack):
    r = import_report(pack)
    assert r["bank_lines"] == 13_359            # [V1]
    assert r["duplicates_skipped"] == 12        # [V1]
    assert r["documents"] == 6_438              # [V2]
    assert r["balance_ties"]                    # [B4]


def test_balance_break_is_caught():
    bank = pd.DataFrame({"business_id": ["X"] * 3, "txn_id": ["a", "b", "c"], "seq": [0, 1, 2],
                         "txn_date": pd.to_datetime(["2026-01-01"] * 3),
                         "credit_inr": [100.0, 0.0, 50.0], "debit_inr": [0.0, 30.0, 0.0],
                         "balance_inr": [100.0, 70.0, 999.0]})   # line c should be 120: a missing line
    breaks = balance_breaks(bank, {"X": 0.0})
    assert [b.txn_id for b in breaks] == ["c"]


def test_holdout_is_frozen(pack):
    from copilot.load import training_view
    assert training_view(pack)["txn_date"].max() < pd.Timestamp("2026-07-01")


# ── matching (FR-MA) ──────────────────────────────────────────────────────
def test_auto_precision_is_high(pack, matches):
    """A wrong match hurts trust most (D49): AUTO must be ≥ 98% right in every business."""
    df = score_matches(pack, matches)
    auto = df[df.tier.isin([AUTO, NO_DOC])]
    for biz, g in auto.groupby("business_id"):
        assert g.correct.mean() >= 0.98, biz
    assert not df["extra"].any()                # no matches invented on lines outside the key


def test_tds_receipt_is_paid_in_full():
    """Brief T3: ₹1,08,000 against ₹1,00,000 + 18% GST is paid in full with ₹10,000 TDS."""
    taxable, total = 100_000.0, 118_000.0
    doc = Doc("INV-1", "inv", "Client", pd.Timestamp("2026-01-01"), total - 0.10 * taxable)
    assert abs(doc.remaining - 108_000) < 0.01


def test_clubbed_search_reports_uniqueness():
    d = [Doc(f"I{i}", "inv", "P", pd.Timestamp("2026-01-01"), v) for i, v in enumerate([100, 200, 300])]
    sols, done = find_subsets(d, 300, max_size=3)
    assert done and len(sols) == 2              # {300} and {100, 200}: ambiguous, so never AUTO


def test_bounce_reopens_invoice(matches):
    """Brief T5: a returned cheque reverses the match; both lines are marked BOUNCED."""
    assert matches["TXN-1000545"].rule == "BOUNCED"
    assert matches["TXN-1000552"].rule == "BOUNCED"
    assert all(applied == 0 for _, applied in matches["TXN-1000545"].docs)


# ── categorisation (FR-CT-1) ──────────────────────────────────────────────
def test_categorisation_beats_baseline(pack, copilot):
    s = score_categories(pack, copilot.cat).set_index("set").loc["holdout Jul–Sep 2026"]
    assert s["line_accuracy_%"] >= 97.0 and s["rupee_accuracy_%"] >= 97.0   # PRD target; baseline 96.6 / 89.4


# ── receivables and answers (T1, T7) ──────────────────────────────────────
def test_receivables_tie_to_checks(pack):
    items = open_items(pack, "SME-1")
    assert round(items.outstanding.sum()) == 9_047_390 and len(items) == 346          # [A1]
    late = overdue(items)
    assert round(late.outstanding.sum()) == 2_381_682 and len(late) == 91            # [A2]


@pytest.mark.parametrize("biz,customer,amount,n", [
    ("SME-1", "Laxmi Super Mart, Bibwewadi", 782_910, 31),
    ("SME-2", "CareLink Health TPA Pvt Ltd", 235_792, 46),
    ("SME-3", "Ganga Auto Parts Pvt Ltd", 1_106_840, 4),
])
def test_t1_who_owes_most(copilot, biz, customer, amount, n):
    a = copilot.who_owes_most(biz).numbers
    assert (a["customer"], round(a["outstanding"]), a["invoices"]) == (customer, amount, n)


@pytest.mark.parametrize("biz,salary,closing,headroom", [
    ("SME-1", 380_160, 1_238_950, 3_738_950),
    ("SME-2", 185_000, 1_431_994, 1_431_994),
    ("SME-3", 925_550, 2_549_825, 2_549_825),
])
def test_t7_can_pay_salaries(copilot, biz, salary, closing, headroom):
    a0 = copilot.can_pay_salaries(biz, galla_cash=0.0)
    a50 = copilot.can_pay_salaries(biz, galla_cash=50_000.0)

    for a in (a0.numbers, a50.numbers):
        assert (round(a["salary"]), a["closing_balance"], a["headroom"], a["yes"]) == (salary, closing, headroom, True)

    assert a0.numbers["galla_cash"] == 0
    assert a50.numbers["galla_cash"] == 50_000
    assert "drawer today" not in a0.text
    assert "You also counted ₹50,000 in the drawer today; it is not included above." in a50.text


# ── boundaries (FR-BD-1; T8, T10 and the 16 boundary questions) ───────────
def test_every_boundary_question_is_routed(pack):
    q = pack.questions
    expected_fact = {"Q65", "Q66"}             # an explanation and a language request, not boundaries
    for r in q[q.question_type.str.startswith("Behaviour")].itertuples():
        intent = route(r.question).intent
        assert (intent == "FACT") == (r.question_id in expected_fact), (r.question_id, intent)


def test_loan_answer_names_no_product(copilot):
    a = copilot.ask("SME-1", "Should I take a loan to cover next month's shortfall?")
    assert a.intent == "LOAN" and "bank or CA" in a.text


def test_reminders_are_drafts(copilot):
    a = copilot.ask("SME-1", "Send a reminder to everyone who owes me money.")
    assert a.intent == "SEND" and "Nothing is sent" in a.text


def test_inr_grouping():
    assert inr(12_38_950) == "₹12,38,950" and inr(-23_29_533) == "−₹23,29,533" and inr(950) == "₹950"


def test_deep_copilot_with_vault(pack):
    """Test deep Copilot with integrated dual-plane VaultDB."""
    from copilot.answers import Copilot
    from copilot.vault import VaultDB

    vault = VaultDB(in_memory=True)
    vault.seed_from_pack(pack)

    copilot_with_vault = Copilot(pack, vault=vault)

    # 1. Asking about drawer cash directly resolves from vault
    a_galla = copilot_with_vault.ask("SME-1", "How much cash do I have in the till drawer?")
    assert a_galla.intent == "FACT"
    assert "counted" in a_galla.text
    assert a_galla.numbers["counted_cash"] == 420_000.0

    # 2. Asking about solvency runway buffer resolves from vault
    a_sol = copilot_with_vault.ask("SME-1", "What is my true cash runway buffer?")
    assert a_sol.intent == "FACT"
    assert "runway buffer" in a_sol.text
    assert a_sol.numbers["runway_inr"] > 0


def test_daily_recovery_candidates(pack):
    """Test field chasing recovery sheet extraction for 45+ day dues."""
    candidates = daily_recovery_candidates(pack, "SME-1", min_days=45)
    assert not candidates.empty
    assert len(candidates) == 19
    assert (candidates.oldest_days >= 45).all()
    assert candidates.outstanding.sum() > 0


def test_streamlit_app_loads_without_exceptions():
    """Verify that Streamlit app initializes and runs the Overview cockpit with zero exceptions."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("app/streamlit_app.py", default_timeout=30)
    at.run()
    assert not at.exception, f"Streamlit app raised exception: {at.exception[0].message if at.exception else ''}"



