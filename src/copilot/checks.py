"""FR-IM-2 / FR-IM-3: checks run on every import before anything is trusted.

Running-balance continuity is the guard against missed lines (gap M1): each line's balance must
equal the previous line's balance plus its credit minus its debit. Idea ported from small MIT
statement parsers (see ps11-research/market/OSS-REPOS.md, Pass 2), reimplemented here.
"""
from dataclasses import dataclass

import pandas as pd

from .load import Pack


@dataclass
class BalanceBreak:
    business_id: str
    txn_id: str
    txn_date: pd.Timestamp
    expected: float
    actual: float

    @property
    def gap(self) -> float:
        return round(self.actual - self.expected, 2)


def balance_breaks(bank: pd.DataFrame, opening: dict[str, float] | None = None, tol: float = 0.5) -> list[BalanceBreak]:
    breaks: list[BalanceBreak] = []
    for biz, g in bank.sort_values("seq").groupby("business_id", sort=False):
        prev = None if opening is None else opening.get(biz)
        for r in g.itertuples():
            if prev is not None:
                expected = prev + r.credit_inr - r.debit_inr
                if abs(expected - r.balance_inr) > tol:
                    breaks.append(BalanceBreak(biz, r.txn_id, r.txn_date, round(expected, 2), r.balance_inr))
            prev = r.balance_inr
    return breaks


def import_report(pack: Pack) -> dict:
    opening = dict(zip(pack.businesses["business_id"], pack.businesses["opening_balance_1apr2025"].astype(float)))
    breaks = balance_breaks(pack.bank, opening)
    inv = pack.invoices
    return {
        "bank_lines": len(pack.bank),
        "duplicates_skipped": pack.duplicates_skipped,
        "balance_breaks": len(breaks),
        "balance_ties": len(breaks) == 0,
        "documents": len(inv),
        "repeated_invoice_numbers": int(inv["invoice_no"].duplicated().sum()),
        "purchase_bills": len(pack.bills),
        "breaks": breaks[:20],
    }
