"""Scoring against the answer keys. The only module that reads `reconciliation_truth` or `true_category`.

A bank line counts as correctly matched when our set of documents equals the answer key's set
(no-document lines must have no documents). Reported per business and per tier, because a wrong
match hurts trust most (D49): precision of AUTO matters more than coverage.
"""
from collections import Counter

import pandas as pd

from .load import Pack
from .match.engine import ASK, AUTO, NO_DOC, SUGGEST, Match


def truth_sets(pack: Pack) -> dict[str, frozenset]:
    t = pack.truth.copy()
    t["doc"] = t["document_id"].where(t["document_type"] != "NONE")
    return {k: frozenset(g["doc"].dropna()) for k, g in t.groupby("txn_id")}


def score_matches(pack: Pack, matches: dict[str, Match]) -> pd.DataFrame:
    truth = truth_sets(pack)
    biz_of = dict(zip(pack.bank["txn_id"], pack.bank["business_id"]))
    rows = []
    for txn, docs in truth.items():
        m = matches.get(txn)
        pred = frozenset(d for d, _ in m.docs) if m else None
        tier = m.tier if m else "UNMATCHED"
        correct = m is not None and tier in (AUTO, SUGGEST, NO_DOC) and pred == docs
        rows.append({"txn_id": txn, "business_id": biz_of.get(txn), "tier": tier,
                     "rule": m.rule if m else None, "correct": correct, "extra": False})
    # predictions on lines the answer key leaves out are false positives
    for txn, m in matches.items():
        if txn not in truth and m.tier in (AUTO, SUGGEST) and m.docs:
            rows.append({"txn_id": txn, "business_id": m.business_id, "tier": m.tier, "rule": m.rule,
                         "correct": False, "extra": True})
    return pd.DataFrame(rows)


def summary(df: pd.DataFrame) -> pd.DataFrame:
    keyed = df[~df["extra"]]
    out = []
    for biz, g in df.groupby("business_id"):
        k = keyed[keyed.business_id == biz]
        auto = g[g.tier.isin([AUTO, NO_DOC])]
        sug = g[g.tier == SUGGEST]
        out.append({
            "business": biz,
            "lines_in_key": len(k),
            "auto": len(auto),
            "auto_precision": round(auto.correct.mean() * 100, 1) if len(auto) else None,
            "straight_through_%": round(len(k[k.tier.isin([AUTO, NO_DOC]) & k.correct]) / len(k) * 100, 1),
            "suggest": len(sug),
            "suggest_right_%": round(sug.correct.mean() * 100, 1) if len(sug) else None,
            "ask": int((k.tier == ASK).sum()),
            "unmatched": int((k.tier == "UNMATCHED").sum()),
            "explained_if_accepted_%": round(k.correct.mean() * 100, 1),
        })
    return pd.DataFrame(out)


def worst_cases(df: pd.DataFrame, pack: Pack, matches: dict[str, Match], n: int = 10) -> pd.DataFrame:
    """Brief Stage 2: the cases the system gets most wrong. Wrong AUTO matches first, then the largest misses."""
    bank = pack.bank.set_index("txn_id")
    wrong = df[(~df.correct) & df.tier.isin([AUTO, SUGGEST])].copy()
    wrong["amount"] = wrong.txn_id.map(bank["amount"]).abs()
    wrong["auto_first"] = (wrong.tier != AUTO).astype(int)
    wrong = wrong.sort_values(["auto_first", "amount"], ascending=[True, False]).head(n)
    wrong["narration"] = wrong.txn_id.map(bank["narration"])
    return wrong[["txn_id", "business_id", "tier", "rule", "amount", "narration"]]


def rule_mix(matches: dict[str, Match]) -> Counter:
    return Counter((m.business_id, m.rule, m.tier) for m in matches.values())
