"""Unit tests for Matcher under Decision 60 (Tasks 4.1, 4.2, 4.3)."""
import tempfile
from pathlib import Path
from copilot import config
from copilot.match.audit import AuditLedger, select_audit_sample
from copilot.match.engine import AUTO, SUGGEST, Matcher, match_all


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
