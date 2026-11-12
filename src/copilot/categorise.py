"""FR-CT-1: categorisation floor, trained only on lines before the holdout (1 Jul 2026).

Two layers, both learned from `true_category` on TRAINING lines only:
  1. payee memory: the same counterparty key seen before → its usual category
  2. lookup: (business, channel, direction) → the most common category (the 96.6% baseline [C4])
Scored by line AND by rupee, because misses can be small in count and large in money [C6].
"""
import re
from collections import Counter, defaultdict

import pandas as pd

from . import config
from .load import Pack
from .match.names import extract, norm

_DIGITS = re.compile(r"\d+")
# guide s.6: for person-to-person payments look at amount, timing and REMARK before calling it salary
_WORK_REMARK = re.compile(r"/(copy|illustration|design|video|content|photo|animation|motion|ui|ux|brand|work|project)\b",
                          re.I)

# Category names relied upon by the forecast engine (from pack.labels.true_category.unique()):
CAT_SALARY = "Salary"
CAT_GST = "GST payment"
CAT_TDS = "TDS deposited"
CAT_OWNER_DRAWINGS = "Owner drawings"
CAT_CAPITAL_INFUSION = "Capital infusion"
CAT_RENT = "Rent"


def payee_key(narration: str) -> str:
    """The counterparty, not the remark: 'IMPS/GANESH PILLAI/…/design work' and '…/illustration' are one payee."""
    name, _ = extract(narration)
    if name:
        return name
    s = _DIGITS.sub(" ", str(narration).upper())
    s = re.sub(r"[^A-Z ]", " ", s)
    words = [w for w in s.split() if len(w) > 1][:4]
    return " ".join(words)


class Categoriser:
    def __init__(self, pack: Pack, train_before: pd.Timestamp = config.HOLDOUT_START):
        lab = pack.bank.merge(pack.labels[["txn_id", "true_category"]], on="txn_id")
        train = lab[lab["txn_date"] < train_before]
        self.lookup: dict[tuple, str] = {}
        by_key: dict[tuple, Counter] = defaultdict(Counter)
        for r in train.itertuples():
            by_key[(r.business_id, r.channel, r.amount > 0)][r.true_category] += 1
        self.lookup = {k: c.most_common(1)[0][0] for k, c in by_key.items()}
        memo: dict[tuple, Counter] = defaultdict(Counter)
        for r in train.itertuples():
            memo[(r.business_id, payee_key(r.narration))][r.true_category] += 1
        # keep a payee only if it is consistent (≥ 90% one category) and seen at least twice
        self.memory = {k: c.most_common(1)[0][0] for k, c in memo.items()
                       if sum(c.values()) >= 2 and c.most_common(1)[0][1] / sum(c.values()) >= 0.9}
        self.owners = {r.business_id: norm(r.owner_or_partner) for r in pack.businesses.itertuples()}

    def predict(self, r) -> tuple[str, str]:
        k = (r.business_id, payee_key(r.narration))
        if k in self.memory:
            return self.memory[k], "payee"
        if r.amount < 0:
            nar = str(r.narration).upper()
            if self.owners.get(r.business_id, "#") in norm(nar) or nar.endswith("-SELF"):
                return "Owner drawings", "rule"
            if r.channel == "IMPS" and _WORK_REMARK.search(str(r.narration)):
                return "Freelancer / contractor payment", "rule"
        return self.lookup.get((r.business_id, r.channel, r.amount > 0), "Uncategorised"), "lookup"

    def apply(self, bank: pd.DataFrame) -> pd.DataFrame:
        out = bank.copy()
        preds = [self.predict(r) for r in out.itertuples()]
        out["category"] = [p[0] for p in preds]
        out["category_source"] = [p[1] for p in preds]
        return out


def score_categories(pack: Pack, cat: pd.DataFrame) -> pd.DataFrame:
    """Line and rupee accuracy against true_category, on all lines and on the holdout (D46)."""
    j = cat.merge(pack.labels[["txn_id", "true_category"]], on="txn_id")
    j["ok"] = j["category"] == j["true_category"]
    j["rupees"] = j["amount"].abs()
    rows = []
    for name, g in [("all lines", j), ("holdout Jul–Sep 2026", j[j["txn_date"] >= config.HOLDOUT_START])]:
        rows.append({"set": name, "lines": len(g),
                     "line_accuracy_%": round(g.ok.mean() * 100, 1),
                     "rupee_accuracy_%": round(g.loc[g.ok, "rupees"].sum() / g["rupees"].sum() * 100, 1)})
    return pd.DataFrame(rows)
