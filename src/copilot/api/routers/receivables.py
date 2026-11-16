"""Receivables & Section 18 Limitation Act Router (`/api/v1/receivables`).

Wraps `open_items()` and `by_customer()` in `src/copilot/receivables.py`.
Preserves ADR-003: Flags Section 18 Limitation Act tripwires for invoices open >= 30 months (900 days),
and 45-day MSMED overdue alerts.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query

from ...load import Pack
from ...receivables import by_customer, open_items
from ..deps import get_pack, parse_as_of_date
from ..schemas import CustomerReceivable, ReceivablesPayload

router = APIRouter(prefix="/receivables", tags=["receivables"])


@router.get("", response_model=ReceivablesPayload, response_model_by_alias=True)
def get_receivables(
    biz: str = Query(default="SME-1", description="Business ID (SME-1, SME-2, SME-3)"),
    as_of: Optional[str] = Query(default=None, description="As-of cutoff date (YYYY-MM-DD)"),
    pack: Pack = Depends(get_pack),
) -> ReceivablesPayload:
    as_of_dt = parse_as_of_date(as_of)
    items = open_items(pack, biz, as_of=as_of_dt)

    if items.empty:
        return ReceivablesPayload(
            businessId=biz,
            totalOutstanding=0.0,
            overdueCount=0,
            limitationAlertCount=0,
            customers=[],
        )

    cust_summary = by_customer(items)
    total_out = float(items["outstanding"].sum())

    customers: list[CustomerReceivable] = []
    limitation_count = 0
    overdue_count = 0

    for r in cust_summary.itertuples():
        c_name = str(r.customer_name)
        c_out = float(r.outstanding)
        c_invs = int(r.invoices)
        c_days = int(r.oldest_days)

        is_lim = c_days >= 900
        if is_lim:
            limitation_count += 1
        if c_days >= 45:
            overdue_count += 1

        cust_id = f"CUST-{biz}-{abs(hash(c_name)) % 100000:05d}"

        customers.append(
            CustomerReceivable(
                customerId=cust_id,
                customerName=c_name,
                phone="910000000001",
                totalOutstanding=round(c_out, 2),
                openInvoiceCount=c_invs,
                oldestInvoiceDays=c_days,
                isLimitationAlert=is_lim,
                hasSalesmanCollectedToday=False,
                recentCollectionNote=None,
                salesmanName=None,
                collectedTodayAmount=None,
                collectedSlipId=None,
            )
        )

    return ReceivablesPayload(
        businessId=biz,
        totalOutstanding=round(total_out, 2),
        overdueCount=overdue_count,
        limitationAlertCount=limitation_count,
        customers=customers,
    )
