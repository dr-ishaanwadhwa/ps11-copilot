"""Customer payment delay profiles and inflow modeling (FR-FC-1, FR-FC-2; D71).

Handles:
- Customer payment delay distributions fitted from invoices paid by cutoff
- Conditional delay sampling given current invoice age
- TPA historical disallowance and TDS rates for clinic claims
- Statutory TDS deductions on open agency invoices (10% on taxable value)
- New post-cutoff invoice issuance and arrival modeling
- Non-invoice recurring receipts (clinic daily patient collections, cash deposits)
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class DelayProfile:
    customer_name: str
    count: int
    delays: np.ndarray


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


def compute_tpa_rates(
    invoices_df: pd.DataFrame, cutoff: pd.Timestamp
) -> tuple[dict[str, tuple[float, float]], tuple[float, float]]:
    """Compute historical amount-weighted disallowance and TDS rates per TPA from settled claims."""
    paid = invoices_df[
        (invoices_df.business_id == "SME-2")
        & (invoices_df.invoice_date <= cutoff)
        & invoices_df.last_payment_date.notna()
        & (invoices_df.last_payment_date <= cutoff)
    ]
    tot_all = float(paid.invoice_total.sum()) if not paid.empty else 0.0
    dis_all = float(paid.disallowed_amount.sum()) if not paid.empty else 0.0
    tds_all = float(paid.tds_deducted_by_customer.sum()) if not paid.empty else 0.0
    default_rates = (
        dis_all / tot_all if tot_all > 0 else 0.047,
        tds_all / tot_all if tot_all > 0 else 0.095,
    )

    tpa_rates: dict[str, tuple[float, float]] = {}
    if not paid.empty:
        for cust, grp in paid.groupby("customer_name"):
            tot = float(grp.invoice_total.sum())
            if tot > 0:
                tpa_rates[str(cust)] = (
                    float(grp.disallowed_amount.sum()) / tot,
                    float(grp.tds_deducted_by_customer.sum()) / tot,
                )
    return tpa_rates, default_rates


def fit_delay_distributions(
    invoices_df: pd.DataFrame,
    cutoff: pd.Timestamp,
    business_id: str,
    min_invoices: int = 5,
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Fit customer-level and business-wide payment delay arrays from invoices paid by cutoff."""
    sub = invoices_df[
        (invoices_df.business_id == business_id)
        & (invoices_df.invoice_date <= cutoff)
        & invoices_df.last_payment_date.notna()
        & (invoices_df.last_payment_date <= cutoff)
    ].copy()

    if len(sub) > 0:
        sub["delay_days"] = (sub["last_payment_date"] - sub["invoice_date"]).dt.days
        biz_delays = np.maximum(0, sub["delay_days"].values.astype(int))
    else:
        biz_delays = np.array([30], dtype=int)

    cust_delays: dict[str, np.ndarray] = {}
    if len(sub) > 0:
        for cust, grp in sub.groupby("customer_name"):
            delays = grp["delay_days"].values.astype(int)
            if len(delays) >= min_invoices:
                cust_delays[str(cust)] = np.maximum(0, delays)

    return cust_delays, biz_delays


def sample_delay_conditional(
    age: int,
    cust_delays: np.ndarray | None,
    biz_delays: np.ndarray,
    rng: np.random.Generator,
) -> int:
    """Sample invoice delay conditional on current age (D71 §2.3)."""
    if cust_delays is not None and len(cust_delays) >= 5:
        eligible = cust_delays[cust_delays > age]
        if len(eligible) > 0:
            return int(rng.choice(eligible))

    # Business-wide distribution for delays > age
    tail = biz_delays[biz_delays > age]
    if len(tail) > 0:
        return int(rng.choice(tail))

    # Residual tail of positive delays
    tail_pos = biz_delays[biz_delays > 0]
    if len(tail_pos) > 0:
        return int(age + rng.choice(tail_pos))

    return int(age + 30)


def compute_net_amount(
    row: pd.Series,
    business_id: str,
    tpa_rates: dict[str, tuple[float, float]],
    default_tpa_rates: tuple[float, float],
) -> float:
    """Compute expected net receipt for an open invoice or claim."""
    total = float(row.get("invoice_total", 0.0) or 0.0)
    taxable = float(row.get("taxable_value", 0.0) or 0.0)

    if business_id == "SME-3":
        # Agency: 10% TDS on taxable value when applicable [R3]
        tds_app = bool(row.get("tds_applicable", True))
        tds = taxable * 0.10 if tds_app else 0.0
        return max(0.0, total - tds)
    elif business_id == "SME-2":
        # Clinic: net of historical disallowance and TDS rates
        cust = str(row.get("customer_name", ""))
        dis_rate, tds_rate = tpa_rates.get(cust, default_tpa_rates)
        return max(0.0, total * (1.0 - dis_rate - tds_rate))
    return total
