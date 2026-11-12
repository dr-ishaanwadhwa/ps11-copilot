"""Safety and compliance tests for public builds (D68)."""
from pathlib import Path

from copilot.vault import PARTIAL_VIEW_NOTICE


def test_partial_view_notice_text():
    assert PARTIAL_VIEW_NOTICE == "Formal books only. The owner's cash memo is not included in this view."


def test_no_concealment_language():
    forbidden = [
        "presentation mode",
        "tax inspection",
        "audit trace",
        "golden pillars",
        "withstand",
        "readiness tier",
        "headroom before",
    ]
    repo_root = Path(__file__).resolve().parent.parent
    for folder in ["app", "src"]:
        for py_file in (repo_root / folder).rglob("*.py"):
            text = py_file.read_text(encoding="utf-8").lower()
            for phrase in forbidden:
                assert phrase not in text, f"Found forbidden phrase '{phrase}' in {py_file}"


def test_deposit_facts_have_no_countdown():
    from copilot.vault import cash_deposit_reporting_facts

    ytd_values = [0.0, 990_000.0, 4_900_000.0, 6_000_000.0]
    for ytd in ytd_values:
        res = cash_deposit_reporting_facts(ytd, account_type="CURRENT", has_pan=True)
        assert res.status == "INFO"
        assert res.citation == "Income-tax Rules 2026, Rule 237 (to be confirmed by a CA)"
        msg = res.message.lower()
        for forbidden in ["headroom", "remaining", "before", "%"]:
            assert forbidden not in msg, f"Found '{forbidden}' in message: {res.message}"

