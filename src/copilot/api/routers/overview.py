"""Overview Cockpit Router (`/api/v1/overview`).

Wraps `load_pack()`, bank balance, CC headroom, vital pulse metrics, and True Solvency base equation.
Preserves ADR-001 (Zero Plaintext Cash): Server returns formal banking plane metrics;
informal drawer cash is hydrated locally in the client browser.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query
import pandas as pd

from ... import config
from ...load import Pack
from ...receivables import by_customer, open_items
from ..deps import get_business_name, get_pack, parse_as_of_date
from ..schemas import (
    CustomerReceivable,
    OverviewPayload,
    SolvencyEquation,
    VitalPulseMetric,
)

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("", response_model=OverviewPayload, response_model_by_alias=True)
def get_overview(
    biz: str = Query(default="SME-1", description="Business ID (SME-1, SME-2, SME-3)"),
    as_of: Optional[str] = Query(default=None, description="As-of cutoff date (YYYY-MM-DD)"),
    pack: Pack = Depends(get_pack),
) -> OverviewPayload:
    as_of_dt = parse_as_of_date(as_of)
    business_name = get_business_name(biz)

    # 1. Bank balance & CC headroom
    b_df = pack.bank[(pack.bank.business_id == biz) & (pack.bank.txn_date <= as_of_dt)]
    if not b_df.empty:
        last_row = b_df.sort_values(["txn_date", "seq"]).iloc[-1]
        bank_balance = float(last_row.balance_inr)
    else:
        bank_balance = 0.0

    sanctioned_limit = float(pack.credit_limit(biz))
    # CC Drawn: If bank balance is negative, that is drawn from CC facility
    cc_drawn = abs(bank_balance) if (bank_balance < 0 and sanctioned_limit > 0) else 0.0
    # CC Headroom: Available buffer in CC facility
    if sanctioned_limit > 0:
        cc_headroom = max(0.0, sanctioned_limit - cc_drawn)
    else:
        cc_headroom = 0.0

    # 2. Formal Receivables & Top Focal Action
    items = open_items(pack, biz, as_of=as_of_dt)
    formal_receivables = float(items["outstanding"].sum()) if not items.empty else 0.0
    cust_summary = by_customer(items) if not items.empty else pd.DataFrame()

    top_focal: Optional[CustomerReceivable] = None
    if not cust_summary.empty:
        # Sort by oldest_days descending to highlight urgent Section 18 / overdue chasers
        top_row = cust_summary.sort_values(["oldest_days", "outstanding"], ascending=[False, False]).iloc[0]
        top_name = str(top_row["customer_name"])
        top_out = float(top_row["outstanding"])
        top_invs = int(top_row["invoices"])
        top_days = int(top_row["oldest_days"])
        is_lim = top_days >= 900

        top_focal = CustomerReceivable(
            customerId=f"CUST-{biz}-{abs(hash(top_name)) % 100000:05d}",
            customerName=top_name,
            phone="910000000001",
            totalOutstanding=top_out,
            openInvoiceCount=top_invs,
            oldestInvoiceDays=top_days,
            isLimitationAlert=is_lim,
            hasSalesmanCollectedToday=False,
        )

    # 3. Formal Commitments (Next 30 Days Outflows: Salary + Bills)
    sal_rows = b_df[(b_df.amount < 0) & (b_df.narration.str.contains("SALARY|SAL|WAGES", case=False, na=False))]
    monthly_sal = abs(sal_rows.amount.tail(15).sum()) / 2.0 if not sal_rows.empty else 150_000.0

    bills = pack.bills[(pack.bills.business_id == biz) & (pack.bills.bill_date <= as_of_dt)]
    open_bills = float(bills.bill_total.sum() - bills.bill_total.head(len(bills) // 2).sum()) if not bills.empty else 50_000.0
    formal_due_30_days = round(monthly_sal + min(open_bills, 200_000.0), 2)

    # 4. Runway calculation (in months)
    total_spendable = max(0.0, bank_balance + cc_headroom)
    if formal_due_30_days > 0:
        runway_months = round(total_spendable / formal_due_30_days, 1)
    else:
        runway_months = 12.0

    # 5. Vital Pulse Metrics
    pulse_metrics = [
        VitalPulseMetric(
            id="bank_balance",
            label="Formal Bank Balance",
            amount=bank_balance,
            tone="positive" if bank_balance >= 0 else "critical",
            subtitle="HDFC / ICICI Current A/c",
        ),
        VitalPulseMetric(
            id="cc_headroom",
            label="Cash-Credit Headroom",
            amount=cc_headroom,
            tone="positive" if cc_headroom > 250_000 else "warning",
            subtitle=f"Limit: ₹{sanctioned_limit:,.0f}" if sanctioned_limit > 0 else "No active CC facility",
        ),
        VitalPulseMetric(
            id="formal_receivables",
            label="Formal Receivables",
            amount=formal_receivables,
            tone="neutral",
            subtitle=f"{len(items)} open sales invoices",
        ),
        VitalPulseMetric(
            id="due_next_30",
            label="Due Next 30 Days",
            amount=formal_due_30_days,
            tone="warning" if formal_due_30_days > total_spendable else "neutral",
            subtitle="Committed payroll & trade dues",
        ),
    ]

    # 6. Solvency base equation for client-side RAM hydration
    solvency_base = SolvencyEquation(
        formalBankBalance=bank_balance,
        ccFacilityDrawn=cc_drawn,
        ccFacilitySanctioned=sanctioned_limit,
        formalDueNext30Days=formal_due_30_days,
        formalReceivables=formal_receivables,
        defaultKhataRealizationRate=0.85,
    )

    return OverviewPayload(
        businessId=biz,
        businessName=business_name,
        asOfDate=as_of_dt.strftime("%Y-%m-%d"),
        bankCurrentBalance=bank_balance,
        ccSanctionedLimit=sanctioned_limit,
        ccHeadroom=cc_headroom,
        runwayMonths=runway_months,
        pulseMetrics=pulse_metrics,
        topFocalAction=top_focal,
        solvencyBase=solvency_base,
        audioBriefUrl=f"/api/v1/overview/briefing-audio?biz={biz}",
    )
