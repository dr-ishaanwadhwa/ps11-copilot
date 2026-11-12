"""FR-RC-1: who owes what, how long it has been open. TDS-short invoices count as paid (T3, gap L8).

v1 reads the invoice statuses as of 30 Sep 2026 from the pack, the same basis as the gold answers.
Stage 2 rebuilds this from our own reconciled ledger so it works on any date.
"""
import pandas as pd

from . import config
from .load import Pack

OPEN_STATUSES = {"OPEN", "PARTIALLY_PAID", "PENDING"}


def open_items(pack: Pack, business_id: str, as_of: pd.Timestamp = config.AS_OF) -> pd.DataFrame:
    inv = pack.invoices.drop_duplicates("invoice_no")
    inv = inv[(inv.business_id == business_id) & inv.status_as_of_30sep2026.isin(OPEN_STATUSES)].copy()
    inv["outstanding"] = (inv.invoice_total - inv.amount_received - inv.tds_deducted_by_customer
                          - inv.disallowed_amount).round(2)
    inv = inv[inv.outstanding > 0.5]
    inv["days_open"] = (as_of - inv.invoice_date).dt.days
    inv["days_overdue"] = (as_of - inv.due_date).dt.days.clip(lower=0)
    return inv[["invoice_no", "customer_name", "invoice_date", "due_date", "invoice_total", "outstanding",
                "days_open", "days_overdue", "status_as_of_30sep2026"]].sort_values("invoice_date")


def by_customer(items: pd.DataFrame) -> pd.DataFrame:
    g = items.groupby("customer_name").agg(outstanding=("outstanding", "sum"), invoices=("invoice_no", "size"),
                                           oldest_days=("days_open", "max"))
    return g.sort_values("outstanding", ascending=False).reset_index()


def overdue(items: pd.DataFrame, days: int = 60) -> pd.DataFrame:
    return items[items.days_overdue > days]


def daily_recovery_candidates(pack: Pack, business_id: str, min_days: int = 45) -> pd.DataFrame:
    """Return customer overdue summary for field collection chasing (min_days+ overdue)."""
    items = open_items(pack, business_id)
    cust = by_customer(items)
    return cust[cust.oldest_days >= min_days].copy()

