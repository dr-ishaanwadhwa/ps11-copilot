"""Shared dependencies and domain service singletons for FastAPI microservice."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional
import pandas as pd

from .. import config
from ..load import Pack, load_pack
from ..forecast.engine import CashForecastSimulator
from ..match.engine import Matcher, match_all
from ..match.audit import AuditLedger


@lru_cache(maxsize=1)
def get_pack() -> Pack:
    """Retrieve shared Pack singleton."""
    return load_pack()


@lru_cache(maxsize=1)
def get_forecast_simulator() -> CashForecastSimulator:
    """Retrieve shared CashForecastSimulator singleton."""
    return CashForecastSimulator(get_pack())


@lru_cache(maxsize=1)
def get_audit_ledger() -> AuditLedger:
    """Retrieve shared AuditLedger singleton."""
    return AuditLedger(config.STATE_DIR)


def get_business_name(biz: str) -> str:
    """Resolve authentic business name for an SME identifier."""
    return config.BUSINESSES.get(biz, f"Business-{biz}")


def parse_as_of_date(as_of: Optional[str]) -> pd.Timestamp:
    """Parse as_of query parameter or default to config.AS_OF."""
    if not as_of:
        return config.AS_OF
    try:
        return pd.Timestamp(as_of)
    except Exception:
        return config.AS_OF
