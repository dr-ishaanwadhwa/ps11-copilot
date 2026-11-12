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


def test_checklist_has_no_score():
    from copilot.vault import deposit_records_checklist

    res = deposit_records_checklist()
    assert set(res.keys()) == {"documents", "referral"}

    # No value contains a digit or %
    all_texts = res["documents"] + [res["referral"]]
    for text in all_texts:
        assert "%" not in text, f"Found '%' in checklist text: {text}"
        assert not any(ch.isdigit() for ch in text), f"Found digit in checklist text: {text}"


def test_public_mode_has_no_free_text():
    import ast

    repo_root = Path(__file__).resolve().parent.parent
    app_source = (repo_root / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    tree = ast.parse(app_source)

    # Find the with tab_ask block
    ask_block = None
    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            for item in node.items:
                if isinstance(item.context_expr, ast.Name) and item.context_expr.id == "tab_ask":
                    ask_block = node
                    break

    assert ask_block is not None, "Could not find with tab_ask block"

    class AskVisitor(ast.NodeVisitor):
        def __init__(self):
            self.in_if_not_public = False
            self.unguarded_input_calls = []

        def visit_If(self, node):
            old_val = self.in_if_not_public
            is_not_public = False
            if isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not):
                if isinstance(node.test.operand, ast.Name) and node.test.operand.id == "PUBLIC":
                    is_not_public = True

            if is_not_public:
                self.in_if_not_public = True
                for child in node.body:
                    self.visit(child)
                self.in_if_not_public = old_val
                for child in node.orelse:
                    self.visit(child)
            else:
                self.generic_visit(node)

        def visit_Call(self, node):
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("text_input", "chat_input"):
                if not self.in_if_not_public:
                    self.unguarded_input_calls.append(node)
            self.generic_visit(node)

    visitor = AskVisitor()
    for stmt in ask_block.body:
        visitor.visit(stmt)

    assert len(visitor.unguarded_input_calls) == 0, (
        f"Found text/chat input calls in Ask block not guarded by 'if not PUBLIC': {visitor.unguarded_input_calls}"
    )


def test_data_pack_is_bundled():
    from copilot import config

    assert config.DEFAULT_DATA_DIR.name == "data"
    for fname in [config.BANK_XLSX, config.DOCS_XLSX, config.EVAL_XLSX]:
        assert (config.DEFAULT_DATA_DIR / fname).exists(), f"Missing {fname} in data/"


def test_invented_seed_data_is_labeled_demo(pack):
    """Test 5.1: Invented seed data is labeled demo and uses fake phone numbers."""
    from copilot.vault import VaultDB

    vault = VaultDB()
    vault.seed_from_pack(pack)

    # SME-1 and SME-3 are demo seeds
    g1 = vault.get_latest_galla("SME-1")
    assert g1 is not None and g1.is_demo is True

    g3 = vault.get_latest_galla("SME-3")
    assert g3 is not None and g3.is_demo is True

    # SME-2 clinic cash bridge is from data pack
    g2 = vault.get_latest_galla("SME-2")
    assert g2 is not None and g2.is_demo is False

    # SME-1 khata accounts are demo with obviously fake phone numbers
    khata = vault.get_khata_summary("SME-1")["accounts"]
    assert len(khata) > 0
    for acc in khata:
        assert acc.is_demo is True
        assert acc.phone.startswith("+91 00000 000")




