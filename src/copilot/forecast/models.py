"""Dataclasses and models for the 90-day cash forecast and shortfall warnings (FR-FC-1, FR-FC-2).

Decisions:
- D4 (agency inflows first)
- D6 (default floors)
- D16 (drawings aren't commitments)
- D40 (2-3 swing items per warning)
- D43 (no advice to delay payments; tax is non-movable)
- D50 (three warning triggers: credit limit headroom, salary day, owner floor)
"""
from dataclasses import dataclass, field
import pandas as pd


@dataclass
class SwingItem:
    description: str
    amount: float
    swing_amount: float
    date: pd.Timestamp
    category: str
    is_movable: bool = True
    row_ids: list[str] = field(default_factory=list)


@dataclass
class WarningCard:
    trigger_type: str  # CREDIT_LIMIT | SALARY_DAY | OWNER_FLOOR
    trigger_name: str
    level: str  # LIKELY (P50) | POSSIBLE (P10)
    warning_date: pd.Timestamp
    projected_value: float
    threshold: float
    swing_items: list[SwingItem]
    message: str


@dataclass
class DailyPoint:
    date: pd.Timestamp
    inflow_p50: float
    outflow_p50: float
    balance_p10: float
    balance_p50: float
    balance_p90: float
    headroom_p50: float = 0.0


@dataclass
class MonthlyForecast:
    month: str  # YYYY-MM
    inflows_p50: float
    outflows_p50: float
    net_p50: float
    closing_balance_p50: float
    min_balance_p50: float
    inflows_p10: float = 0.0
    inflows_p90: float = 0.0
    outflows_p10: float = 0.0
    outflows_p90: float = 0.0


@dataclass
class ForecastResult:
    business_id: str
    cutoff: pd.Timestamp
    opening_balance: float
    daily_points: list[DailyPoint]
    monthly_forecasts: list[MonthlyForecast]
    warnings: list[WarningCard]
    metadata: dict = field(default_factory=dict)
