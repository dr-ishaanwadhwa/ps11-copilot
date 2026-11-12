"""Total Solvency Engine: Reconciling formal bank liquidity with physical cash.

Solves the 'False Insolvency' dilemma:
- An SME owner looks broke in their bank overdraft while sitting on substantial Galla cash.
- Or, an owner looks healthy on bank balance while owing heavy unrecorded cash supplier dues.

True Cash Runway Buffer:
  (Bank Bal - CC Drawn) + Galla Cash + (α * Kaccha Inflows) - (Formal Commitments + Cash Payables)
"""
from __future__ import annotations

import pandas as pd
from .. import config
from ..load import Pack
from .db import VaultDB
from .models import TotalSolvency


def compute_total_solvency(
    pack: Pack,
    vault: VaultDB,
    biz: str,
    as_of: pd.Timestamp = pd.Timestamp("2026-09-30"),
    haircut_alpha: float = config.KHATA_COLLECTION_ASSUMPTION,
) -> TotalSolvency:
    """Computes the unified dual-plane liquidity analysis for an SME."""
    b = pack.bank[(pack.bank.business_id == biz) & (pack.bank.txn_date <= as_of)]
    last_bank = b.sort_values(["txn_date", "seq"]).iloc[-1]
    bank_bal = float(last_bank.balance_inr)
    
    cc_limit = pack.credit_limit(biz)
    cc_drawn = abs(bank_bal) if (bank_bal < 0 and cc_limit > 0) else 0.0

    latest_galla = vault.get_latest_galla(biz)
    galla_cash = latest_galla.counted_cash if latest_galla else 0.0

    khata = vault.get_khata_summary(biz)
    informal_recv = khata["receivables"]
    informal_pay = khata["payables"]

    sal_re = b[(b.amount < 0) & (b.narration.str.contains("SALARY|SAL|WAGES", case=False, na=False))]
    monthly_sal = abs(sal_re.amount.tail(15).sum()) / 2.0 if not sal_re.empty else 150_000.0
    
    bills = pack.bills[(pack.bills.business_id == biz) & (pack.bills.bill_date <= as_of)]
    open_bills = float(bills.bill_total.sum() - bills.bill_total.head(len(bills)//2).sum()) if not bills.empty else 50_000.0
    formal_commitments = monthly_sal + min(open_bills, 200_000.0)

    return TotalSolvency(
        business_id=biz,
        as_of=as_of,
        bank_balance=bank_bal,
        cc_limit=cc_limit,
        cc_drawn=cc_drawn,
        galla_cash=galla_cash,
        informal_receivables=informal_recv,
        informal_payables=informal_pay,
        formal_commitments=round(formal_commitments, 2),
        haircut_alpha=haircut_alpha,
    )


def format_solvency_report(solvency: TotalSolvency) -> dict:
    """Generates a side-by-side comparison between the Bank-Only View and Dual-Plane Reality."""
    bank_headroom = solvency.net_bank_liquidity
    true_runway = solvency.true_cash_runway_inr
    
    status_headline = (
        "False Insolvency Detected: Bank alone looks stressed, but your physical cash reserves cover commitments."
        if solvency.is_false_insolvency else
        ("Solvent & Liquid: Ample working capital buffer across bank and counter cash."
         if true_runway > 0 else "Liquidity Alert: Total reserves below 30-day commitments.")
    )

    return {
        "business_id": solvency.business_id,
        "as_of": solvency.as_of.strftime("%d %b %Y"),
        "bank_balance": solvency.bank_balance,
        "net_bank_headroom": bank_headroom,
        "galla_cash": solvency.galla_cash,
        "informal_receivables_expected": solvency.total_expected_inflows,
        "total_commitments": solvency.total_commitments,
        "true_cash_runway_inr": true_runway,
        "is_false_insolvency": solvency.is_false_insolvency,
        "headline": status_headline
    }
