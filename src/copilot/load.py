"""FR-IM-1: load the three workbooks, deduplicate, and expose them as DataFrames and DuckDB tables."""
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import pandas as pd

from . import config


@dataclass
class Pack:
    bank: pd.DataFrame            # deduplicated bank lines, file order kept in `seq`
    labels: pd.DataFrame          # category_labels (true_category is the score key, never category_bookkeeper)
    invoices: pd.DataFrame        # sales invoices and clinic TPA claims
    bills: pd.DataFrame           # purchase bills
    collections: pd.DataFrame     # clinic daily collections
    parties: pd.DataFrame
    truth: pd.DataFrame           # reconciliation_truth (answer key: used only for scoring)
    businesses: pd.DataFrame
    questions: pd.DataFrame
    cash_actuals: pd.DataFrame
    admin_log: pd.DataFrame
    duplicates_skipped: int = 0
    meta: dict = field(default_factory=dict)


def _num(df: pd.DataFrame, cols) -> pd.DataFrame:
    for c in cols:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    return df


def load_pack(data_dir: Path | None = None) -> Pack:
    d = Path(data_dir or config.DATA_DIR)
    if not d.exists():
        raise FileNotFoundError(f"Data pack not found at {d}. Set COPILOT_DATA to the folder that contains the PS-11 workbooks.")
    bank_x = pd.ExcelFile(d / config.BANK_XLSX)
    docs_x = pd.ExcelFile(d / config.DOCS_XLSX)
    eval_x = pd.ExcelFile(d / config.EVAL_XLSX)

    raw = pd.read_excel(bank_x, "bank_transactions")
    raw["seq"] = range(len(raw))
    bank = raw.drop_duplicates("txn_id", keep="first").copy()
    dupes = len(raw) - len(bank)
    bank = _num(bank, ["debit_inr", "credit_inr", "balance_inr"])
    bank["txn_date"] = pd.to_datetime(bank["txn_date"])
    bank["amount"] = bank["credit_inr"] - bank["debit_inr"]          # + money in, − money out

    inv = pd.read_excel(docs_x, "sales_invoices")
    inv = _num(inv, ["taxable_value", "cgst", "sgst", "igst", "invoice_total", "amount_received",
                     "tds_deducted_by_customer", "disallowed_amount"])
    for c in ["invoice_date", "due_date", "last_payment_date"]:
        inv[c] = pd.to_datetime(inv[c])

    bills = pd.read_excel(docs_x, "purchase_bills")
    bills = _num(bills, ["taxable_value", "bill_total", "tds_deducted_by_us"])
    for c in ["bill_date", "due_date", "paid_date"]:
        bills[c] = pd.to_datetime(bills[c])

    coll = pd.read_excel(docs_x, "daily_collections")
    coll["date"] = pd.to_datetime(coll["date"])
    coll = _num(coll, ["card_net_settled", "upi_amount", "cash_collected"])

    return Pack(
        bank=bank,
        labels=pd.read_excel(bank_x, "category_labels"),
        invoices=inv,
        bills=bills,
        collections=coll,
        parties=pd.read_excel(docs_x, "parties"),
        truth=pd.read_excel(docs_x, "reconciliation_truth"),
        businesses=pd.read_excel(bank_x, "businesses"),
        questions=pd.read_excel(eval_x, "owner_questions"),
        cash_actuals=pd.read_excel(eval_x, "monthly_cash_actuals"),
        admin_log=pd.read_excel(eval_x, "admin_time_log"),
        duplicates_skipped=dupes,
        meta={"data_dir": str(d)},
    )


def training_view(pack: Pack) -> pd.DataFrame:
    """Bank lines a forecast may train on: strictly before the frozen holdout (FR-IM-1)."""
    return pack.bank[pack.bank["txn_date"] < config.HOLDOUT_START]


def to_duckdb(pack: Pack) -> duckdb.DuckDBPyConnection:
    """Named tables for query-template answers (FR-QA-1): every answer is a query with its rows."""
    con = duckdb.connect()
    for name in ["bank", "labels", "invoices", "bills", "collections", "parties", "businesses"]:
        con.register(name, getattr(pack, name))
    return con
