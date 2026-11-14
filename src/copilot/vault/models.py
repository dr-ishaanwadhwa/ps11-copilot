"""Data models for the cash book plane (local-first on-device ledger).

In accordance with the Dual-Plane Architecture:
- Tracks physical Galla cash, daily Rokad in/out, and informal Pending Khata.
- Completely isolated from formal accounting books (never exported to CA or GST).
- Employs neutral commercial terminology (no incriminating language).
"""
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd
from .. import config

PARTIAL_VIEW_NOTICE = "Formal books only. The owner's cash memo is not included in this view."


@dataclass
class GallaEntry:
    """Daily cash drawer record for balancing physical till cash."""
    business_id: str
    date: pd.Timestamp
    opening_cash: float
    cash_in: float
    cash_out: float
    cash_banked: float
    counted_cash: float
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


def calculate_drawer_balance(
    opening_cash: float,
    cash_in: float,
    cash_out: float,
    cash_banked: float,
    counted_cash: float,
) -> dict:
    """Calculate 5-variable cash drawer balance and drift."""
    expected_cash = round(opening_cash + cash_in - cash_out - cash_banked, 2)
    drift = round(counted_cash - expected_cash, 2)
    is_balanced = abs(drift) < 50.0
    return {
        "opening_cash": round(opening_cash, 2),
        "cash_in": round(cash_in, 2),
        "cash_out": round(cash_out, 2),
        "cash_banked": round(cash_banked, 2),
        "expected_cash": expected_cash,
        "counted_cash": round(counted_cash, 2),
        "drift": drift,
        "is_balanced": is_balanced,
        "status_label": "Balanced" if is_balanced else "Drift to check",
    }


@dataclass
class Collection:
    """Salesman collection slip entry for route collections (ADR-001, ADR-004, R3)."""
    business_id: str
    date: pd.Timestamp
    shop: str
    amount: float
    salesman: str = ""
    payment_mode: str = "CASH"
    slip_id: str = ""
    invoice_no: str = ""
    is_banked: bool = False
    bank_txn_id: str = ""
    notes: str = ""

    def __init__(
        self,
        business_id: str = "",
        date: pd.Timestamp | str | None = None,
        shop: str = "",
        amount: float = 0.0,
        salesman: str = "",
        payment_mode: str = "CASH",
        slip_id: str = "",
        invoice_no: str = "",
        is_banked: bool = False,
        bank_txn_id: str = "",
        notes: str = "",
        *,
        shop_name: str | None = None,
        salesman_name: str | None = None,
        slip_no: str | None = None,
        **kwargs,
    ):
        self.business_id = business_id
        if date is None:
            self.date = pd.Timestamp.now()
        elif isinstance(date, str):
            self.date = pd.Timestamp(date)
        else:
            self.date = date
        self.shop = shop_name if shop_name is not None else shop
        self.amount = float(amount)
        self.salesman = salesman_name if salesman_name is not None else salesman
        self.payment_mode = (payment_mode or "CASH").upper()
        self.slip_id = slip_no if slip_no is not None else (slip_id or "")
        if not self.slip_id:
            import uuid
            self.slip_id = f"SLIP-{uuid.uuid4().hex[:8].upper()}"
        self.invoice_no = invoice_no or ""
        self.is_banked = bool(is_banked)
        self.bank_txn_id = bank_txn_id or ""
        self.notes = notes or ""

    @property
    def shop_name(self) -> str:
        return self.shop

    @shop_name.setter
    def shop_name(self, value: str) -> None:
        self.shop = value

    @property
    def salesman_name(self) -> str:
        return self.salesman

    @salesman_name.setter
    def salesman_name(self, value: str) -> None:
        self.salesman = value

    @property
    def slip_no(self) -> str:
        return self.slip_id

    @slip_no.setter
    def slip_no(self, value: str) -> None:
        self.slip_id = value


@dataclass
class RokadEntry:
    """Individual cash-in / cash-out entry in the daily cash book."""
    entry_id: str
    business_id: str
    timestamp: pd.Timestamp
    direction: str
    amount: float
    category: str
    counterparty: str
    note: str = ""


@dataclass
class KhataAccount:
    """Informal trade credit or pending khata ledger."""
    party_name: str
    business_id: str
    balance_due: float
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
