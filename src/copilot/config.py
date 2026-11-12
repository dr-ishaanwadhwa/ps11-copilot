"""Paths and fixed dates. Default data directory is the repo's data/ folder (D72)."""
import os
from pathlib import Path

import pandas as pd

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR = Path(os.environ.get("COPILOT_DATA", DEFAULT_DATA_DIR))

DEFAULT_STATE_DIR = Path(__file__).resolve().parent.parent.parent / ".copilot_state"
STATE_DIR = Path(os.environ.get("COPILOT_STATE_DIR", DEFAULT_STATE_DIR))

BANK_XLSX = "PS-11_bank_statements.xlsx"
DOCS_XLSX = "PS-11_invoices_and_reconciliation.xlsx"
EVAL_XLSX = "PS-11_copilot_evaluation.xlsx"

HOLDOUT_START = pd.Timestamp("2026-07-01")  # forecasts train on data before this date only
AS_OF = pd.Timestamp("2026-09-30")          # invoice statuses in the pack are as of this date

BUSINESSES = {"SME-1": "Kaveri Distributors", "SME-2": "SmileArc Dental Clinic", "SME-3": "Northlight Design Studio"}


from dataclasses import dataclass


@dataclass(frozen=True)
class BusinessProfile:
    business_id: str
    name: str
    archetype: str              # "distributor", "clinic", "agency"
    doc_kinds: tuple[str, ...]  # ("inv",) or ("claim",)
    batch_rule_name: str        # "CLUBBED" or "TPA_BATCH"
    max_batch_size: int         # 6 or 13
    has_tds: bool               # True for agency (Section 194J)
    has_daily_collections: bool # True for clinic (dc_id) and distributor (salesmen)
    has_round_off: bool         # True for distributor kirana roundoffs
    primary_receipt_category: str
    median_delay: float
    p90_delay: float


BUSINESS_PROFILES: dict[str, BusinessProfile] = {
    "SME-1": BusinessProfile(
        business_id="SME-1",
        name="Kaveri Distributors",
        archetype="distributor",
        doc_kinds=("inv",),
        batch_rule_name="CLUBBED",
        max_batch_size=6,
        has_tds=False,
        has_daily_collections=True,
        has_round_off=True,
        primary_receipt_category="Sales receipt — customer",
        median_delay=28.0,
        p90_delay=45.0,
    ),
    "SME-2": BusinessProfile(
        business_id="SME-2",
        name="SmileArc Dental Clinic",
        archetype="clinic",
        doc_kinds=("claim",),
        batch_rule_name="TPA_BATCH",
        max_batch_size=13,
        has_tds=False,
        has_daily_collections=True,
        has_round_off=False,
        primary_receipt_category="Insurance/TPA receipt",
        median_delay=42.0,
        p90_delay=70.0,
    ),
    "SME-3": BusinessProfile(
        business_id="SME-3",
        name="Northlight Design Studio",
        archetype="agency",
        doc_kinds=("inv",),
        batch_rule_name="CLUBBED",
        max_batch_size=6,
        has_tds=True,
        has_daily_collections=False,
        has_round_off=False,
        primary_receipt_category="Sales receipt — customer",
        median_delay=25.0,
        p90_delay=45.0,
    ),
}


def get_profile(biz: str) -> BusinessProfile:
    """Retrieve domain profile for a business, falling back to a safe generic profile."""
    return BUSINESS_PROFILES.get(
        biz,
        BusinessProfile(
            business_id=biz,
            name=BUSINESSES.get(biz, biz),
            archetype="generic",
            doc_kinds=("inv",),
            batch_rule_name="CLUBBED",
            max_batch_size=6,
            has_tds=False,
            has_daily_collections=False,
            has_round_off=False,
            primary_receipt_category="Sales receipt — customer",
            median_delay=30.0,
            p90_delay=60.0,
        ),
    )

TDS_RATE = 0.10          # guide s.4: TDS is 10% of the value before GST
ROUND_OFF_MAX = 100.0    # guide s.5: UPI round-offs under ₹100
BOUNCE_WINDOW_DAYS = 2   # every bounce in the pack reverses within 2 days [R7]
KHATA_COLLECTION_ASSUMPTION = 0.85  # default recovery assumption on informal receivables
