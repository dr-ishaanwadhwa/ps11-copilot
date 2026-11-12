"""Unit tests for Matcher under Decision 60 (Tasks 4.1, 4.2, 4.3)."""
import tempfile
from pathlib import Path
from types import SimpleNamespace
import pandas as pd
from copilot import config
from copilot.match.audit import AuditLedger, select_audit_sample
from copilot.match.engine import AUTO, SUGGEST, Matcher, match_all
from copilot.vault.models import Collection


def test_handle_memory_learns_only_from_confirm_payer(pack, monkeypatch):
    """Test 4.2: After match_all, handle_memory contains only entries added via confirm_payer."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        monkeypatch.setattr(config, "STATE_DIR", Path(tmp_dir))

        mt = Matcher(pack)
        assert len(mt.handle_memory) == 0

        # Run match_all with this matcher
        for r in pack.bank.sort_values(["txn_date", "seq"]).itertuples():
            mt.match(r)

        # Assert no handles were auto-learned from AUTO matches
        assert len(mt.handle_memory) == 0, f"Leaked auto-learned handles: {mt.handle_memory}"

        # Now confirm a handle
        mt.confirm_payer("test@upi", "Test Customer")
        assert mt.handle_memory["test@upi"] == "Test Customer"

        # A new matcher loads it from disk
        mt2 = Matcher(pack)
        assert mt2.handle_memory.get("test@upi") == "Test Customer"


def test_audit_suspension_and_requalification(pack, monkeypatch):
    """Test 4.3: A seeded wrong audit result suspends its class; matches become SUGGEST; requalify restores AUTO."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_dir = Path(tmp_dir)
        monkeypatch.setattr(config, "STATE_DIR", state_dir)

        ledger = AuditLedger(state_dir)
        rule_class = ("SME-1", "EXACT")
        assert rule_class not in ledger.suspended_classes()

        # Seed a wrong audit result
        ledger.record("TXN-1000001", rule_class, correct=False, reviewer="lead")
        assert rule_class in ledger.suspended_classes()

        # Matcher with this ledger demotes that class to SUGGEST
        mt = Matcher(pack, audit_ledger=ledger)
        for r in pack.bank[pack.bank.business_id == "SME-1"].itertuples():
            m = mt.match(r)
            if m and m.rule == "EXACT":
                assert m.tier == SUGGEST
                assert "rule suspended after an audit miss (D60)" in m.note
                break

        # Requalify the rule class
        ledger.requalify(rule_class)
        assert rule_class not in ledger.suspended_classes()

        # Matcher restores AUTO
        mt2 = Matcher(pack, audit_ledger=ledger)
        restored = False
        for r in pack.bank[pack.bank.business_id == "SME-1"].itertuples():
            m = mt2.match(r)
            if m and m.rule == "EXACT" and abs(r.amount) < 100_000:
                assert m.tier == AUTO
                restored = True
                break
        assert restored, "Expected an EXACT match to be restored to AUTO"


def test_select_audit_sample(pack):
    """Test 4.3: select_audit_sample is deterministic and picks at least 1 per class."""
    matches = match_all(pack)
    week = "2026-W30"
    sample1 = select_audit_sample(matches, pack.bank, week, rate=0.02)
    sample2 = select_audit_sample(matches, pack.bank, week, rate=0.02)
    assert sample1 == sample2
    assert len(sample1) > 0


def test_cash_collections_feed_deposit_matching(pack):
    """Test 5.3 (D55): 3 synthetic collection records feed a cash deposit match as SUGGEST."""
    mt = Matcher(pack)

    # Pick 3 open invoices across distinct shops for SME-1
    invs = []
    for party, docs in mt.docs["SME-1"].items():
        for d in docs:
            if d.remaining > 0:
                invs.append(d)
                break
        if len(invs) == 3:
            break

    assert len(invs) == 3
    dep_amt = sum(d.remaining for d in invs)
    dep_date = max(d.date for d in invs) + pd.Timedelta(days=5)

    # Record 3 synthetic collections on the day prior to deposit
    for i, d in enumerate(invs):
        col = Collection(
            business_id="SME-1",
            date=dep_date - pd.Timedelta(days=1),
            shop=d.party,
            amount=d.remaining,
            salesman=f"Salesman {i + 1}",
        )
        mt.record_collection(col)

    # Synthetic bank cash deposit row
    row = SimpleNamespace(
        txn_id="TXN-TEST-DEPOSIT-COLL",
        business_id="SME-1",
        channel="CASH",
        amount=dep_amt,
        txn_date=dep_date,
        narration="CASH DEPOSIT BY SELF - CDM HADAPSAR",
        seq=1,
    )

    m = mt.match(row)
    assert m is not None
    # Must propose SUGGEST, never AUTO
    assert m.tier == SUGGEST
    assert m.rule == "CASH_DEPOSIT"
    # Matches the 3 shops' invoices
    matched_ids = {doc_id for doc_id, _ in m.docs}
    assert matched_ids == {d.id for d in invs}
