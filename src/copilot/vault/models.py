"""Data models for the cash book plane (local-first on-device ledger).

In accordance with the Dual-Plane Architecture:
- Tracks physical Galla cash, daily Rokad in/out, and informal Pending Khata.
- Completely isolated from formal accounting books (never exported to CA or GST).
- Employs neutral commercial terminology (no incriminating language).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import pandas as pd
from .. import config


@dataclass
class GallaEntry:
    """Daily cash drawer record for balancing physical till cash."""
    business_id: str
    date: pd.Timestamp
    opening_cash: float
    cash_in: float           # e.g., daily counter takings, direct settlements
    cash_out: float          # e.g., hamali, freight, local cash purchases
    cash_banked: float       # cash deposited into bank current/savings account
    counted_cash: float      # physical cash counted in drawer at day close
    notes: str = ""
    is_demo: bool = False

    @property
    def expected_cash(self) -> float:
        return round(self.opening_cash + self.cash_in - self.cash_out - self.cash_banked, 2)

    @property
    def drift(self) -> float:
        """Discrepancy between counted cash and book expected cash."""
        return round(self.counted_cash - self.expected_cash, 2)

    @property
    def is_balanced(self) -> bool:
        return abs(self.drift) < 50.0  # ₹50 normal till tolerance

    @property
    def status_label(self) -> str:
        return "Balanced" if self.is_balanced else "Drift to check"


@dataclass
class Collection:
    """Salesman collection slip entry for cash collections (Task 5.3, D55)."""
    business_id: str
    date: pd.Timestamp
    shop: str
    amount: float
    salesman: str = ""


@dataclass
class RokadEntry:
    """Individual cash-in / cash-out entry in the daily cash book."""
    entry_id: str
    business_id: str
    timestamp: pd.Timestamp
    direction: str           # "IN" or "OUT"
    amount: float
    category: str            # e.g., "COUNTER_SALE", "HAMALI", "FREIGHT", "SUPPLIER_ROKDA", "PETTY_EXPENSE"
    counterparty: str
    note: str = ""


@dataclass
class KhataAccount:
    """Informal trade credit or pending khata ledger."""
    party_name: str
    business_id: str
    balance_due: float       # + they owe us, - we owe them
    last_active_date: pd.Timestamp
    months_open: int = 0
    phone: str = ""
    is_demo: bool = False

    @property
    def is_limitation_alert(self) -> bool:
        """Section 18 Limitation Act alert: debts older than 30 months risk becoming unenforceable."""
        return self.months_open >= 30


@dataclass
class TotalSolvency:
    """Unified dual-plane liquidity analysis."""
    business_id: str
    as_of: pd.Timestamp
    bank_balance: float
    cc_limit: float
    cc_drawn: float
    galla_cash: float
    informal_receivables: float
    informal_payables: float
    formal_commitments: float   # upcoming payroll, statutory dues, supplier bills
    haircut_alpha: float = config.KHATA_COLLECTION_ASSUMPTION # risk-adjusted recovery rate on informal receivables

    @property
    def net_bank_liquidity(self) -> float:
        """Available headroom in bank (balance plus unused CC limit)."""
        headroom = max(0.0, self.cc_limit - self.cc_drawn) if self.cc_limit > 0 else 0.0
        return self.bank_balance + headroom

    @property
    def total_liquidity_reserve(self) -> float:
        """True liquid cash = bank balance + physical cash in drawer."""
        return self.bank_balance + self.galla_cash

    @property
    def total_expected_inflows(self) -> float:
        return round(self.informal_receivables * self.haircut_alpha, 2)

    @property
    def total_commitments(self) -> float:
        return round(self.formal_commitments + self.informal_payables, 2)

    @property
    def true_cash_runway_inr(self) -> float:
        """
        True Cash Runway Buffer =
          (Bank Bal - CC Overdraft) + Galla Cash + (α * Kaccha Inflows) - (Formal Commitments + Cash Payables)
        """
        return round(
            (self.bank_balance - self.cc_drawn)
            + self.galla_cash
            + self.total_expected_inflows
            - self.total_commitments,
            2
        )

    @property
    def is_false_insolvency(self) -> bool:
        """
        True if the bank-only view signals a severe cash crunch while
        the combined dual-plane solvency remains positive.
        """
        bank_alone = (self.bank_balance - self.cc_drawn) - self.formal_commitments
        return bank_alone < 0 and self.true_cash_runway_inr > 0
