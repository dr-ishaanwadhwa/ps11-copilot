"""Structural guard: time-cut view of the data pack (D71)."""
from dataclasses import dataclass
import numpy as np
import pandas as pd

from ..categorise import Categoriser
from ..load import Pack


@dataclass(frozen=True)
class AsOfView:
    cutoff: pd.Timestamp
    bank: pd.DataFrame
    invoices: pd.DataFrame    # invoice_date <= cutoff; post-cutoff outcomes removed
    bills: pd.DataFrame       # bill_date <= cutoff; paid_date > cutoff set to NaT, status recomputed
    collections: pd.DataFrame # date <= cutoff (clinic daily takings)
    categories: pd.DataFrame  # categoriser output for bank rows <= cutoff
    businesses: pd.DataFrame
    parties: pd.DataFrame

    def credit_limit(self, biz: str) -> float:
        from ..load import get_credit_limit
        return get_credit_limit(self.businesses, biz)


def as_of(pack: Pack, cutoff: pd.Timestamp) -> AsOfView:
    """Build an AsOfView strictly containing data available up to cutoff."""
    bank = pack.bank[pack.bank.txn_date <= cutoff].copy()

    inv = pack.invoices[pack.invoices.invoice_date <= cutoff].copy()
    unpaid_mask = inv["last_payment_date"].isna() | (inv["last_payment_date"] > cutoff)
    inv.loc[inv["last_payment_date"] > cutoff, "last_payment_date"] = pd.NaT
    inv.loc[unpaid_mask, "amount_received"] = 0.0
    inv.loc[unpaid_mask, "status_as_of_30sep2026"] = np.nan
    inv.loc[unpaid_mask, "disallowed_amount"] = np.nan
    inv.loc[unpaid_mask, "tds_deducted_by_customer"] = np.nan

    bills = pack.bills[pack.bills.bill_date <= cutoff].copy()
    bills.loc[bills["paid_date"] > cutoff, "paid_date"] = pd.NaT
    if "payment_status" in bills.columns:
        bills["payment_status"] = np.where(bills["paid_date"].isna(), "UNPAID", "PAID")

    if hasattr(pack, "collections") and pack.collections is not None and not pack.collections.empty:
        collections = pack.collections[pack.collections.date <= cutoff].copy()
    else:
        collections = pd.DataFrame()

    categoriser = Categoriser(pack, train_before=cutoff)
    categories = categoriser.apply(bank)

    businesses = pack.businesses.copy()
    parties = pack.parties.copy()

    return AsOfView(
        cutoff=cutoff,
        bank=bank,
        invoices=inv,
        bills=bills,
        collections=collections,
        categories=categories,
        businesses=businesses,
        parties=parties,
    )
