"""Calendar balance forecast: the owner's bank balance for the next 30 to 90 days.

Why this exists: replaying the Monte Carlo engine from past start dates showed its *balance* path drifting far
from what happened (for the distributor it predicted Rs 40-49 lakh while the real balance stayed at Rs 11-21
lakh), and its P10-P90 band caught the real balance in only 3 of 18 checks. Its monthly inflow/outflow totals
score well, but the balance an owner reads did not.

This model is deliberately simple and checkable. From the start date it uses only data up to that date:

1. Today's balance is the anchor.
2. The business's own month shape: the average net cash flow on each day of the month over the last six
   months (salaries on the 1st, GST on the 20th, collection days), centred so it adds no drift by itself.
3. A slow pull back toward the six-month average balance (half-way in 90 days), because these balances
   swing around a level rather than trending away.
4. A likely range taken from how wrong this same method was when replayed weekly on the business's own
   past (10th and 90th percentile of those errors at each horizon), so the range is earned, not assumed.

What-ifs act on top of the point path: customers paying N days late (N days of typical receipts arrive after
the window), a sales change (typical receipts scaled), and a one-off payment on a chosen date.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..load import Pack

HALF_LIFE_DAYS = 90
SHAPE_MONTHS = 6
MAX_HORIZON = 90


@dataclass
class CalendarPoint:
    date: pd.Timestamp
    p10: float
    p50: float
    p90: float
    actual: float | None = None


@dataclass
class CalendarForecast:
    business_id: str
    start: pd.Timestamp
    horizon: int
    opening_balance: float
    credit_limit: float
    points: list[CalendarPoint]
    backtest_runs: int                     # how many past replays the range is built from
    typical_daily_receipts: float
    accuracy: dict = field(default_factory=dict)   # filled when actual balances exist inside the window

    @property
    def lowest(self) -> CalendarPoint:
        return min(self.points, key=lambda p: p.p50)

    @property
    def has_actuals(self) -> bool:
        return any(p.actual is not None for p in self.points)


def daily_series(pack: Pack, business_id: str) -> tuple[pd.Series, pd.Series]:
    """Calendar-day net flow and end-of-day balance (balance carried over days with no entries)."""
    b = pack.bank[pack.bank.business_id == business_id].sort_values(["txn_date", "seq"])
    days = pd.date_range(b.txn_date.min().normalize(), b.txn_date.max().normalize())
    day = b.txn_date.dt.normalize()
    net = b.groupby(day).amount.sum().reindex(days, fill_value=0.0)
    bal = b.groupby(day).balance_inr.last().reindex(days).ffill()
    return net, bal


def _point_path(net: pd.Series, bal: pd.Series, start: pd.Timestamp, horizon: int) -> np.ndarray:
    hist_net = net[(net.index > start - pd.DateOffset(months=SHAPE_MONTHS)) & (net.index <= start)]
    shape = hist_net.groupby(hist_net.index.day).mean()
    shape = shape - shape.mean()
    future = pd.date_range(start + pd.Timedelta(days=1), periods=horizon)
    seasonal = np.cumsum([float(shape.get(d.day, 0.0)) for d in future])
    hist_bal = bal[(bal.index > start - pd.DateOffset(months=SHAPE_MONTHS)) & (bal.index <= start)]
    level = float(hist_bal.mean())
    b0 = float(bal[:start].iloc[-1])
    decay = 0.5 ** (np.arange(1, horizon + 1) / HALF_LIFE_DAYS)
    return level + (b0 - level) * decay + seasonal


def _past_errors(net: pd.Series, bal: pd.Series, start: pd.Timestamp, horizon: int) -> np.ndarray | None:
    """Replay the method weekly on the business's own past (only data before `start`) and keep its errors."""
    first = bal.index.min() + pd.DateOffset(months=2)
    runs = []
    for c in pd.date_range(first, start - pd.Timedelta(days=horizon), freq="7D"):
        actual = bal[c + pd.Timedelta(days=1): c + pd.Timedelta(days=horizon)].to_numpy()
        if len(actual) == horizon:
            runs.append(actual - _point_path(net, bal, c, horizon))
    return np.vstack(runs) if len(runs) >= 4 else None


def calendar_forecast(
    pack: Pack,
    business_id: str,
    start: pd.Timestamp,
    horizon: int = 90,
    receipt_delay_days: int = 0,
    sales_change_pct: float = 0.0,
    one_off_amount: float = 0.0,
    one_off_date: pd.Timestamp | None = None,
) -> CalendarForecast:
    horizon = int(max(7, min(MAX_HORIZON, horizon)))
    net, bal = daily_series(pack, business_id)
    start = pd.Timestamp(start).normalize()
    start = min(max(start, bal.index.min() + pd.DateOffset(months=2)), bal.index.max())

    path = _point_path(net, bal, start, horizon)
    errors = _past_errors(net, bal, start, horizon)
    if errors is not None:
        lo, hi = np.percentile(errors, 10, axis=0), np.percentile(errors, 90, axis=0)
    else:  # too little history: a plain widening range, said as such by backtest_runs == 0
        spread = np.std(np.diff(bal[:start].to_numpy()[-180:])) * np.sqrt(np.arange(1, horizon + 1))
        lo, hi = -1.28 * spread, 1.28 * spread

    # What-ifs, measured against the business's typical daily receipts over the last 90 days.
    b = pack.bank[(pack.bank.business_id == business_id) & (pack.bank.txn_date <= start)]
    recent = b[(b.txn_date > start - pd.Timedelta(days=90)) & (b.amount > 0)]
    typical_in = float(recent.amount.sum()) / 90.0
    k = np.arange(1, horizon + 1)
    adjust = np.zeros(horizon)
    if receipt_delay_days:
        adjust -= typical_in * np.minimum(k, receipt_delay_days)
    if sales_change_pct:
        adjust += typical_in * (sales_change_pct / 100.0) * k
    future = pd.date_range(start + pd.Timedelta(days=1), periods=horizon)
    if one_off_amount and one_off_date is not None:
        adjust -= np.where(future >= pd.Timestamp(one_off_date).normalize(), one_off_amount, 0.0)
    path = path + adjust

    points = []
    for i, d in enumerate(future):
        actual = float(bal[d]) if d in bal.index and d <= bal.index.max() else None
        points.append(CalendarPoint(date=d, p10=float(path[i] + lo[i]), p50=float(path[i]),
                                    p90=float(path[i] + hi[i]), actual=actual))

    fc = CalendarForecast(
        business_id=business_id, start=start, horizon=horizon, opening_balance=float(bal[:start].iloc[-1]),
        credit_limit=float(pack.credit_limit(business_id) or 0.0), points=points,
        backtest_runs=0 if errors is None else len(errors), typical_daily_receipts=typical_in,
    )
    with_actual = [p for p in points if p.actual is not None]
    if with_actual and not (receipt_delay_days or sales_change_pct or one_off_amount):
        err = np.array([abs(p.p50 - p.actual) for p in with_actual])
        flat = np.array([abs(fc.opening_balance - p.actual) for p in with_actual])
        inside = np.mean([p.p10 <= p.actual <= p.p90 for p in with_actual])
        fc.accuracy = {"days": len(with_actual), "avg_error": float(err.mean()), "flat_error": float(flat.mean()),
                       "inside_range": float(inside), "end_error": float(err[-1])}
    return fc
