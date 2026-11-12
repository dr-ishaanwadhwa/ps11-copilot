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

TDS_RATE = 0.10          # guide s.4: TDS is 10% of the value before GST
ROUND_OFF_MAX = 100.0    # guide s.5: UPI round-offs under ₹100
BOUNCE_WINDOW_DAYS = 2   # every bounce in the pack reverses within 2 days [R7]
