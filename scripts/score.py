"""Score the matcher against reconciliation_truth and write a report.

    python scripts/score.py            # prints the summary and the ten worst cases
    python scripts/score.py --json out.json
"""
import argparse
import json
import sys

import pandas as pd

from copilot.forecast import evaluate_holdout
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

    print("=== 90-DAY FORECAST HOLDOUT BENCHMARK (FR-FC-1, FR-FC-2; D48) ===")
    print("forecast: not scored (being rebuilt; see CORRECTIONS-REPORT.md)")
    if args.json:
        with open(args.json, "w") as f:
            json.dump({
                "matching_overall": overall,
                "by_business": s.to_dict("records"),
                "worst": w.astype(str).to_dict("records"),
                "forecast_holdout": "not scored (being rebuilt; see CORRECTIONS-REPORT.md)",
            }, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
