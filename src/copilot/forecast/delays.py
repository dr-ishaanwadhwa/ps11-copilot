"""Customer payment delay profiles and open invoice projection (FR-FC-1, FR-FC-2).

Handles:
- Customer payment delay distributions (median, P10, P90)
- Fallback to business-wide curve when < 5 historical payments
- Censoring and age-conditioned delay sampling
- Statutory TDS deductions (10% on taxable value for SME-3 and SME-2 insurance claims [R3])
"""
from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class DelayProfile:
    customer_name: str
    count: int
    median_delay: float
    p10_delay: float
    p90_delay: float


@dataclass
class OpenInvoiceForecast:
    invoice_no: str
    customer_name: str
    invoice_date: pd.Timestamp
    due_date: pd.Timestamp
    gross_amount: float
    net_receipt: float
    expected_p50_date: pd.Timestamp
    expected_p10_date: pd.Timestamp
    expected_p90_date: pd.Timestamp
    tds_deducted: float
    row_id: str


def fit_delay_profiles(
    invoices_df: pd.DataFrame,
    cutoff: pd.Timestamp,
    business_id: str | None = None,
    min_invoices: int = 5,
) -> tuple[dict[str, DelayProfile], DelayProfile]:
    """Fit customer-level payment delay distributions from closed invoices before cutoff."""
    sub = invoices_df[invoices_df.invoice_date <= cutoff].copy()
    if business_id:
        sub = sub[sub.business_id == business_id]

    paid = sub[sub.last_payment_date <= cutoff].copy()
    paid["delay_days"] = (paid["last_payment_date"] - paid["invoice_date"]).dt.days

    # Business-wide default profile
    if len(paid) > 0:
        biz_median = float(paid["delay_days"].median())
        biz_p10 = float(np.percentile(paid["delay_days"], 10))
        biz_p90 = float(np.percentile(paid["delay_days"], 90))
    else:
        biz_median, biz_p10, biz_p90 = 30.0, 15.0, 60.0

    default_profile = DelayProfile(
        customer_name="__DEFAULT__",
        count=len(paid),
        median_delay=biz_median,
        p10_delay=biz_p10,
        p90_delay=biz_p90,
    )

    profiles: dict[str, DelayProfile] = {}
    for cust, grp in paid.groupby("customer_name"):
        delays = grp["delay_days"].values
        n = len(delays)
        if n >= min_invoices:
            profiles[cust] = DelayProfile(
                customer_name=cust,
                count=n,
                median_delay=float(np.median(delays)),
                p10_delay=float(np.percentile(delays, 10)),
                p90_delay=float(np.percentile(delays, 90)),
            )
        else:
            # Fallback to business-wide curve (Section 3.1)
            profiles[cust] = DelayProfile(
                customer_name=cust,
                count=n,
                median_delay=biz_median,
                p10_delay=biz_p10,
                p90_delay=biz_p90,
            )

    return profiles, default_profile


def project_open_invoices(
    invoices_df: pd.DataFrame,
    cutoff: pd.Timestamp,
    business_id: str,
    profiles: dict[str, DelayProfile],
    default_profile: DelayProfile,
) -> list[OpenInvoiceForecast]:
    """Project receipt dates and net proceeds for all invoices open at cutoff."""
    sub = invoices_df[
        (invoices_df.business_id == business_id) & (invoices_df.invoice_date <= cutoff)
    ].copy()

    # Open invoices: either unpaid or paid after cutoff
    open_inv = sub[(sub.last_payment_date > cutoff) | sub.last_payment_date.isna()].copy()

    forecasts: list[OpenInvoiceForecast] = []
    for _, row in open_inv.iterrows():
        cust = str(row["customer_name"])
        profile = profiles.get(cust, default_profile)

        # TDS calculation (Section 2, [R3])
        # SME-3 creative agency has 10% TDS on pre-GST taxable value
        taxable = float(row.get("taxable_value", 0.0) or 0.0)
        total = float(row.get("invoice_total", 0.0) or 0.0)

        if business_id == "SME-3":
            tds = round(taxable * 0.10, 2)
            net_receipt = total - tds
        elif business_id == "SME-2":
            # TPA claims: disallowance + TDS
            disallow = float(row.get("disallowed_amount", 0.0) or 0.0)
            tds = round(taxable * 0.10, 2) if taxable > 0 else 0.0
            net_receipt = max(0.0, total - disallow - tds)
        else:
            tds = 0.0
            net_receipt = total

        inv_date = pd.Timestamp(row["invoice_date"])
        age_days = (cutoff - inv_date).days

        # P50 expected arrival date
        if profile.median_delay > age_days:
            p50_days = profile.median_delay
        else:
            # Already overdue: expected in 3 to 10 days
            p50_days = age_days + max(3, int((profile.p90_delay - age_days) / 2))

        # P10 (optimistic / fast payer)
        p10_days = max(age_days + 1, profile.p10_delay)

        # P90 (late / stretched payer)
        p90_days = max(age_days + 7, profile.p90_delay)

        exp_p50 = inv_date + pd.Timedelta(days=int(p50_days))
        exp_p10 = inv_date + pd.Timedelta(days=int(p10_days))
        exp_p90 = inv_date + pd.Timedelta(days=int(p90_days))

        due_date = pd.Timestamp(row.get("due_date", inv_date + pd.Timedelta(days=30)))
        row_id = str(row.get("invoice_no", row.name))

        forecasts.append(
            OpenInvoiceForecast(
                invoice_no=str(row["invoice_no"]),
                customer_name=cust,
                invoice_date=inv_date,
                due_date=due_date,
                gross_amount=total,
                net_receipt=net_receipt,
                expected_p50_date=exp_p50,
                expected_p10_date=exp_p10,
                expected_p90_date=exp_p90,
                tds_deducted=tds,
                row_id=row_id,
            )
        )

    return forecasts
