"""Evaluation, backtesting and scoring for 90-day cash forecast (FR-FC-1, FR-FC-2; D48).

Implements:
- Holdout evaluation on 18 series-months (Jul, Aug, Sep 2026) against `cash_actuals`
- Naive 3-month baseline comparison (18.19% on holdout [F1])
- Agency inflows comparison (naive 46.2% [F2])
- Paired bootstrap test (seed 0, 10,000 resamples) of improvement vs baseline
- Early warning false alarm checks (0 events in holdout [F4])
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd

from ..load import Pack
from .engine import simulate_forecast
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


@dataclass
class HoldoutEvaluation:
    mape: float
    naive_mape: float
    agency_inflow_mape: float
    naive_agency_inflow_mape: float
    bootstrap_diff_mean: float
    bootstrap_diff_ci: tuple[float, float]
    passed: bool
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

    for biz in ["SME-1", "SME-2", "SME-3"]:
        fc: ForecastResult = simulate_forecast(pack, biz, cutoff=cutoff)
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
                )
            )

    mape = float(np.mean([s.ape for s in scores]))
    naive_mape = float(np.mean([s.naive_ape for s in scores]))

    agency_in_scores = [s for s in scores if s.business_id == "SME-3" and s.series == "inflow"]
    agency_in_mape = float(np.mean([s.ape for s in agency_in_scores]))
    naive_agency_in_mape = float(np.mean([s.naive_ape for s in agency_in_scores]))

    # Paired bootstrap test (seed 0, 10,000 resamples) of improvement (naive_ape - our_ape)
    np.random.seed(0)
    diffs = np.array([s.naive_ape - s.ape for s in scores])
    n = len(diffs)
    resamples = np.random.choice(diffs, size=(10_000, n), replace=True)
    resample_means = resamples.mean(axis=1)

    boot_mean = float(np.mean(resample_means))
    boot_ci = (float(np.percentile(resample_means, 2.5)), float(np.percentile(resample_means, 97.5)))

    passed = (mape <= 0.10) and (mape < naive_mape)

    return HoldoutEvaluation(
        mape=mape,
        naive_mape=naive_mape,
        agency_inflow_mape=agency_in_mape,
        naive_agency_inflow_mape=naive_agency_in_mape,
        bootstrap_diff_mean=boot_mean,
        bootstrap_diff_ci=boot_ci,
        passed=passed,
        scores=scores,
        false_alarms=false_alarms,
    )
