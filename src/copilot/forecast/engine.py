"""Bottom-up daily cash flow simulation engine (FR-FC-1, FR-FC-2; D71).

Simulates daily cash trajectory for 90 days following cutoff date:
- Bottom-up invoice arrival based on customer payment delay distributions
- Age-conditioned delay sampling (Task 2.3)
- Statutory TDS deductions and TPA historical disallowance rates
- Outflows derived strictly from pre-cutoff 3-month medians and recurring payees (Task 2.4)
- Monte Carlo sampling across n_paths paths (Task 2.5)
- Warning triggers and swing items computed on simulated paths
"""
import re
import numpy as np
import pandas as pd

from .. import config
from ..categorise import payee_key
from .asof import AsOfView, as_of
from .delays import (
    compute_net_amount,
    compute_tpa_rates,
    fit_delay_distributions,
    sample_delay_conditional,
)
from .models import DailyPoint, ForecastResult, MonthlyForecast, SwingItem
from .warnings import evaluate_warnings


def roll_sunday_to_monday(dt: pd.Timestamp) -> pd.Timestamp:
    """Statutory dates falling on Sunday roll to Monday [S1]."""
    if dt.dayofweek == 6:  # Sunday
        return dt + pd.Timedelta(days=1)
    return dt


def get_credit_limit(view: AsOfView, business_id: str) -> float:
    """Extract credit limit from business bank account description."""
    try:
        row = view.businesses.set_index("business_id").loc[business_id]
        acct = str(row.get("bank_account", ""))
        m = re.search(r"limit ₹([\d,]+)", acct)
        return float(m.group(1).replace(",", "")) if m else 0.0
    except Exception:
        return 0.0


def simulate_forecast(
    view: AsOfView,
    business_id: str,
    n_paths: int = 1000,
    seed: int = 0,
    owner_floor: float = 0.0,
) -> ForecastResult:
    """Run bottom-up daily cash flow simulation for 90 days from cutoff (strictly <= cutoff data)."""
    cutoff = view.cutoff
    rng = np.random.default_rng(seed)

    # 1. Opening balance strictly before or on cutoff
    bank = view.bank[view.bank.business_id == business_id]
    if len(bank) == 0:
        opening_bal = 0.0
    else:
        last_row = bank.sort_values(["txn_date", "seq"]).iloc[-1]
        opening_bal = float(last_row.balance_inr)

    credit_limit = get_credit_limit(view, business_id)

    # Timeline: 90 days after cutoff
    n_days = 90
    dates = [cutoff + pd.Timedelta(days=i) for i in range(1, n_days + 1)]
    date_to_idx = {d: i for i, d in enumerate(dates)}
    months = sorted(list({d.strftime("%Y-%m") for d in dates}))

    # 2. Outflows derived bottom-up from pre-cutoff categories (Task 2.4)
    b_cat = view.categories[view.categories.business_id == business_id]
    start_3m = cutoff - pd.DateOffset(months=3)
    start_6m = cutoff - pd.DateOffset(months=6)
    start_90d = cutoff - pd.Timedelta(days=90)

    # 2a. Salary: median monthly total in 3 months before cutoff; most common day
    b_3m = b_cat[(b_cat.txn_date > start_3m) & (b_cat.txn_date <= cutoff)]
    sal_rows = b_3m[b_3m.category == "Salary"]
    if not sal_rows.empty:
        sal_m = sal_rows.groupby(sal_rows.txn_date.dt.to_period("M")).amount.sum().abs()
        monthly_sal = float(sal_m.median())
        sal_day = int(sal_rows.txn_date.dt.day.value_counts().index[0])
    else:
        monthly_sal, sal_day = 0.0, 1

    # 2b. Statutory: GST on 20th and TDS on 7th; median of each over 3 months
    gst_rows = b_3m[b_3m.category == "GST payment"]
    gst_amt = float(gst_rows.groupby(gst_rows.txn_date.dt.to_period("M")).amount.sum().abs().median()) if not gst_rows.empty else 0.0
    tds_rows = b_3m[b_3m.category == "TDS deposited"]
    tds_amt = float(tds_rows.groupby(tds_rows.txn_date.dt.to_period("M")).amount.sum().abs().median()) if not tds_rows.empty else 0.0

    # 2c. Owner drawings: median monthly total over 3 months before cutoff, most common day
    drw_rows = b_3m[b_3m.category == "Owner drawings"]
    if not drw_rows.empty:
        drw_amt = float(drw_rows.groupby(drw_rows.txn_date.dt.to_period("M")).amount.sum().abs().median())
        drw_day = int(drw_rows.txn_date.dt.day.value_counts().index[0])
    else:
        drw_amt, drw_day = 0.0, 1

    # 2d. Recurring payees: >= 4 of 6 months, amount CV <= 0.25
    b_6m = b_cat[(b_cat.txn_date > start_6m) & (b_cat.txn_date <= cutoff) & (b_cat.amount < 0)].copy()
    b_6m["payee"] = b_6m["narration"].apply(payee_key)
    b_6m["m_period"] = b_6m["txn_date"].dt.to_period("M")
    candidates = b_6m[~b_6m.category.isin(["Salary", "GST payment", "TDS deposited", "Owner drawings"])]
    recurring: list[dict] = []
    for p, grp in candidates.groupby("payee"):
        if grp["m_period"].nunique() >= 4:
            amts = grp["amount"].abs().values
            mean_a = float(np.mean(amts))
            std_a = float(np.std(amts))
            cv = std_a / mean_a if mean_a > 0 else 1.0
            if cv <= 0.25:
                recurring.append({
                    "payee": p,
                    "amount": float(np.median(amts)),
                    "day": int(grp["txn_date"].dt.day.median()),
                })
    rec_payee_names = {r["payee"] for r in recurring}

    # 2e. Supplier bills open at cutoff
    bills_biz = view.bills[view.bills.business_id == business_id]
    paid_b = bills_biz[bills_biz.paid_date.notna()]
    if not paid_b.empty:
        lags = (paid_b.paid_date - paid_b.due_date).dt.days
        median_lag = float(lags.median())
    else:
        median_lag = 0.0
    open_bills = bills_biz[bills_biz.paid_date.isna()]
    bill_outflows: dict[pd.Timestamp, float] = {}
    for r in open_bills.itertuples():
        p_date = r.due_date + pd.Timedelta(days=int(median_lag))
        bill_outflows[p_date] = bill_outflows.get(p_date, 0.0) + float(r.bill_total)

    # 2f. Residual daily outflow over 90 days before cutoff
    b_90d = b_cat[(b_cat.txn_date > start_90d) & (b_cat.txn_date <= cutoff) & (b_cat.amount < 0)].copy()
    b_90d["payee"] = b_90d["narration"].apply(payee_key)
    rem = b_90d[~b_90d.category.isin(["Salary", "GST payment", "TDS deposited", "Owner drawings"]) & (~b_90d.payee.isin(rec_payee_names))]
    daily_residual = float(rem.amount.abs().sum()) / 90.0

    # Build base daily outflow schedule
    base_daily_outflow = np.zeros(n_days)
    salary_dates: list[pd.Timestamp] = []
    for idx, d in enumerate(dates):
        base_daily_outflow[idx] += daily_residual
        if d in bill_outflows:
            base_daily_outflow[idx] += bill_outflows[d]
        if d.day == sal_day:
            sal_d = roll_sunday_to_monday(d)
            if sal_d in date_to_idx:
                base_daily_outflow[date_to_idx[sal_d]] += monthly_sal
                if sal_d not in salary_dates:
                    salary_dates.append(sal_d)
        if d.day == 20:
            gst_d = roll_sunday_to_monday(d)
            if gst_d in date_to_idx:
                base_daily_outflow[date_to_idx[gst_d]] += gst_amt
        if d.day == 7:
            tds_d = roll_sunday_to_monday(d)
            if tds_d in date_to_idx:
                base_daily_outflow[date_to_idx[tds_d]] += tds_amt
        if d.day == drw_day:
            drw_d = roll_sunday_to_monday(d)
            if drw_d in date_to_idx:
                base_daily_outflow[date_to_idx[drw_d]] += drw_amt
        for rp in recurring:
            if d.day == rp["day"]:
                rp_d = roll_sunday_to_monday(d)
                if rp_d in date_to_idx:
                    base_daily_outflow[date_to_idx[rp_d]] += rp["amount"]

    # 3. Inflow modeling (Task 2.3)
    inv_biz = view.invoices[view.invoices.business_id == business_id]
    tpa_rates, def_tpa = compute_tpa_rates(view.invoices, cutoff)
    cust_delays, biz_delays = fit_delay_distributions(view.invoices, cutoff, business_id)

    # 3a. Open invoices at cutoff
    open_inv = inv_biz[inv_biz.last_payment_date.isna()].copy()
    open_items: list[dict] = []
    candidate_swings: list[SwingItem] = []

    for r in open_inv.itertuples():
        age = (cutoff - r.invoice_date).days
        net_amt = compute_net_amount(pd.Series(r._asdict()), business_id, tpa_rates, def_tpa)
        open_items.append({
            "invoice_date": r.invoice_date,
            "customer": r.customer_name,
            "age": age,
            "net": net_amt,
            "invoice_no": str(r.invoice_no),
        })

        # Calculate approximate P50 and P90 arrival dates for swing item candidates
        cd = cust_delays.get(r.customer_name)
        eligible = cd[cd > age] if cd is not None else np.array([])
        p50_lag = int(np.median(eligible)) if len(eligible) > 0 else (int(np.median(biz_delays[biz_delays > age])) if len(biz_delays[biz_delays > age]) > 0 else age + 30)
        p90_lag = int(np.percentile(eligible, 90)) if len(eligible) > 0 else (int(np.percentile(biz_delays[biz_delays > age], 90)) if len(biz_delays[biz_delays > age]) > 0 else age + 45)

        candidate_swings.append(
            SwingItem(
                description=f"{r.customer_name}'s invoice",
                amount=net_amt,
                swing_amount=net_amt if p90_lag > p50_lag else 0.0,
                date=r.invoice_date + pd.Timedelta(days=p50_lag),
                category="Receipt",
                is_movable=True,
                row_ids=[str(r.invoice_no)],
            )
        )

    # 3b. New invoices raised post-cutoff
    inv_90 = inv_biz[(inv_biz.invoice_date > start_90d) & (inv_biz.invoice_date <= cutoff)]
    tot_90 = float(inv_90.invoice_total.sum())
    weekday_totals = inv_90.groupby(inv_90.invoice_date.dt.dayofweek).invoice_total.sum()
    weekday_shares = {w: float(weekday_totals.get(w, 0.0)) / tot_90 if tot_90 > 0 else 1.0 / 7.0 for w in range(7)}

    # 3c. Non-invoice credits over 8 weeks
    start_8w = cutoff - pd.Timedelta(weeks=8)
    b_8w = b_cat[(b_cat.txn_date > start_8w) & (b_cat.txn_date <= cutoff) & (b_cat.amount > 0)]
    biz_profile = config.get_profile(business_id)
    non_inv = b_8w[~b_8w.category.isin([biz_profile.primary_receipt_category, "Capital infusion"])]
    daily_credits = non_inv.groupby("txn_date").amount.sum()
    all_8w_dates = pd.date_range(start_8w + pd.Timedelta(days=1), cutoff)
    daily_credits = daily_credits.reindex(all_8w_dates, fill_value=0.0)
    non_inv_weekday_mean = daily_credits.groupby(daily_credits.index.dayofweek).mean().to_dict()

    # 4. Monte Carlo Simulation (Task 2.5)
    sim_in = np.zeros((n_paths, n_days))
    sim_out = np.zeros((n_paths, n_days))

    for p in range(n_paths):
        sim_out[p, :] = base_daily_outflow.copy()

        # Non-invoice credits
        for idx, d in enumerate(dates):
            sim_in[p, idx] += non_inv_weekday_mean.get(d.dayofweek, 0.0)

        # Open invoices
        for item in open_items:
            age = item["age"]
            c = item["customer"]
            del_draw = sample_delay_conditional(age, cust_delays.get(c), biz_delays, rng)
            arr = item["invoice_date"] + pd.Timedelta(days=del_draw)
            if arr in date_to_idx:
                sim_in[p, date_to_idx[arr]] += item["net"]

        # New invoices
        for idx, d in enumerate(dates):
            iss_amt = (tot_90 / 90.0) * 7.0 * weekday_shares[d.dayofweek]
            if biz_profile.has_tds:
                iss_net = iss_amt * (1.0 - config.TDS_RATE)
            elif biz_profile.archetype == "clinic":
                iss_net = iss_amt * (1.0 - def_tpa[0] - def_tpa[1])
            else:
                iss_net = iss_amt
            del_draw = int(rng.choice(biz_delays)) if len(biz_delays) > 0 else 30
            arr = d + pd.Timedelta(days=del_draw)
            if arr in date_to_idx:
                sim_in[p, date_to_idx[arr]] += iss_net

    # 5. Daily Aggregation & Paths
    sim_balance = np.zeros((n_paths, n_days))
    running_bal = np.full(n_paths, opening_bal)
    for idx in range(n_days):
        running_bal += sim_in[:, idx] - sim_out[:, idx]
        sim_balance[:, idx] = running_bal.copy()

    daily_points: list[DailyPoint] = []
    for idx, d in enumerate(dates):
        inf_p50 = float(np.percentile(sim_in[:, idx], 50))
        out_p50 = float(np.percentile(sim_out[:, idx], 50))
        b_p10 = float(np.percentile(sim_balance[:, idx], 10))
        b_p50 = float(np.percentile(sim_balance[:, idx], 50))
        b_p90 = float(np.percentile(sim_balance[:, idx], 90))
        daily_points.append(
            DailyPoint(
                date=d,
                inflow_p50=inf_p50,
                outflow_p50=out_p50,
                balance_p10=b_p10,
                balance_p50=b_p50,
                balance_p90=b_p90,
                headroom_p50=credit_limit + b_p50 if credit_limit > 0 else 0.0,
            )
        )

    # 6. Monthly Forecasts
    monthly_forecasts: list[MonthlyForecast] = []
    for m in months:
        m_indices = [i for i, d in enumerate(dates) if d.strftime("%Y-%m") == m]
        if not m_indices:
            continue
        m_inf_paths = sim_in[:, m_indices].sum(axis=1)
        m_out_paths = sim_out[:, m_indices].sum(axis=1)
        m_net_paths = m_inf_paths - m_out_paths

        inf_p10 = float(np.percentile(m_inf_paths, 10))
        inf_p50 = float(np.percentile(m_inf_paths, 50))
        inf_p90 = float(np.percentile(m_inf_paths, 90))

        out_p10 = float(np.percentile(m_out_paths, 10))
        out_p50 = float(np.percentile(m_out_paths, 50))
        out_p90 = float(np.percentile(m_out_paths, 90))

        last_day_idx = m_indices[-1]
        close_p50 = float(np.percentile(sim_balance[:, last_day_idx], 50))
        min_p50 = float(min(np.percentile(sim_balance[:, i], 50) for i in m_indices))

        monthly_forecasts.append(
            MonthlyForecast(
                month=m,
                inflows_p50=inf_p50,
                outflows_p50=out_p50,
                net_p50=inf_p50 - out_p50,
                closing_balance_p50=close_p50,
                min_balance_p50=min_p50,
                inflows_p10=inf_p10,
                inflows_p90=inf_p90,
                outflows_p10=out_p10,
                outflows_p90=out_p90,
            )
        )

    # 7. Evaluate Warnings (Task 2.5)
    warnings = evaluate_warnings(
        daily_points=daily_points,
        candidate_swings=candidate_swings,
        salary_amount=monthly_sal,
        salary_dates=salary_dates,
        credit_limit=credit_limit,
        credit_headroom_floor=250_000.0,
        owner_floor=owner_floor,
    )

    return ForecastResult(
        business_id=business_id,
        cutoff=cutoff,
        opening_balance=opening_bal,
        daily_points=daily_points,
        monthly_forecasts=monthly_forecasts,
        warnings=warnings,
    )


class CashForecastSimulator:
    """Deep module encapsulating time-slicing, categoriser caching, delay modeling, and Monte Carlo simulation."""

    def __init__(self, pack):
        self.pack = pack
        self._view_cache: dict[pd.Timestamp, AsOfView] = {}

    def get_view(self, cutoff: pd.Timestamp) -> AsOfView:
        """Retrieve or build a strictly time-cut AsOfView for a cutoff date."""
        if cutoff not in self._view_cache:
            self._view_cache[cutoff] = as_of(self.pack, cutoff)
        return self._view_cache[cutoff]

    def simulate(
        self,
        business_id: str,
        cutoff: pd.Timestamp = config.AS_OF,
        n_paths: int = 1000,
        seed: int = 0,
        owner_floor: float = 0.0,
    ) -> ForecastResult:
        """Run bottom-up Monte Carlo cash forecast from a cutoff date."""
        view = self.get_view(cutoff)
        return simulate_forecast(
            view=view,
            business_id=business_id,
            n_paths=n_paths,
            seed=seed,
            owner_floor=owner_floor,
        )

