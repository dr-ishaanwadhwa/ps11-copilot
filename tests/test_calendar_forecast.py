"""The owner's balance forecast: no peeking past the start date, honest ranges, what-ifs move the right way."""
import pandas as pd
import pytest

from copilot.forecast.calendar import calendar_forecast, daily_series
from copilot.load import load_pack


@pytest.fixture(scope="module")
def pack():
    return load_pack()


def test_starts_from_the_real_balance_and_covers_the_horizon(pack):
    fc = calendar_forecast(pack, "SME-1", pd.Timestamp("2026-09-30"), horizon=60)
    assert fc.opening_balance == pytest.approx(1_238_950)
    assert len(fc.points) == 60
    assert fc.points[0].date == pd.Timestamp("2026-10-01")
    assert all(p.p10 <= p.p50 <= p.p90 for p in fc.points)
    assert fc.backtest_runs >= 4


def test_uses_only_data_up_to_the_start_date(pack):
    """Changing anything after the start date must not change the forecast."""
    start = pd.Timestamp("2026-03-31")
    before = calendar_forecast(pack, "SME-3", start, horizon=30)
    later = pack.bank.txn_date > start
    saved = pack.bank.loc[later, "amount"].copy()
    try:
        pack.bank.loc[later, "amount"] = saved * 5
        after = calendar_forecast(pack, "SME-3", start, horizon=30)
    finally:
        pack.bank.loc[later, "amount"] = saved
    assert [p.p50 for p in before.points] == pytest.approx([p.p50 for p in after.points])


def test_past_start_reports_accuracy_against_what_happened(pack):
    fc = calendar_forecast(pack, "SME-2", pd.Timestamp("2026-06-30"), horizon=90)
    assert fc.has_actuals and fc.accuracy["days"] == 90
    _, bal = daily_series(pack, "SME-2")
    assert fc.points[-1].actual == pytest.approx(float(bal[pd.Timestamp("2026-09-28")]))


def test_what_ifs_push_the_balance_the_right_way(pack):
    start = pd.Timestamp("2026-09-30")
    base = calendar_forecast(pack, "SME-1", start, horizon=30)
    late = calendar_forecast(pack, "SME-1", start, horizon=30, receipt_delay_days=15)
    down = calendar_forecast(pack, "SME-1", start, horizon=30, sales_change_pct=-20)
    up = calendar_forecast(pack, "SME-1", start, horizon=30, sales_change_pct=20)
    bill = calendar_forecast(pack, "SME-1", start, horizon=30, one_off_amount=500_000,
                             one_off_date=pd.Timestamp("2026-10-10"))
    assert late.points[-1].p50 < base.points[-1].p50
    assert down.points[-1].p50 < base.points[-1].p50 < up.points[-1].p50
    assert bill.points[8].p50 == pytest.approx(base.points[8].p50)          # 9 Oct, before the payment
    assert bill.points[9].p50 == pytest.approx(base.points[9].p50 - 500_000)  # 10 Oct onwards
    assert not late.accuracy  # what-ifs are not scored against reality
