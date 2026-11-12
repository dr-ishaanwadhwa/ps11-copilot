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
