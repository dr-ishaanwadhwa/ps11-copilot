"""Evaluation, backtesting and scoring for 90-day cash forecast (FR-FC-1, FR-FC-2; D71).

Implements:
- Holdout evaluation on 18 series-months (Jul, Aug, Sep 2026) against `cash_actuals`
- Naive 3-month baseline comparison (18.19% on holdout [F1])
- Agency inflows comparison (naive 46.2% [F2])
- Paired bootstrap test (seed 0, 10,000 resamples) of improvement vs baseline
- P10-P90 coverage of actuals
- Historical rolling backtest evaluation across 10 month-end cutoffs (2025-06-30 to 2026-03-31)
- Warning lead-time replay across historical trigger breach events
"""
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

from ..load import Pack
from .asof import as_of
from .engine import get_credit_limit, simulate_forecast
from .models import ForecastResult


@dataclass
class SeriesScore:
    business_id: str
    month: str
    series: str  # inflow | outflow
    predicted_p50: float
    actual: float
    ape: float
    naive_pred: float
    naive_ape: float
    p10: float
    p90: float
    covered: bool


@dataclass
class HoldoutEvaluation:
    mape: float
    naive_mape: float
    agency_inflow_mape: float
    naive_agency_inflow_mape: float
    bootstrap_diff_mean: float
    bootstrap_diff_ci: tuple[float, float]
    coverage_p10_p90: float
    scores: list[SeriesScore]
    false_alarms: dict[str, int]


def evaluate_holdout(pack: Pack, cutoff: pd.Timestamp = pd.Timestamp("2026-06-30")) -> HoldoutEvaluation:
    """Evaluate 90-day forecast against the frozen 3-month holdout (Jul-Sep 2026)."""
    ca = pack.cash_actuals
    holdout = ca[ca.is_forecast_holdout == True].set_index(["business_id", "month"])

    # 1. Compute naive 3-month baseline from pre-cutoff months (Apr, May, Jun 2026)
    pre = ca[ca.month.isin(["2026-04", "2026-05", "2026-06"])]
    naive_means = pre.groupby("business_id")[["inflows_inr", "outflows_inr"]].mean()

    scores: list[SeriesScore] = []
    false_alarms: dict[str, int] = {}

    view = as_of(pack, cutoff)

    for biz in ["SME-1", "SME-2", "SME-3"]:
        fc: ForecastResult = simulate_forecast(view, biz, n_paths=1000, seed=0)
        false_alarms[biz] = len([w for w in fc.warnings if w.level == "LIKELY"])

        for mf in fc.monthly_forecasts:
            key = (biz, mf.month)
            if key not in holdout.index:
                continue
            act_row = holdout.loc[key]
            act_in = float(act_row["inflows_inr"])
            act_out = float(act_row["outflows_inr"])

            naive_in = float(naive_means.loc[biz, "inflows_inr"])
            naive_out = float(naive_means.loc[biz, "outflows_inr"])

            ape_in = abs(mf.inflows_p50 - act_in) / act_in
            ape_out = abs(mf.outflows_p50 - act_out) / act_out

            naive_ape_in = abs(naive_in - act_in) / act_in
            naive_ape_out = abs(naive_out - act_out) / act_out

            cov_in = bool(mf.inflows_p10 <= act_in <= mf.inflows_p90)
            cov_out = bool(mf.outflows_p10 <= act_out <= mf.outflows_p90)

            scores.append(
                SeriesScore(
                    business_id=biz,
                    month=mf.month,
                    series="inflow",
                    predicted_p50=mf.inflows_p50,
                    actual=act_in,
                    ape=ape_in,
                    naive_pred=naive_in,
                    naive_ape=naive_ape_in,
                    p10=mf.inflows_p10,
                    p90=mf.inflows_p90,
                    covered=cov_in,
                )
            )
            scores.append(
                SeriesScore(
                    business_id=biz,
                    month=mf.month,
                    series="outflow",
                    predicted_p50=mf.outflows_p50,
                    actual=act_out,
                    ape=ape_out,
                    naive_pred=naive_out,
                    naive_ape=naive_ape_out,
                    p10=mf.outflows_p10,
                    p90=mf.outflows_p90,
                    covered=cov_out,
                )
            )

    mape = float(np.mean([s.ape for s in scores]))
    naive_mape = float(np.mean([s.naive_ape for s in scores]))

    # Assert naive value matches fixed property of data (18.19% [F1])
    assert abs(naive_mape - 0.1819) < 0.001, f"Naive MAPE {naive_mape:.4f} did not match expected 18.19%"

    agency_in_scores = [s for s in scores if s.business_id == "SME-3" and s.series == "inflow"]
    agency_in_mape = float(np.mean([s.ape for s in agency_in_scores]))
    naive_agency_in_mape = float(np.mean([s.naive_ape for s in agency_in_scores]))

    # Paired bootstrap test (seed 0, 10,000 resamples) of improvement (naive_ape - our_ape)
    rng = np.random.default_rng(0)
    diffs = np.array([s.naive_ape - s.ape for s in scores])
    n = len(diffs)
    resamples = rng.choice(diffs, size=(10_000, n), replace=True)
    resample_means = resamples.mean(axis=1)

    boot_mean = float(np.mean(resample_means))
    boot_ci = (float(np.percentile(resample_means, 2.5)), float(np.percentile(resample_means, 97.5)))

    cov_rate = float(np.mean([1.0 if s.covered else 0.0 for s in scores]))

    return HoldoutEvaluation(
        mape=mape,
        naive_mape=naive_mape,
        agency_inflow_mape=agency_in_mape,
        naive_agency_inflow_mape=naive_agency_in_mape,
        bootstrap_diff_mean=boot_mean,
        bootstrap_diff_ci=boot_ci,
        coverage_p10_p90=cov_rate,
        scores=scores,
        false_alarms=false_alarms,
    )


def evaluate_backtests(pack: Pack, n_paths: int = 300) -> dict[str, float]:
    """Month-end cutoffs from 2025-06-30 to 2026-03-31 (10 cutoffs), each scored on next 3 months.
    
    Uses n_paths=300 for execution speed.
    """
    cutoffs = pd.date_range("2025-06-30", "2026-03-31", freq="ME")
    ca = pack.cash_actuals.set_index(["business_id", "month"])

    scores_by_biz = {"SME-1": [], "SME-2": [], "SME-3": []}
    all_scores: list[float] = []

    for cutoff in cutoffs:
        view = as_of(pack, cutoff)
        next_months = [(cutoff + pd.DateOffset(months=i)).strftime("%Y-%m") for i in [1, 2, 3]]
        for biz in ["SME-1", "SME-2", "SME-3"]:
            fc = simulate_forecast(view, biz, n_paths=n_paths, seed=0)
            for mf in fc.monthly_forecasts:
                if mf.month in next_months and (biz, mf.month) in ca.index:
                    act = ca.loc[(biz, mf.month)]
                    act_in = float(act["inflows_inr"])
                    act_out = float(act["outflows_inr"])
                    ape_in = abs(mf.inflows_p50 - act_in) / act_in if act_in > 0 else 0.0
                    ape_out = abs(mf.outflows_p50 - act_out) / act_out if act_out > 0 else 0.0
                    scores_by_biz[biz].extend([ape_in, ape_out])
                    all_scores.extend([ape_in, ape_out])

    res = {
        "pooled_mape": float(np.mean(all_scores)),
        "sme1_mape": float(np.mean(scores_by_biz["SME-1"])),
        "sme2_mape": float(np.mean(scores_by_biz["SME-2"])),
        "sme3_mape": float(np.mean(scores_by_biz["SME-3"])),
    }
    return res


def replay_lead_times(pack: Pack, cache_path: Path | None = None) -> pd.DataFrame:
    """Replay warning lead times for historical trigger breach events (D71 §2.7).
    
    Caches output to cache_path (default scripts/out/lead_times.csv).
    """
    if cache_path is None:
        cache_path = Path(__file__).resolve().parents[3] / "scripts" / "out" / "lead_times.csv"

    if cache_path.exists():
        return pd.read_csv(cache_path)

    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Detect events: runs of days where actual balance crosses a trigger
    # Event 1: Distributor CC headroom < 2.5L
    b1 = pack.bank[pack.bank.business_id == "SME-1"].sort_values(["txn_date", "seq"])
    daily_b1 = b1.groupby("txn_date")["balance_inr"].last()
    sample_view = as_of(pack, b1.txn_date.min())
    limit = get_credit_limit(sample_view, "SME-1")
    breach_days = daily_b1[daily_b1 < (250000.0 - limit)].index.tolist()

    runs: list[list[pd.Timestamp]] = []
    current_run: list[pd.Timestamp] = []
    for d in breach_days:
        if not current_run or (d - current_run[-1]).days == 1:
            current_run.append(d)
        else:
            runs.append(current_run)
            current_run = [d]
    if current_run:
        runs.append(current_run)

    event_rows = []
    for r in runs:
        event_t = r[0]
        # Run daily cutoffs d = t-30 ... t-1 (n_paths=200)
        on_flags = {}
        for days_ahead in range(1, 31):
            d = event_t - pd.Timedelta(days=days_ahead)
            view = as_of(pack, d)
            fc = simulate_forecast(view, "SME-1", n_paths=200, seed=0)
            is_on = False
            for p in fc.daily_points:
                if abs((p.date - event_t).days) <= 10:
                    if (limit + p.balance_p50) < 250000.0:
                        is_on = True
                        break
            on_flags[days_ahead] = is_on

        # Lead time = t - earliest d from which warning stays on every day until t-1
        lead_time = 0
        for k in range(1, 31):
            if all(on_flags.get(j, False) for j in range(1, k + 1)):
                lead_time = k
            else:
                break

        event_rows.append({
            "business_id": "SME-1",
            "trigger": "CREDIT_LIMIT",
            "event_date": str(event_t.date()),
            "lead_time_days": lead_time,
            "run_length_days": len(r),
        })

    # Holdout false alarms: likely warnings on holdout (cutoff 2026-06-30)
    holdout_view = as_of(pack, pd.Timestamp("2026-06-30"))
    for biz in ["SME-1", "SME-2", "SME-3"]:
        fc = simulate_forecast(holdout_view, biz, n_paths=200, seed=0)
        likely_count = len([w for w in fc.warnings if w.level == "LIKELY"])
        event_rows.append({
            "business_id": biz,
            "trigger": "HOLDOUT_FALSE_ALARMS",
            "event_date": "2026-06-30",
            "lead_time_days": 0,
            "run_length_days": likely_count,
        })

    df = pd.DataFrame(event_rows)
    df.to_csv(cache_path, index=False)
    return df
