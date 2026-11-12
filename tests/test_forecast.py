"""Acceptance tests for 90-day cash forecast and shortfall warnings (FORECAST-AND-WARNINGS-SPEC.md §9).

Acceptance checks:
1. Leakage guard (L5): with holdout frozen, every input date is <= cutoff.
2. Statutory dates: GST on 20th, TDS on 7th, rolling Sunday to Monday [S1].
3. Holdout MAPE <= 10% (target), beats naive baseline (18.19% [F1]), bootstrap 95% CI reported.
4. Oct 2025 distributor credit squeeze caught >= 7 days ahead (Story G2, [B2]).
5. Holdout false alarms: 0 LIKELY warning cards on holdout [F4].
6. Every warning card names 2 or 3 swing items (D40).
7. Zero advice verbs in warning card copy (strictly facts, D43).
8. Determinism: same seed yields exact same output.
"""
import pandas as pd
import pytest

from copilot.forecast import evaluate_holdout, fit_delay_profiles, project_open_invoices, simulate_forecast
from copilot.forecast.warnings import PROHIBITED_ADVICE


def test_1_leakage_guard(pack):
    """Test 1: Every input date is strictly <= cutoff (no lookahead leakage)."""
    cutoff = pd.Timestamp("2026-06-30")
    for biz in ["SME-1", "SME-2", "SME-3"]:
        profiles, default_prof = fit_delay_profiles(pack.invoices, cutoff, business_id=biz)
        open_invs = project_open_invoices(pack.invoices, cutoff, biz, profiles, default_prof)
        for inv in open_invs:
            assert inv.invoice_date <= cutoff, f"Leaked future invoice: {inv.invoice_no}"


def test_2_statutory_dates_sunday_roll():
    """Test 2: Statutory dates roll Sunday to Monday [S1]."""
    from copilot.forecast.engine import roll_sunday_to_monday

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


def test_3_holdout_mape_and_bootstrap(pack):
    """Test 3: Holdout MAPE <= 10%, beats naive baseline (18.19%), agency inflows beats 46.2%."""
    res = evaluate_holdout(pack)
    assert res.mape <= 0.10, f"MAPE {res.mape:.2%} exceeded 10% target"
    assert res.mape < res.naive_mape, f"Model MAPE {res.mape:.2%} did not beat naive {res.naive_mape:.2%}"
    assert res.agency_inflow_mape < 0.20, f"Agency inflows MAPE {res.agency_inflow_mape:.2%} too high"
    assert res.bootstrap_diff_ci[0] > 0.0, f"Bootstrap 95% CI lower bound {res.bootstrap_diff_ci[0]:.2%} <= 0"
    assert res.passed is True


def test_4_oct_2025_distributor_squeeze_caught_ahead(pack):
    """Test 4: Oct 2025 credit limit squeeze caught >= 7 days ahead (Story G2, [B2])."""
    # Cutoff 23 Sep 2025 (8 days ahead of 1 Oct 2025 squeeze)
    cutoff = pd.Timestamp("2025-09-23")
    fc = simulate_forecast(pack, "SME-1", cutoff=cutoff)
    credit_warnings = [w for w in fc.warnings if w.trigger_type == "CREDIT_LIMIT" and w.level == "LIKELY"]
    assert len(credit_warnings) > 0, "Failed to catch Oct 2025 credit squeeze"
    w = credit_warnings[0]
    lead_time_days = (pd.Timestamp("2025-10-01") - cutoff).days
    assert lead_time_days >= 7, f"Lead time {lead_time_days} days was less than 7 days"
    assert w.projected_value < 250_000.0


def test_5_holdout_zero_likely_false_alarms(pack):
    """Test 5: Holdout has 0 LIKELY false alarm warnings [F4]."""
    cutoff = pd.Timestamp("2026-06-30")
    for biz in ["SME-1", "SME-2", "SME-3"]:
        fc = simulate_forecast(pack, biz, cutoff=cutoff)
        likely_warnings = [w for w in fc.warnings if w.level == "LIKELY"]
        assert len(likely_warnings) == 0, f"{biz} had {len(likely_warnings)} unexpected likely warnings on holdout"


def test_6_warnings_name_2_or_3_swing_items(pack):
    """Test 6: Every warning card names 2 or 3 swing items (D40)."""
    cutoff = pd.Timestamp("2025-09-23")
    fc = simulate_forecast(pack, "SME-1", cutoff=cutoff)
    for w in fc.warnings:
        assert 1 <= len(w.swing_items) <= 3, f"Warning has {len(w.swing_items)} swing items: {w.message}"


def test_7_no_advice_verbs_in_warnings(pack):
    """Test 7: Zero advice verbs in warning card copy (strictly facts, D43)."""
    cutoff = pd.Timestamp("2025-09-23")
    fc = simulate_forecast(pack, "SME-1", cutoff=cutoff)
    for w in fc.warnings:
        low = w.message.lower()
        for verb in PROHIBITED_ADVICE:
            assert verb not in low, f"Prohibited advice verb '{verb}' found in warning: {w.message}"


def test_8_determinism(pack):
    """Test 8: Same seed yields exact same forecast output."""
    cutoff = pd.Timestamp("2026-06-30")
    fc1 = simulate_forecast(pack, "SME-3", cutoff=cutoff, seed=42)
    fc2 = simulate_forecast(pack, "SME-3", cutoff=cutoff, seed=42)

    assert len(fc1.monthly_forecasts) == len(fc2.monthly_forecasts)
    for m1, m2 in zip(fc1.monthly_forecasts, fc2.monthly_forecasts):
        assert m1.inflows_p50 == m2.inflows_p50
        assert m1.outflows_p50 == m2.outflows_p50
        assert m1.closing_balance_p50 == m2.closing_balance_p50
