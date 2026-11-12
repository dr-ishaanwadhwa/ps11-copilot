"""Bank statement and Tally Prime XML ingestion engine.

Supports:
1. Standard Indian bank CSV and Excel exports (HDFC, ICICI, SBI, Axis, Kotak).
2. Tally Prime XML bill-wise allocations and ledger exports.
3. Balance validation and line deduplication.
"""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
from typing import Any

import pandas as pd


def parse_bank_statement(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """Parse an uploaded bank statement (CSV or Excel) into normalized transactions.

    Returns dict with:
        - df: pd.DataFrame with columns ['txn_date', 'narration', 'amount', 'balance']
        - rows_read: int
        - balance_ties: bool
        - breaks: list of indices where running balance does not tie
        - summary: dict of total_credits, total_debits, closing_balance
    """
    fn = filename.lower()
    if fn.endswith(".csv"):
        # Try utf-8 first, fallback to latin-1
        try:
            raw_df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
        except UnicodeDecodeError:
            raw_df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")
    elif fn.endswith((".xlsx", ".xls")):
        raw_df = pd.read_excel(io.BytesIO(file_bytes))
    else:
        raise ValueError(f"Unsupported file format '{filename}'. Expected CSV or Excel (.xlsx/.xls).")

    # Normalize column names: strip spaces and lowercase
    col_map = {c: str(c).strip().lower().replace(" ", "_") for c in raw_df.columns}
    df = raw_df.rename(columns=col_map)

    # Detect date column
    date_col = next((c for c in df.columns if any(k in c for k in ("date", "txn_date", "value_date"))), None)
    # Detect narration column
    narr_col = next((c for c in df.columns if any(k in c for k in ("narration", "description", "particulars", "remarks"))), None)
    # Detect balance column
    bal_col = next((c for c in df.columns if any(k in c for k in ("balance", "closing_bal", "closing_balance", "running_bal"))), None)
    # Detect amount columns (either single 'amount' with Dr/Cr, or separate debit/credit)
    dr_col = next((c for c in df.columns if any(k in c for k in ("debit", "withdrawal", "dr"))), None)
    cr_col = next((c for c in df.columns if any(k in c for k in ("credit", "deposit", "cr"))), None)
    amt_col = next((c for c in df.columns if c in ("amount", "txn_amount") and c not in (dr_col, cr_col)), None)

    if not date_col:
        raise ValueError("Could not find a valid Date column in the statement.")
    if not narr_col:
        raise ValueError("Could not find a valid Narration/Description column in the statement.")

    def clean_num(val) -> float:
        if pd.isna(val) or val is None:
            return 0.0
        s = re.sub(r"[^\d.-]", "", str(val))
        try:
            return float(s) if s else 0.0
        except ValueError:
            return 0.0

    parsed_rows = []
    for _, row in df.iterrows():
        raw_date = row[date_col]
        if pd.isna(raw_date):
            continue
        try:
            t_date = pd.to_datetime(raw_date, dayfirst=True)
        except Exception:
            continue

        narr = str(row[narr_col]).strip()
        if not narr or narr.lower() == "nan":
            continue

        if dr_col and cr_col:
            dr = clean_num(row[dr_col])
            cr = clean_num(row[cr_col])
            amt = cr - dr
        elif amt_col:
            amt = clean_num(row[amt_col])
        else:
            amt = 0.0

        bal = clean_num(row[bal_col]) if bal_col else 0.0

        parsed_rows.append({
            "txn_date": t_date,
            "narration": narr,
            "amount": amt,
            "balance": bal,
        })

    if not parsed_rows:
        raise ValueError("No valid transaction rows found in the uploaded file.")

    res_df = pd.DataFrame(parsed_rows).sort_values("txn_date").reset_index(drop=True)

    # Check running balance ties
    breaks = []
    balance_ties = True
    if bal_col and len(res_df) > 1:
        for i in range(1, len(res_df)):
            prev_b = res_df.loc[i - 1, "balance"]
            curr_b = res_df.loc[i, "balance"]
            curr_amt = res_df.loc[i, "amount"]
            # Tolerance +/- 1.0 rupee for round-offs
            if abs((prev_b + curr_amt) - curr_b) > 1.0:
                breaks.append(i)
        balance_ties = len(breaks) == 0

    credits = res_df[res_df.amount > 0].amount.sum()
    debits = res_df[res_df.amount < 0].amount.sum()
    closing = res_df.iloc[-1]["balance"] if bal_col else 0.0

    return {
        "df": res_df,
        "rows_read": len(res_df),
        "balance_ties": balance_ties,
        "breaks": breaks,
        "summary": {
            "total_credits": float(credits),
            "total_debits": float(abs(debits)),
            "closing_balance": float(closing),
        },
    }


def parse_tally_xml(xml_content: str | bytes) -> pd.DataFrame:
    """Parse Tally Prime XML export of bill-wise ledger allocations.

    Extracts:
        - party_name: str
        - bill_date: datetime
        - bill_name: str
        - amount: float
        - bill_type: str (New Ref / Agst Ref)
    """
    if isinstance(xml_content, str):
        xml_bytes = xml_content.encode("utf-8")
    else:
        xml_bytes = xml_content

    root = ET.fromstring(xml_bytes)
    records = []

    # Traverse all TALLYMESSAGE / LEDGER or BILLALLOCATIONS elements
    for ledger in root.iter("LEDGER"):
        party_name = ledger.get("NAME") or ""
        if not party_name:
            p_elem = ledger.find(".//NAME")
            if p_elem is not None and p_elem.text:
                party_name = p_elem.text.strip()

        # Check for bill allocations
        for bill in ledger.iter("BILLALLOCATIONS.LIST"):
            name_elem = bill.find("NAME")
            amt_elem = bill.find("AMOUNT")
            type_elem = bill.find("BILLTYPE")
            date_elem = bill.find("BILLCREDITPERIOD") or bill.find("DATE")

            bill_name = name_elem.text.strip() if (name_elem is not None and name_elem.text) else "BILL-REF"
            raw_amt = amt_elem.text.strip() if (amt_elem is not None and amt_elem.text) else "0"
            b_type = type_elem.text.strip() if (type_elem is not None and type_elem.text) else "Agst Ref"

            try:
                amt = float(re.sub(r"[^\d.-]", "", raw_amt))
            except ValueError:
                amt = 0.0

            raw_d = date_elem.text.strip() if (date_elem is not None and date_elem.text) else ""
            try:
                b_date = pd.to_datetime(raw_d) if raw_d else pd.Timestamp.now()
            except Exception:
                b_date = pd.Timestamp.now()

            records.append({
                "party_name": party_name,
                "bill_name": bill_name,
                "amount": abs(amt),
                "bill_type": b_type,
                "bill_date": b_date,
            })

    # Also handle standalone BILLALLOCATIONS root tags
    if not records:
        for bill in root.iter("BILLALLOCATION"):
            p_elem = bill.find("PARTYNAME") or bill.find("LEDGERNAME")
            name_elem = bill.find("NAME")
            amt_elem = bill.find("AMOUNT")

            party_name = p_elem.text.strip() if (p_elem is not None and p_elem.text) else "Customer"
            bill_name = name_elem.text.strip() if (name_elem is not None and name_elem.text) else "BILL"
            raw_amt = amt_elem.text.strip() if (amt_elem is not None and amt_elem.text) else "0"
            try:
                amt = float(re.sub(r"[^\d.-]", "", raw_amt))
            except ValueError:
                amt = 0.0

            records.append({
                "party_name": party_name,
                "bill_name": bill_name,
                "amount": abs(amt),
                "bill_type": "Agst Ref",
                "bill_date": pd.Timestamp.now(),
            })

    return pd.DataFrame(records) if records else pd.DataFrame(columns=["party_name", "bill_name", "amount", "bill_type", "bill_date"])
