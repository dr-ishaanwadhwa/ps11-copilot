"""Score the matcher against reconciliation_truth and write a report.

    python scripts/score.py            # prints the summary and the ten worst cases
    python scripts/score.py --json out.json
"""
import argparse
import json
import sys

import pandas as pd

from copilot.forecast import evaluate_backtests, evaluate_holdout, replay_lead_times
from copilot.load import load_pack
from copilot.match import match_all
from copilot.score import score_matches, summary, worst_cases


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    args = ap.parse_args()
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 20)

    pack = load_pack()
    matches = match_all(pack)
    df = score_matches(pack, matches)
    keyed = df[~df["extra"]]
    auto = df[df.tier.isin(["AUTO", "NO_DOC"])]
    overall = {
        "auto_precision_%": round(auto.correct.mean() * 100, 2),
        "straight_through_%": round((keyed.tier.isin(["AUTO", "NO_DOC"]) & keyed.correct).mean() * 100, 1),
        "explained_if_suggestions_accepted_%": round(keyed.correct.mean() * 100, 1),
        "lines_in_key": len(keyed),
        "false_positive_lines_outside_key": int(df["extra"].sum()),
    }
    s = summary(df)
    w = worst_cases(df, pack, matches)
    print("=== RECONCILIATION MATCHING (FR-RC-1) ===")
    print(s.to_string(index=False), "\n")
    print("overall:", overall, "\n")
    print("ten worst cases (wrong AUTO first, then largest):")
    print(w.to_string(index=False), "\n")

    print("=== 90-DAY FORECAST HOLDOUT BENCHMARK (FR-FC-1, FR-FC-2; D48, D71) ===")
    fc_eval = evaluate_holdout(pack)
    print(f"Holdout Pooled MAPE: {fc_eval.mape:.2%} (naive 3-month baseline: {fc_eval.naive_mape:.2%})")
    print(f"Agency Inflows MAPE: {fc_eval.agency_inflow_mape:.2%} (naive baseline: {fc_eval.naive_agency_inflow_mape:.2%})")
    print(f"Bootstrap diff (naive - model): {fc_eval.bootstrap_diff_mean:+.2%} (95% CI: [{fc_eval.bootstrap_diff_ci[0]:+.2%}, {fc_eval.bootstrap_diff_ci[1]:+.2%}])")
    print(f"Holdout P10-P90 Coverage: {fc_eval.coverage_p10_p90:.1%}\n")
    print("Per-series holdout scores:")
    score_rows = [
        {
            "business_id": s.business_id,
            "month": s.month,
            "series": s.series,
            "pred_p50": round(s.predicted_p50),
            "actual": round(s.actual),
            "ape": f"{s.ape:.2%}",
            "naive_ape": f"{s.naive_ape:.2%}",
            "p10_p90": f"[{round(s.p10):,}, {round(s.p90):,}]",
            "covered": s.covered,
        }
        for s in fc_eval.scores
    ]
    print(pd.DataFrame(score_rows).to_string(index=False), "\n")

    print("Historical Backtests (10 month-end cutoffs Jun 2025 – Mar 2026, n_paths=300):")
    bt_eval = evaluate_backtests(pack)
    print(f"  Pooled Backtest MAPE: {bt_eval['pooled_mape']:.2%}")
    print(f"  SME-1 Backtest MAPE: {bt_eval['sme1_mape']:.2%}")
    print(f"  SME-2 Backtest MAPE: {bt_eval['sme2_mape']:.2%}")
    print(f"  SME-3 Backtest MAPE: {bt_eval['sme3_mape']:.2%}\n")

    print("Warning Lead Times (Replay on historical breach events):")
    lt_df = replay_lead_times(pack)
    print(lt_df.to_string(index=False), "\n")

    if args.json:
        with open(args.json, "w") as f:
            json.dump({
                "matching_overall": overall,
                "by_business": s.to_dict("records"),
                "worst": w.astype(str).to_dict("records"),
                "forecast_holdout": {
                    "mape": fc_eval.mape,
                    "naive_mape": fc_eval.naive_mape,
                    "agency_inflow_mape": fc_eval.agency_inflow_mape,
                    "naive_agency_inflow_mape": fc_eval.naive_agency_inflow_mape,
                    "bootstrap_diff_mean": fc_eval.bootstrap_diff_mean,
                    "bootstrap_diff_ci": list(fc_eval.bootstrap_diff_ci),
                    "coverage_p10_p90": fc_eval.coverage_p10_p90,
                    "false_alarms": fc_eval.false_alarms,
                },
                "backtest_evaluation": bt_eval,
                "lead_times": lt_df.to_dict("records"),
            }, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
