"""Unit tests for Matcher under Decision 60 (Tasks 4.1, 4.2)."""
import tempfile
from pathlib import Path
from copilot import config
from copilot.match.engine import Matcher, match_all


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
