"""Score a router against the router test set (AI-ML-AGENTS-PLAN.md §4.1; D63, D66, D70).

    python scripts/score_router.py              # development set with keyword rules
    python scripts/score_router.py --use-llm    # development set with Claude classifier
    python scripts/score_router.py --heldout PATH  # heldout evaluation set from QA lead
"""
import argparse
from collections import defaultdict
from pathlib import Path
import sys

from copilot.boundary import route
from copilot.evals.router_cases import BOUNDARY_INTENTS, CASES, PACK_EXPECTED
from copilot.load import load_pack


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--misses", type=int, default=0)
    ap.add_argument("--use-llm", action="store_true", default=False, help="Enable Claude structured-output classifier")
    ap.add_argument("--heldout", type=str, default=None, help="Path to QA lead heldout TSV file (INTENT<TAB>question)")
    args = ap.parse_args()

    pack = load_pack()
    known_names = []
    if hasattr(pack, "parties") and "party_name" in pack.parties.columns:
        known_names.extend(pack.parties["party_name"].dropna().tolist())
    if hasattr(pack, "invoices") and "customer_name" in pack.invoices.columns:
        known_names.extend(pack.invoices["customer_name"].dropna().tolist())
    if hasattr(pack, "bills") and "supplier_name" in pack.bills.columns:
        known_names.extend(pack.bills["supplier_name"].dropna().tolist())

    if args.heldout:
        eval_label = f"Held-out evaluation set ({args.heldout})"
        p = Path(args.heldout)
        if not p.exists():
            print(f"Error: heldout file not found: {args.heldout}", file=sys.stderr)
            return 1
        rows = []
        with open(p, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line or "\t" not in line:
                    continue
                intent, q_text = line.split("\t", 1)
                rows.append((q_text.strip(), intent.strip(), frozenset(), "unknown", f"heldout:{line_no}"))
    else:
        eval_label = "development set (not the gate)"
        rows = [(c.text, c.expect, c.also_ok, c.lang, c.source) for c in CASES]
        q = pack.questions.set_index("question_id")
        for qid, want in PACK_EXPECTED.items():
            rows.append((q.loc[qid, "question"], want, frozenset(), "en", f"pack:{qid}"))
        for qid, r in q.iterrows():
            if qid not in PACK_EXPECTED and not str(r.question_type).startswith("Behaviour"):
                rows.append((r.question, "FACT", frozenset(), "en", f"pack:{qid}"))

    stats = defaultdict(lambda: [0, 0, 0])  # key -> [n, exact, safe]
    misses = []
    for text, want, also_ok, lang, source in rows:
        got = route(text, use_llm=args.use_llm, known_names=known_names).intent
        exact = got == want or got in also_ok
        safe = exact or (got in BOUNDARY_INTENTS if want in BOUNDARY_INTENTS else False)
        for key in (want, f"lang:{lang}", "ALL BOUNDARY" if want in BOUNDARY_INTENTS else "ALL FACT"):
            s = stats[key]
            s[0] += 1
            s[1] += exact
            s[2] += safe
        if not exact:
            misses.append((source, lang, want, got, text))

    mode_str = "Keywords + Claude LLM" if args.use_llm else "Keywords only"
    print(f"=== ROUTER EVALUATION: {eval_label} ({mode_str}) ===")
    print(f"{'group':16} {'n':>4} {'exact':>7} {'safe':>7}")
    for key in sorted(stats, key=lambda k: (k.startswith("ALL"), k.startswith("lang:"), k)):
        n, e, s = stats[key]
        print(f"{key:16} {n:>4} {e / n:>7.1%} {s / n:>7.1%}")

    b, f = stats["ALL BOUNDARY"], stats["ALL FACT"]
    b_exact_rate = b[1] / b[0] if b[0] > 0 else 0.0
    f_exact_rate = f[1] / f[0] if f[0] > 0 else 0.0
    gate = (b[1] == b[0]) and (f_exact_rate >= 0.98)

    print(f"\nOverall boundary exact: {b_exact_rate:.1%} ({b[1]}/{b[0]})")
    print(f"Overall FACT exact:     {f_exact_rate:.1%} ({f[1]}/{f[0]})")
    if not args.heldout:
        print("Note: Scored on development set (not the gate). The release gate is the held-out set (D70).")
    else:
        print(f"Gate (boundary exact 100%, FACT >= 98%): {'PASS' if gate else 'FAIL'}")

    for m in misses[: args.misses]:
        print("  miss:", m)
    return 0 if gate else 1


if __name__ == "__main__":
    sys.exit(main())
