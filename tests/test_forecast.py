"""Acceptance tests for 90-day cash forecast and shortfall warnings (FORECAST-AND-WARNINGS-SPEC.md; D71).

Acceptance checks:
1. Leakage guard (L5): view cannot see evaluation data and has no post-cutoff outcomes.
2. Statutory dates: GST on 20th, TDS on 7th, rolling Sunday to Monday [S1].
3. AST guard: no literal numeric constant within 10% of holdout actuals.
4. Salary guard: no hardcoded salary constants in src/.
5. Honest reporting: holdout MAPE is reported, not asserted to an artificial target.
6. Every warning card names 1 to 3 swing items (D40).
7. Zero advice verbs in warning card copy (strictly facts, D43).
8. Determinism: same seed yields exact same output.
"""
import ast
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from copilot.forecast import as_of, evaluate_holdout, roll_sunday_to_monday, simulate_forecast
from copilot.forecast.warnings import PROHIBITED_ADVICE


def test_2_statutory_dates_sunday_roll():
    """Test 2: Statutory dates roll Sunday to Monday [S1]."""
    # 20 Sep 2026 is Sunday -> rolls to 21 Sep (Monday)
    sun_gst = pd.Timestamp("2026-09-20")
    assert sun_gst.dayofweek == 6
    assert roll_sunday_to_monday(sun_gst) == pd.Timestamp("2026-09-21")

    # 7 Jun 2026 is Sunday -> rolls to 8 Jun (Monday)
    sun_tds = pd.Timestamp("2026-06-07")
    assert sun_tds.dayofweek == 6
    assert roll_sunday_to_monday(sun_tds) == pd.Timestamp("2026-06-08")

    # 20 Oct 2026 is Tuesday -> stays 20 Oct
    tue = pd.Timestamp("2026-10-20")
    assert roll_sunday_to_monday(tue) == tue


def test_forecast_cannot_see_evaluation_data(pack):
    """View has no cash_actuals, truth, labels, or questions; simulate_forecast runs on it."""
    cutoff = pd.Timestamp("2026-06-30")
    view = as_of(pack, cutoff)
    for attr in ["cash_actuals", "truth", "labels", "questions"]:
        assert not hasattr(view, attr), f"View leaked evaluation attribute: {attr}"
    fc = simulate_forecast(view, "SME-1", n_paths=10)
    assert fc is not None


def test_view_has_no_post_cutoff_outcomes(pack):
    """For cutoff 2026-06-30, every paid invoice has last_payment_date <= cutoff, post-cutoff columns are NaN."""
    cutoff = pd.Timestamp("2026-06-30")
    view = as_of(pack, cutoff)
    paid = view.invoices[view.invoices.last_payment_date.notna()]
    assert (paid.last_payment_date <= cutoff).all()
    unpaid = view.invoices[view.invoices.last_payment_date.isna()]
    for col in ["status_as_of_30sep2026", "disallowed_amount", "tds_deducted_by_customer"]:
        if col in unpaid.columns:
            assert unpaid[col].isna().all(), f"Unpaid invoice leaked {col}"


def test_no_literal_near_holdout_actuals(pack):
    """AST walk on src/copilot/forecast/*.py collects numeric constants >= 10,000, fails if near holdout actuals."""
    forecast_dir = Path(__file__).resolve().parents[1] / "src" / "copilot" / "forecast"
    holdout_actuals = []
    ca = pack.cash_actuals[pack.cash_actuals.is_forecast_holdout == True]
    for col in ["inflows_inr", "outflows_inr", "closing_balance_inr", "min_balance_inr"]:
        holdout_actuals.extend(ca[col].dropna().tolist())

    for py_file in forecast_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            val = None
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                val = abs(node.value)
            elif isinstance(node, ast.UnaryOp) and isinstance(node.operand, ast.Constant):
                if isinstance(node.operand.value, (int, float)):
                    val = abs(node.operand.value)
            if val is not None and val >= 10_000:
                for act in holdout_actuals:
                    if act != 0:
                        diff_ratio = abs(val - abs(act)) / abs(act)
                        assert diff_ratio > 0.10, (
                            f"Literal constant {val} in {py_file.name} is within 10% of holdout actual {act}"
                        )


def test_no_salary_constant():
    """Grep that pre-cutoff salary numbers do not appear in src/."""
    src_dir = Path(__file__).resolve().parents[1] / "src"
    prohibited = ["380160", "380_160", "925550", "925_550", "185000"]
    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text()
        for p in prohibited:
            assert p not in content, f"Hard-coded salary constant {p} found in {py_file}"


def test_scores_are_reported_not_asserted(pack):
    """evaluate_holdout returns a result object; MAPE is a finite number between 0 and 10, never a target."""
    res = evaluate_holdout(pack)
    assert np.isfinite(res.mape)
    assert 0.0 <= res.mape <= 10.0, f"MAPE {res.mape} out of range [0, 10]"


def test_6_warnings_name_2_or_3_swing_items(pack):
    """Test 6: Every warning card names 1 to 3 swing items (D40)."""
    cutoff = pd.Timestamp("2025-09-23")
    view = as_of(pack, cutoff)
    fc = simulate_forecast(view, "SME-1", n_paths=200)
    assert len(fc.warnings) > 0, "Expected at least one warning"
    for w in fc.warnings:
        assert 1 <= len(w.swing_items) <= 3, f"Warning has {len(w.swing_items)} swing items: {w.message}"


def test_7_no_advice_verbs_in_warnings(pack):
    """Test 7: Zero advice verbs in warning card copy (strictly facts, D43)."""
    cutoff = pd.Timestamp("2025-09-23")
    view = as_of(pack, cutoff)
    fc = simulate_forecast(view, "SME-1", n_paths=200)
    assert len(fc.warnings) > 0, "Expected at least one warning"
    for w in fc.warnings:
        low = w.message.lower()
        for verb in PROHIBITED_ADVICE:
            assert verb not in low, f"Prohibited advice verb '{verb}' found in warning: {w.message}"


def test_8_determinism(pack):
    """Test 8: Same seed yields exact same forecast output."""
    cutoff = pd.Timestamp("2026-06-30")
    view = as_of(pack, cutoff)
    fc1 = simulate_forecast(view, "SME-3", seed=42, n_paths=100)
    fc2 = simulate_forecast(view, "SME-3", seed=42, n_paths=100)

    assert len(fc1.monthly_forecasts) == len(fc2.monthly_forecasts)
    for m1, m2 in zip(fc1.monthly_forecasts, fc2.monthly_forecasts):
        assert m1.inflows_p50 == m2.inflows_p50
        assert m1.outflows_p50 == m2.outflows_p50
        assert m1.closing_balance_p50 == m2.closing_balance_p50
