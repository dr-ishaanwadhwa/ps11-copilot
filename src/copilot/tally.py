"""CA Tally Export Pack: TallyPrime XML Receipt Vouchers and 6-Sheet OpenPyXL CA Reconciliation Workbook.

Generates:
1. Pure TDL XML Receipt Vouchers compatible with TallyPrime 1.0-7.1 and Tally.ERP 9.
2. Standardized 6-sheet Chartered Accountant Reconciliation Workbook (.xlsx) via openpyxl.
"""
from __future__ import annotations

import io
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import pandas as pd


# ---------------------------------------------------------------------------
# Visual Styling Tokens (aligned with Design Tokens)
# ---------------------------------------------------------------------------
COLOR_PRIMARY_HEADER = "24509A"   # Primary Accent Blue
COLOR_SUBHEADER = "F3F3F0"        # Subheader Light Neutral
COLOR_ALERT_FILL = "FDE8E8"       # Discrepancy Light Red
COLOR_ALERT_TEXT = "A8261D"       # Discrepancy Red Text
COLOR_PASS_FILL = "DEF7EC"        # Pass Light Green
COLOR_PASS_TEXT = "03543F"        # Pass Green Text
COLOR_INK = "17191C"              # Dark Ink Text

INR_CURRENCY_FORMAT = '₹#,##,##0.00;[Red]−₹#,##,##0.00;"₹0.00"'
DATE_FORMAT = "YYYY-MM-DD"


# ---------------------------------------------------------------------------
# Date and GUID Helpers
# ---------------------------------------------------------------------------
def _format_tally_date(val: Any) -> str:
    """Format any date-like input to strictly 8-digit YYYYMMDD string (no separators)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return datetime.now().strftime("%Y%m%d")
    if isinstance(val, (datetime, date, pd.Timestamp)):
        return val.strftime("%Y%m%d")
    s = str(val).strip()
    digits = re.sub(r"[^\d]", "", s)
    if len(digits) >= 8:
        return digits[:8]
    try:
        ts = pd.to_datetime(s)
        return ts.strftime("%Y%m%d")
    except Exception:
        return datetime.now().strftime("%Y%m%d")


def _format_iso_date(val: Any) -> str:
    """Format date to YYYY-MM-DD string."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    if isinstance(val, (datetime, date, pd.Timestamp)):
        return val.strftime("%Y-%m-%d")
    try:
        ts = pd.to_datetime(val)
        return ts.strftime("%Y-%m-%d")
    except Exception:
        return str(val)[:10]


# ---------------------------------------------------------------------------
# TallyPrime / Tally.ERP 9 XML Receipt Vouchers Generator
# ---------------------------------------------------------------------------
def generate_tally_xml(*args: Any, **kwargs: Any) -> str:
    """Generate TallyPrime / Tally.ERP 9 XML Receipt Vouchers conforming to R4 specification.

    Supported calling conventions:
    1. Direct Vouchers Mode:
       generate_tally_xml(company_name: str, vouchers: list[dict]) -> str
       generate_tally_xml(company_name="...", vouchers=[...]) -> str
    2. Model Mode:
       generate_tally_xml(pack: Pack, matches: list[Match], biz: str, company_name: str = None) -> str
       generate_tally_xml(pack=pack, matches=matches, biz=biz, company_name=...) -> str
    """
    company_name: str = "Kaveri Distributors"
    vouchers: list[dict[str, Any]] = []

    # Detect calling convention
    if args and not hasattr(args[0], "bank") and not hasattr(args[0], "invoices"):
        # Form 1: generate_tally_xml(company_name, vouchers)
        company_name = str(args[0])
        if len(args) > 1 and isinstance(args[1], list):
            vouchers = args[1]
        elif "vouchers" in kwargs:
            vouchers = kwargs["vouchers"]
    elif "company_name" in kwargs and "vouchers" in kwargs and not ("pack" in kwargs or args):
        company_name = str(kwargs["company_name"])
        vouchers = kwargs["vouchers"]
    else:
        # Form 2: generate_tally_xml(pack, matches, biz, company_name=None)
        pack = args[0] if len(args) > 0 else kwargs.get("pack")
        matches = args[1] if len(args) > 1 else kwargs.get("matches", [])
        biz = args[2] if len(args) > 2 else kwargs.get("biz", "SME-1")
        comp = args[3] if len(args) > 3 else kwargs.get("company_name", None)

        if comp:
            company_name = str(comp)
        elif pack and hasattr(pack, "businesses") and pack.businesses is not None:
            biz_df = pack.businesses[pack.businesses["business_id"] == biz]
            if not biz_df.empty:
                company_name = str(biz_df["business_name"].iloc[0])
            else:
                company_name = f"Business-{biz}"
        else:
            company_name = "Kaveri Distributors" if biz == "SME-1" else f"Business-{biz}"

        vouchers = _build_vouchers_from_pack(pack, matches, biz, company_name)

    return _render_tally_xml(company_name, vouchers)


def _build_vouchers_from_pack(
    pack: Any,
    matches: Sequence[Any],
    biz: str,
    company_name: str,
) -> list[dict[str, Any]]:
    """Build list of voucher dictionaries from Pack and Match models."""
    vouchers: list[dict[str, Any]] = []
    if not pack or not hasattr(pack, "bank") or pack.bank is None:
        return vouchers

    # Determine default bank ledger name from pack.businesses
    bank_ledger = "HDFC Bank Current A/c"
    if hasattr(pack, "businesses") and pack.businesses is not None:
        biz_rows = pack.businesses[pack.businesses["business_id"] == biz]
        if not biz_rows.empty:
            acct_desc = str(biz_rows["bank_account"].iloc[0])
            if "HDFC" in acct_desc:
                bank_ledger = "HDFC Bank Current A/c"
            elif "ICICI" in acct_desc:
                bank_ledger = "ICICI Bank Current A/c"
            elif "Kotak" in acct_desc:
                bank_ledger = "Kotak Mahindra Bank Current A/c"
            else:
                bank_ledger = acct_desc.split("—")[0].strip() + " Current A/c"

    # Index bank table by txn_id
    bank_by_id: dict[str, Any] = {}
    if hasattr(pack, "bank") and pack.bank is not None:
        for r in pack.bank[pack.bank["business_id"] == biz].itertuples():
            bank_by_id[r.txn_id] = r

    # Filter AUTO matched receipts (or confirmed matches)
    for m in matches:
        if getattr(m, "business_id", "") != biz:
            continue
        tier = getattr(m, "tier", "")
        if tier not in ("AUTO", "CONFIRMED"):
            continue

        txn_id = getattr(m, "txn_id", "")
        bank_row = bank_by_id.get(txn_id)
        if bank_row is None:
            continue

        credit_inr = getattr(bank_row, "credit_inr", 0.0)
        amt = float(credit_inr if credit_inr > 0 else getattr(bank_row, "amount", 0.0))
        txn_date = getattr(bank_row, "txn_date", None)
        narration = getattr(bank_row, "narration", "")
        channel = getattr(bank_row, "channel", "Bank")
        rule = getattr(m, "rule", "EXACT")
        payer = getattr(m, "payer", None) or "Customer"
        docs = getattr(m, "docs", [])

        # Build allocations
        allocations = [
            {"invoice_no": doc_id, "amount": float(doc_amt), "bill_type": "Agst Ref"}
            for doc_id, doc_amt in docs
        ]
        doc_total = sum(float(doc_amt) for _, doc_amt in docs) if docs else amt
        round_off = round(amt - doc_total, 2) if (docs and abs(amt - doc_total) <= 100.0) else 0.0

        vouchers.append({
            "txn_id": txn_id,
            "biz": biz,
            "date": txn_date,
            "voucher_no": f"RCPT-{txn_id}",
            "party_name": payer,
            "amount": amt,
            "bank_ledger": bank_ledger,
            "narration": f"Auto-reconciled: D60 {rule} match against {', '.join(d[0] for d in docs)} via {channel} UTR: {narration}",
            "round_off": round_off,
            "allocations": allocations,
            "guid": f"COPILOT-{biz}-{txn_id}",
            "channel": channel,
        })

    return vouchers


def _render_tally_xml(company_name: str, vouchers: list[dict[str, Any]]) -> str:
    """Render vouchers into Tally XML format with strict schema compliance."""
    root = ET.Element("ENVELOPE")
    header = ET.SubElement(root, "HEADER")
    tally_req = ET.SubElement(header, "TALLYREQUEST")
    tally_req.text = "Import Data"

    body = ET.SubElement(root, "BODY")
    import_data = ET.SubElement(body, "IMPORTDATA")
    req_desc = ET.SubElement(import_data, "REQUESTDESC")
    rep_name = ET.SubElement(req_desc, "REPORTNAME")
    rep_name.text = "Vouchers"
    static_vars = ET.SubElement(req_desc, "STATICVARIABLES")
    curr_comp = ET.SubElement(static_vars, "SVCURRENTCOMPANY")
    curr_comp.text = company_name

    req_data = ET.SubElement(import_data, "REQUESTDATA")
    tally_msg = ET.SubElement(req_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})

    for idx, v in enumerate(vouchers, start=1):
        vch = ET.SubElement(tally_msg, "VOUCHER", {
            "VOUCHERTYPE": "Receipt",
            "VCHTYPE": "Receipt",
            "ACTION": "Create",
            "OBJVIEW": "Accounting Voucher View",
        })

        date_str = _format_tally_date(v.get("date"))
        ET.SubElement(vch, "DATE").text = date_str
        ET.SubElement(vch, "EFFECTIVEDATE").text = date_str

        # Deterministic GUID
        explicit_guid = v.get("guid") or v.get("Tally_Voucher_GUID")
        if explicit_guid:
            guid = str(explicit_guid)
        elif "txn_id" in v and "biz" in v:
            guid = f"COPILOT-{v['biz']}-{v['txn_id']}"
        else:
            seed = f"{company_name}:{v.get('voucher_no', date_str)}"
            guid = str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))

        ET.SubElement(vch, "GUID").text = guid
        ET.SubElement(vch, "VOUCHERTYPENAME").text = "Receipt"
        ET.SubElement(vch, "VOUCHERNUMBER").text = str(v.get("voucher_no") or f"RCPT-{date_str}-{idx:03d}")
        party_name = str(v.get("party_name") or "Sundry Debtors")
        ET.SubElement(vch, "PARTYLEDGERNAME").text = party_name
        ET.SubElement(vch, "NARRATION").text = str(v.get("narration") or "Receipt Voucher")
        ET.SubElement(vch, "ISINVOICE").text = "No"

        # Check for bounced cheque / reversal
        is_reversed = bool(v.get("is_reversed") or v.get("is_bounced"))

        amount = float(v.get("amount", 0.0))
        bank_ledger = str(v.get("bank_ledger") or "HDFC Bank Current A/c")
        tds_amount = float(v.get("tds_amount", 0.0))
        round_off = float(v.get("round_off", 0.0))
        credit_amount = amount + tds_amount - round_off

        if not is_reversed:
            # Normal Receipt: Debit Bank (Negative in Tally XML), Credit Debtor (Positive in Tally XML)
            # 1. Bank Debit Entry
            debit_entry = ET.SubElement(vch, "ALLLEDGERENTRIES.LIST")
            ET.SubElement(debit_entry, "LEDGERNAME").text = bank_ledger
            ET.SubElement(debit_entry, "ISDEEMEDPOSITIVE").text = "Yes"
            ET.SubElement(debit_entry, "AMOUNT").text = f"-{amount:.2f}"

            # Bank Allocation Details if present
            instrument_no = v.get("instrument_number") or v.get("instrument_no") or v.get("utr")
            if instrument_no:
                bank_alloc = ET.SubElement(debit_entry, "BANKALLOCATIONS.LIST")
                ET.SubElement(bank_alloc, "DATE").text = date_str
                ET.SubElement(bank_alloc, "INSTRUMENTDATE").text = date_str
                ET.SubElement(bank_alloc, "TRANSACTIONTYPE").text = str(v.get("channel") or "Inter Bank Transfer")
                ET.SubElement(bank_alloc, "PAYMENTFAVOURING").text = company_name
                ET.SubElement(bank_alloc, "INSTRUMENTNUMBER").text = str(instrument_no)
                ET.SubElement(bank_alloc, "AMOUNT").text = f"-{amount:.2f}"

            # 2. TDS Debit Entry (if applicable)
            if tds_amount > 0:
                tds_entry = ET.SubElement(vch, "ALLLEDGERENTRIES.LIST")
                ET.SubElement(tds_entry, "LEDGERNAME").text = str(v.get("tds_ledger") or "TDS Receivable")
                ET.SubElement(tds_entry, "ISDEEMEDPOSITIVE").text = "Yes"
                ET.SubElement(tds_entry, "AMOUNT").text = f"-{tds_amount:.2f}"

            # 3. Round-Off Entry (if applicable)
            if round_off != 0.0:
                ro_entry = ET.SubElement(vch, "ALLLEDGERENTRIES.LIST")
                ET.SubElement(ro_entry, "LEDGERNAME").text = "Round Off"
                ET.SubElement(ro_entry, "ISDEEMEDPOSITIVE").text = "No" if round_off > 0 else "Yes"
                ET.SubElement(ro_entry, "AMOUNT").text = f"{round_off:.2f}"

            # 4. Customer Credit Entry
            # Support multiple credit entries if specified (e.g. multi-shop route cash deposit)
            custom_credits = v.get("credit_entries")
            if custom_credits and isinstance(custom_credits, list):
                for ce in custom_credits:
                    ce_entry = ET.SubElement(vch, "ALLLEDGERENTRIES.LIST")
                    ET.SubElement(ce_entry, "LEDGERNAME").text = str(ce.get("party_name") or party_name)
                    ET.SubElement(ce_entry, "ISDEEMEDPOSITIVE").text = "No"
                    ce_amt = float(ce.get("amount", 0.0))
                    ET.SubElement(ce_entry, "AMOUNT").text = f"{ce_amt:.2f}"
                    ce_allocs = ce.get("allocations", [])
                    for alloc in ce_allocs:
                        ba = ET.SubElement(ce_entry, "BILLALLOCATIONS.LIST")
                        ET.SubElement(ba, "NAME").text = str(alloc.get("invoice_no") or alloc.get("name") or "ON_ACCOUNT")
                        ET.SubElement(ba, "BILLTYPE").text = str(alloc.get("bill_type") or "Agst Ref")
                        ET.SubElement(ba, "AMOUNT").text = f"{float(alloc.get('amount', 0.0)):.2f}"
            else:
                credit_entry = ET.SubElement(vch, "ALLLEDGERENTRIES.LIST")
                ET.SubElement(credit_entry, "LEDGERNAME").text = party_name
                ET.SubElement(credit_entry, "ISDEEMEDPOSITIVE").text = "No"
                ET.SubElement(credit_entry, "AMOUNT").text = f"{credit_amount:.2f}"

                allocations = v.get("allocations", [])
                if allocations:
                    for alloc in allocations:
                        ba = ET.SubElement(credit_entry, "BILLALLOCATIONS.LIST")
                        ET.SubElement(ba, "NAME").text = str(alloc.get("invoice_no") or alloc.get("name") or "ON_ACCOUNT")
                        ET.SubElement(ba, "BILLTYPE").text = str(alloc.get("bill_type") or "Agst Ref")
                        ET.SubElement(ba, "AMOUNT").text = f"{float(alloc.get('amount', 0.0)):.2f}"
                else:
                    ba = ET.SubElement(credit_entry, "BILLALLOCATIONS.LIST")
                    inv_no = str(v.get("invoice_no") or "ON_ACCOUNT")
                    ET.SubElement(ba, "NAME").text = inv_no
                    ET.SubElement(ba, "BILLTYPE").text = "Agst Ref" if v.get("invoice_no") else "On Account"
                    ET.SubElement(ba, "AMOUNT").text = f"{credit_amount:.2f}"
        else:
            # Reversal / Bounced Cheque: Credit Bank, Debit Customer
            debit_entry = ET.SubElement(vch, "ALLLEDGERENTRIES.LIST")
            ET.SubElement(debit_entry, "LEDGERNAME").text = party_name
            ET.SubElement(debit_entry, "ISDEEMEDPOSITIVE").text = "Yes"
            ET.SubElement(debit_entry, "AMOUNT").text = f"-{amount:.2f}"

            credit_entry = ET.SubElement(vch, "ALLLEDGERENTRIES.LIST")
            ET.SubElement(credit_entry, "LEDGERNAME").text = bank_ledger
            ET.SubElement(credit_entry, "ISDEEMEDPOSITIVE").text = "No"
            ET.SubElement(credit_entry, "AMOUNT").text = f"{amount:.2f}"

    xml_bytes = ET.tostring(root, encoding="utf-8")
    return '<?xml version="1.0" encoding="utf-8"?>\n' + xml_bytes.decode("utf-8")


# ---------------------------------------------------------------------------
# Standardized CA Reconciliation Excel Workbook Generator
# ---------------------------------------------------------------------------
def generate_ca_excel_pack(*args: Any, **kwargs: Any) -> bytes:
    """Generate standardized 6-sheet CA Reconciliation Excel Workbook (.xlsx).

    Supported calling conventions:
    1. Direct Data Mode:
       generate_ca_excel_pack(company, biz, as_of, summary, matched, suggest, unmatched, invs, slips)
       generate_ca_excel_pack(company="...", biz="...", as_of=..., ...)
    2. Model Mode:
       generate_ca_excel_pack(pack: Pack, matches: list[Match], vault: Any, biz: str)
       generate_ca_excel_pack(pack=pack, matches=matches, vault=vault, biz=biz)
    """
    company: str = "Kaveri Distributors"
    biz: str = "SME-1"
    as_of: pd.Timestamp = pd.Timestamp("2026-09-30")
    summary: dict[str, Any] = {}
    matched: list[dict[str, Any]] = []
    suggest: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    invs: list[dict[str, Any]] = []
    slips: list[dict[str, Any]] = []

    # Detect calling convention
    if args and not hasattr(args[0], "bank") and not hasattr(args[0], "invoices"):
        # Form 1: Direct Data Mode
        company = str(args[0])
        biz = str(args[1]) if len(args) > 1 else kwargs.get("biz", "SME-1")
        as_of = args[2] if len(args) > 2 else kwargs.get("as_of", pd.Timestamp("2026-09-30"))
        summary = args[3] if len(args) > 3 else kwargs.get("summary", {})
        matched = args[4] if len(args) > 4 else kwargs.get("matched", [])
        suggest = args[5] if len(args) > 5 else kwargs.get("suggest", [])
        unmatched = args[6] if len(args) > 6 else kwargs.get("unmatched", [])
        invs = args[7] if len(args) > 7 else kwargs.get("invs", [])
        slips = args[8] if len(args) > 8 else kwargs.get("slips", [])
    elif "company" in kwargs and not ("pack" in kwargs or args):
        company = str(kwargs.get("company", "Company"))
        biz = str(kwargs.get("biz", "SME-1"))
        as_of = kwargs.get("as_of", pd.Timestamp("2026-09-30"))
        summary = kwargs.get("summary", {})
        matched = kwargs.get("matched", [])
        suggest = kwargs.get("suggest", [])
        unmatched = kwargs.get("unmatched", [])
        invs = kwargs.get("invs", [])
        slips = kwargs.get("slips", [])
    else:
        # Form 2: Model Mode from pack, matches, vault, biz
        pack = args[0] if len(args) > 0 else kwargs.get("pack")
        matches = args[1] if len(args) > 1 else kwargs.get("matches", [])
        vault = args[2] if len(args) > 2 else kwargs.get("vault", None)
        biz = str(args[3] if len(args) > 3 else kwargs.get("biz", "SME-1"))

        company, as_of, summary, matched, suggest, unmatched, invs, slips = _extract_excel_pack_data(
            pack, matches, vault, biz
        )

    return _build_openpyxl_workbook(company, biz, as_of, summary, matched, suggest, unmatched, invs, slips)


def _extract_excel_pack_data(
    pack: Any,
    matches: Sequence[Any],
    vault: Any,
    biz: str,
) -> tuple[str, pd.Timestamp, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract and synthesize all 6 dataset structures from Pack, Match, and Vault models."""
    company = "Kaveri Distributors" if biz == "SME-1" else f"Business-{biz}"
    opening_balance = 0.0
    bank_account_name = "HDFC Bank Current A/c"

    if pack and hasattr(pack, "businesses") and pack.businesses is not None:
        biz_df = pack.businesses[pack.businesses["business_id"] == biz]
        if not biz_df.empty:
            company = str(biz_df["business_name"].iloc[0])
            opening_balance = float(biz_df["opening_balance_1apr2025"].iloc[0])
            acct_raw = str(biz_df["bank_account"].iloc[0])
            if "HDFC" in acct_raw:
                bank_account_name = "HDFC Bank Current A/c (1928)"
            elif "ICICI" in acct_raw:
                bank_account_name = "ICICI Bank Current A/c"
            elif "Kotak" in acct_raw:
                bank_account_name = "Kotak Mahindra Bank Current A/c"

    # Bank statement figures
    biz_bank = pd.DataFrame()
    as_of = pd.Timestamp("2026-09-30")
    if pack and hasattr(pack, "bank") and pack.bank is not None:
        biz_bank = pack.bank[pack.bank["business_id"] == biz].sort_values(["txn_date", "seq"])
        if not biz_bank.empty:
            as_of = pd.Timestamp(biz_bank["txn_date"].max())

    total_credits = float(biz_bank["credit_inr"].sum()) if not biz_bank.empty else 0.0
    total_debits = float(biz_bank["debit_inr"].sum()) if not biz_bank.empty else 0.0
    computed_closing = opening_balance + total_credits - total_debits
    actual_closing = float(biz_bank.iloc[-1]["balance_inr"]) if not biz_bank.empty else computed_closing

    # Partition matches
    auto_matches = [m for m in matches if getattr(m, "business_id", "") == biz and getattr(m, "tier", "") in ("AUTO", "CONFIRMED")]
    suggest_matches = [m for m in matches if getattr(m, "business_id", "") == biz and getattr(m, "tier", "") == "SUGGEST"]
    ask_matches = [m for m in matches if getattr(m, "business_id", "") == biz and getattr(m, "tier", "") == "ASK"]
    no_doc_matches = [m for m in matches if getattr(m, "business_id", "") == biz and getattr(m, "tier", "") == "NO_DOC"]

    bank_by_id: dict[str, Any] = {}
    if not biz_bank.empty:
        for r in biz_bank.itertuples():
            bank_by_id[r.txn_id] = r

    def _calc_sum(ms: Sequence[Any]) -> float:
        total = 0.0
        for m in ms:
            r = bank_by_id.get(getattr(m, "txn_id", ""))
            if r:
                cr = getattr(r, "credit_inr", 0.0)
                total += float(cr if cr > 0 else getattr(r, "amount", 0.0))
        return total

    auto_inr = _calc_sum(auto_matches)
    suggest_inr = _calc_sum(suggest_matches)
    ask_inr = _calc_sum(ask_matches)
    no_doc_inr = _calc_sum(no_doc_matches)

    # Cash drawer data from Vault
    drawer_counted = 0.0
    drawer_drift = 0.0
    salesman_collections = 0.0
    slips_data: list[dict[str, Any]] = []

    if vault is not None:
        try:
            if hasattr(vault, "get_latest_galla"):
                latest_galla = vault.get_latest_galla(biz)
                if latest_galla:
                    drawer_counted = float(getattr(latest_galla, "counted_cash", 0.0))
                    expected = float(getattr(latest_galla, "expected_cash", 0.0))
                    drawer_drift = round(drawer_counted - expected, 2)
        except Exception:
            pass

        try:
            if hasattr(vault, "get_collections"):
                colls = vault.get_collections(biz)
                for s in colls:
                    salesman_collections += float(getattr(s, "amount", 0.0))
                    slips_data.append({
                        "Slip_ID": getattr(s, "slip_id", ""),
                        "Collection_Date": _format_iso_date(getattr(s, "date", "")),
                        "Salesman_Name": getattr(s, "salesman", ""),
                        "Retail_Shop_Name": getattr(s, "shop", ""),
                        "Amount_Collected_INR": float(getattr(s, "amount", 0.0)),
                        "Payment_Mode": getattr(s, "payment_mode", "CASH"),
                        "Linked_Invoice_No": getattr(s, "invoice_no", ""),
                        "Drawer_Deposit_Date": _format_iso_date(getattr(s, "date", "")),
                        "Drawer_Tally_Status": "BALANCED_IN_GALLA" if getattr(s, "payment_mode", "") == "CASH" else "NOT_APPLICABLE",
                    })
        except Exception:
            pass

    summary = {
        "opening_balance": opening_balance,
        "total_credits": total_credits,
        "total_debits": total_debits,
        "computed_closing": computed_closing,
        "actual_closing": actual_closing,
        "auto_count": len(auto_matches),
        "auto_inr": auto_inr,
        "suggest_count": len(suggest_matches),
        "suggest_inr": suggest_inr,
        "ask_count": len(ask_matches),
        "ask_inr": ask_inr,
        "no_doc_count": len(no_doc_matches),
        "no_doc_inr": no_doc_inr,
        "drawer_counted": drawer_counted,
        "salesman_collections": salesman_collections,
        "drawer_drift": drawer_drift,
    }

    # Sheet 2: Matched_Receipts_AUTO
    matched_receipts: list[dict[str, Any]] = []
    for m in auto_matches:
        txn_id = getattr(m, "txn_id", "")
        r = bank_by_id.get(txn_id)
        if not r:
            continue
        amt = float(getattr(r, "credit_inr", 0.0) or getattr(r, "amount", 0.0))
        docs = getattr(m, "docs", [])
        doc_total = sum(float(d[1]) for d in docs) if docs else amt
        round_off = round(amt - doc_total, 2) if (docs and abs(amt - doc_total) <= 100.0) else 0.0
        guid = f"COPILOT-{biz}-{txn_id}"

        matched_receipts.append({
            "Txn_ID": txn_id,
            "Txn_Date": _format_iso_date(getattr(r, "txn_date", None)),
            "Amount_INR": amt,
            "Bank_Account": bank_account_name,
            "Bank_Narration": getattr(r, "narration", ""),
            "Channel": getattr(r, "channel", "Bank"),
            "Payer_Party_Name": getattr(m, "payer", "") or "Customer",
            "Matching_Rule": getattr(m, "rule", "EXACT"),
            "Matched_Doc_IDs": ", ".join(d[0] for d in docs),
            "Doc_Total_INR": doc_total,
            "Round_Off_INR": round_off,
            "TDS_Deducted_INR": 0.0,
            "Tally_Voucher_GUID": guid,
            "Tally_Post_Status": "READY_FOR_IMPORT",
        })

    # Sheet 3: Suggested_Matches
    suggested_matches: list[dict[str, Any]] = []
    for m in suggest_matches:
        txn_id = getattr(m, "txn_id", "")
        r = bank_by_id.get(txn_id)
        if not r:
            continue
        amt = float(getattr(r, "credit_inr", 0.0) or getattr(r, "amount", 0.0))
        docs = getattr(m, "docs", [])
        suggested_matches.append({
            "Txn_ID": txn_id,
            "Txn_Date": _format_iso_date(getattr(r, "txn_date", None)),
            "Amount_INR": amt,
            "Bank_Narration": getattr(r, "narration", ""),
            "Proposed_Party": getattr(m, "payer", "") or "Inferred Party",
            "Proposed_Rule": getattr(m, "rule", "EXACT_AMBIGUOUS"),
            "Proposed_Doc_IDs": ", ".join(d[0] for d in docs),
            "Confidence_Note": getattr(m, "note", "") or "Requires review (D60)",
            "CA_Approval_Status": "PENDING_REVIEW",
            "CA_Audit_Remarks": "",
        })

    # Sheet 4: Unmatched_Bank_Credits
    unmatched_credits: list[dict[str, Any]] = []
    for m in ask_matches:
        txn_id = getattr(m, "txn_id", "")
        r = bank_by_id.get(txn_id)
        if not r:
            continue
        amt = float(getattr(r, "credit_inr", 0.0) or getattr(r, "amount", 0.0))
        unmatched_credits.append({
            "Txn_ID": txn_id,
            "Txn_Date": _format_iso_date(getattr(r, "txn_date", None)),
            "Amount_INR": amt,
            "Bank_Narration": getattr(r, "narration", ""),
            "Channel": getattr(r, "channel", "Bank"),
            "Reason_Code": getattr(m, "note", "") or "UNMATCHED_CREDIT",
            "Client_Clarification": "",
            "Suggested_Action": "Request party confirmation via WhatsApp / CA allocate",
        })

    # Sheet 5: Open_Invoices_Aging
    open_invoices: list[dict[str, Any]] = []
    if pack and hasattr(pack, "invoices") and pack.invoices is not None:
        biz_invs = pack.invoices[pack.invoices["business_id"] == biz]
        for inv_row in biz_invs.itertuples():
            total = float(getattr(inv_row, "invoice_total", 0.0))
            received = float(getattr(inv_row, "amount_received", 0.0))
            outstanding = total - received
            if outstanding > 0.01:
                due_ts = getattr(inv_row, "due_date", None) or getattr(inv_row, "invoice_date", None)
                days = (as_of - pd.Timestamp(due_ts)).days if due_ts is not None else 0
                days = max(days, 0)

                if days <= 30:
                    bucket = "0-30 Days"
                elif days <= 60:
                    bucket = "31-60 Days"
                elif days <= 90:
                    bucket = "61-90 Days"
                elif days <= 180:
                    bucket = "91-180 Days"
                elif days <= 365:
                    bucket = "181-365 Days"
                elif days < 913:
                    bucket = ">365 Days"
                else:
                    bucket = ">30 Months"

                # Section 18 of the Limitation Act: 3-year statutory bar; alert near 30-month cliff
                s18_alert = "YES: >30 MONTHS CLIFF" if days >= 913 else "NO"

                open_invoices.append({
                    "Invoice_No": getattr(inv_row, "invoice_no", ""),
                    "Invoice_Date": _format_iso_date(getattr(inv_row, "invoice_date", None)),
                    "Due_Date": _format_iso_date(getattr(inv_row, "due_date", None)),
                    "Customer_Name": getattr(inv_row, "customer_name", ""),
                    "Taxable_Value_INR": float(getattr(inv_row, "taxable_value", 0.0)),
                    "GST_INR": float(getattr(inv_row, "cgst", 0.0) + getattr(inv_row, "sgst", 0.0) + getattr(inv_row, "igst", 0.0)),
                    "Invoice_Total_INR": total,
                    "Settled_INR": received,
                    "Outstanding_INR": outstanding,
                    "Days_Outstanding": days,
                    "Aging_Bucket": bucket,
                    "Section_18_Alert": s18_alert,
                })

    return company, as_of, summary, matched_receipts, suggested_matches, unmatched_credits, open_invoices, slips_data


def _build_openpyxl_workbook(
    company_name: str,
    business_id: str,
    as_of_date: pd.Timestamp,
    summary_data: dict[str, Any],
    matched_receipts: list[dict[str, Any]],
    suggested_matches: list[dict[str, Any]],
    unmatched_credits: list[dict[str, Any]],
    open_invoices: list[dict[str, Any]],
    salesman_slips: list[dict[str, Any]],
) -> bytes:
    """Build and style the 6-sheet CA Reconciliation Workbook."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default blank sheet

    # Fonts & Styles
    header_fill = PatternFill(start_color=COLOR_PRIMARY_HEADER, end_color=COLOR_PRIMARY_HEADER, fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    section_fill = PatternFill(start_color=COLOR_SUBHEADER, end_color=COLOR_SUBHEADER, fill_type="solid")
    section_font = Font(name="Calibri", size=11, bold=True, color=COLOR_INK)
    bold_font = Font(name="Calibri", size=10, bold=True)
    regular_font = Font(name="Calibri", size=10)

    pass_fill = PatternFill(start_color=COLOR_PASS_FILL, end_color=COLOR_PASS_FILL, fill_type="solid")
    pass_font = Font(name="Calibri", size=10, bold=True, color=COLOR_PASS_TEXT)
    fail_fill = PatternFill(start_color=COLOR_ALERT_FILL, end_color=COLOR_ALERT_FILL, fill_type="solid")
    fail_font = Font(name="Calibri", size=10, bold=True, color=COLOR_ALERT_TEXT)

    thin_border = Border(
        left=Side(style="thin", color="E5E7EB"),
        right=Side(style="thin", color="E5E7EB"),
        top=Side(style="thin", color="E5E7EB"),
        bottom=Side(style="thin", color="E5E7EB"),
    )

    as_of_str = _format_iso_date(as_of_date)

    # -----------------------------------------------------------------------
    # Sheet 1: Reconciliation_Summary
    # -----------------------------------------------------------------------
    ws1 = wb.create_sheet(title="Reconciliation_Summary")
    ws1.views.sheetView[0].showGridLines = True

    # Block A: Header Metadata
    ws1.append(["Business Name", company_name, "Business ID", business_id])
    ws1.append(["As of Date", as_of_str, "Audit Standard", "Companies Act 2013 / IT Act 2025"])
    ws1.append([])

    # Block B: Bank Balance Tie Verification
    opening_bal = float(summary_data.get("opening_balance", 0.0))
    credits = float(summary_data.get("total_credits", 0.0))
    debits = float(summary_data.get("total_debits", 0.0))
    computed_close = float(summary_data.get("computed_closing", round(opening_bal + credits - debits, 2)))
    actual_close = float(summary_data.get("actual_closing", computed_close))
    variance = round(computed_close - actual_close, 2)
    tie_status = "PASS: 100% TIED" if abs(variance) < 1.0 else "FAIL: BALANCE BREAK"

    ws1.append(["BANK ACCOUNT BALANCE TIE VERIFICATION", ""])
    ws1.append(["Opening Balance", opening_bal])
    ws1.append(["Total Bank Credits", credits])
    ws1.append(["Total Bank Debits", debits])
    ws1.append(["Computed Closing Balance", computed_close])
    ws1.append(["Actual Bank Closing", actual_close])
    ws1.append(["Balance Variance", variance])
    ws1.append(["Balance Tie Status", tie_status])
    ws1.append([])

    # Block C: Decision 60 Matching Classification
    auto_cnt = summary_data.get("auto_count", len(matched_receipts))
    auto_amt = float(summary_data.get("auto_inr", sum(float(r.get("Amount_INR", 0.0)) for r in matched_receipts)))
    sug_cnt = summary_data.get("suggest_count", len(suggested_matches))
    sug_amt = float(summary_data.get("suggest_inr", sum(float(r.get("Amount_INR", 0.0)) for r in suggested_matches)))
    ask_cnt = summary_data.get("ask_count", len(unmatched_credits))
    ask_amt = float(summary_data.get("ask_inr", sum(float(r.get("Amount_INR", 0.0)) for r in unmatched_credits)))
    no_doc_cnt = summary_data.get("no_doc_count", 0)
    no_doc_amt = float(summary_data.get("no_doc_inr", 0.0))

    ws1.append(["DECISION 60 MATCHING CLASSIFICATION", "Count", "Rupee Total (INR)"])
    ws1.append(["AUTO Reconciled (Straight-Through)", auto_cnt, auto_amt])
    ws1.append(["SUGGEST Reconciled (Review Queue)", sug_cnt, sug_amt])
    ws1.append(["ASK (Unmatched Exceptions)", ask_cnt, ask_amt])
    ws1.append(["NO_DOC (Owner Capital / Contra)", no_doc_cnt, no_doc_amt])
    ws1.append([])

    # Block D: Cash Drawer & Collections Cross-Check
    drawer_counted = float(summary_data.get("drawer_counted", 0.0))
    salesman_colls = float(summary_data.get("salesman_collections", sum(float(s.get("Amount_Collected_INR", 0.0)) for s in salesman_slips)))
    drawer_drift = float(summary_data.get("drawer_drift", 0.0))

    ws1.append(["CASH DRAWER & COLLECTIONS CROSS-CHECK", ""])
    ws1.append(["Drawer Counted Cash", drawer_counted])
    ws1.append(["Salesman Route Collections", salesman_colls])
    ws1.append(["Drawer Drift", drawer_drift])

    # Style Sheet 1
    for row in ws1.iter_rows():
        for cell in row:
            val = str(cell.value or "")
            if cell.column == 1 and cell.value and any(val.startswith(p) for p in ("BANK ACCOUNT", "DECISION 60", "CASH DRAWER")):
                cell.fill = section_fill
                cell.font = section_font
            elif cell.row in (1, 2) and cell.column in (1, 3):
                cell.font = bold_font
            elif cell.column == 1 and cell.value:
                cell.font = regular_font

            # Style currency cells
            if isinstance(cell.value, (int, float)) and cell.column in (2, 3) and cell.row > 4:
                # Count column in block C is integer, amounts are currency
                if cell.row in (13, 14, 15, 16) and cell.column == 2:
                    cell.number_format = "#,##0"
                else:
                    cell.number_format = INR_CURRENCY_FORMAT

            # Highlight Balance Tie Status
            if val == "PASS: 100% TIED":
                cell.fill = pass_fill
                cell.font = pass_font
            elif val == "FAIL: BALANCE BREAK":
                cell.fill = fail_fill
                cell.font = fail_font

    # -----------------------------------------------------------------------
    # Sheet 2: Matched_Receipts_AUTO
    # -----------------------------------------------------------------------
    ws2 = wb.create_sheet(title="Matched_Receipts_AUTO")
    headers2 = [
        "Txn_ID", "Txn_Date", "Amount_INR", "Bank_Account", "Bank_Narration",
        "Channel", "Payer_Party_Name", "Matching_Rule", "Matched_Doc_IDs",
        "Doc_Total_INR", "Round_Off_INR", "TDS_Deducted_INR", "Tally_Voucher_GUID", "Tally_Post_Status"
    ]
    ws2.append(headers2)
    for cell in ws2[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r in matched_receipts:
        ws2.append([r.get(k, "") for k in headers2])

    ws2.auto_filter.ref = ws2.dimensions
    ws2.freeze_panes = "A2"

    # Number formatting for Sheet 2
    for row in ws2.iter_rows(min_row=2):
        for cell in row:
            col_name = headers2[cell.column - 1]
            if col_name in ("Amount_INR", "Doc_Total_INR", "Round_Off_INR", "TDS_Deducted_INR"):
                cell.number_format = INR_CURRENCY_FORMAT
                cell.alignment = Alignment(horizontal="right")
            elif col_name == "Txn_Date":
                cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border

    # -----------------------------------------------------------------------
    # Sheet 3: Suggested_Matches
    # -----------------------------------------------------------------------
    ws3 = wb.create_sheet(title="Suggested_Matches")
    headers3 = [
        "Txn_ID", "Txn_Date", "Amount_INR", "Bank_Narration", "Proposed_Party",
        "Proposed_Rule", "Proposed_Doc_IDs", "Confidence_Note", "CA_Approval_Status", "CA_Audit_Remarks"
    ]
    ws3.append(headers3)
    for cell in ws3[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r in suggested_matches:
        ws3.append([r.get(k, "") for k in headers3])

    ws3.auto_filter.ref = ws3.dimensions
    ws3.freeze_panes = "A2"

    for row in ws3.iter_rows(min_row=2):
        for cell in row:
            col_name = headers3[cell.column - 1]
            if col_name == "Amount_INR":
                cell.number_format = INR_CURRENCY_FORMAT
                cell.alignment = Alignment(horizontal="right")
            elif col_name == "Txn_Date":
                cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border

    # -----------------------------------------------------------------------
    # Sheet 4: Unmatched_Bank_Credits
    # -----------------------------------------------------------------------
    ws4 = wb.create_sheet(title="Unmatched_Bank_Credits")
    headers4 = [
        "Txn_ID", "Txn_Date", "Amount_INR", "Bank_Narration", "Channel",
        "Reason_Code", "Client_Clarification", "Suggested_Action"
    ]
    ws4.append(headers4)
    for cell in ws4[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r in unmatched_credits:
        ws4.append([r.get(k, "") for k in headers4])

    ws4.auto_filter.ref = ws4.dimensions
    ws4.freeze_panes = "A2"

    for row in ws4.iter_rows(min_row=2):
        for cell in row:
            col_name = headers4[cell.column - 1]
            if col_name == "Amount_INR":
                cell.number_format = INR_CURRENCY_FORMAT
                cell.alignment = Alignment(horizontal="right")
            elif col_name == "Txn_Date":
                cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border

    # -----------------------------------------------------------------------
    # Sheet 5: Open_Invoices_Aging
    # -----------------------------------------------------------------------
    ws5 = wb.create_sheet(title="Open_Invoices_Aging")
    headers5 = [
        "Invoice_No", "Invoice_Date", "Due_Date", "Customer_Name", "Taxable_Value_INR",
        "GST_INR", "Invoice_Total_INR", "Settled_INR", "Outstanding_INR",
        "Days_Outstanding", "Aging_Bucket", "Section_18_Alert"
    ]
    ws5.append(headers5)
    for cell in ws5[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r in open_invoices:
        ws5.append([r.get(k, "") for k in headers5])

    ws5.auto_filter.ref = ws5.dimensions
    ws5.freeze_panes = "A2"

    for row in ws5.iter_rows(min_row=2):
        for cell in row:
            col_name = headers5[cell.column - 1]
            if col_name in ("Taxable_Value_INR", "GST_INR", "Invoice_Total_INR", "Settled_INR", "Outstanding_INR"):
                cell.number_format = INR_CURRENCY_FORMAT
                cell.alignment = Alignment(horizontal="right")
            elif col_name == "Days_Outstanding":
                cell.number_format = "#,##0"
                cell.alignment = Alignment(horizontal="right")
            elif col_name in ("Invoice_Date", "Due_Date"):
                cell.alignment = Alignment(horizontal="center")
            elif col_name == "Section_18_Alert" and "YES" in str(cell.value or ""):
                cell.fill = fail_fill
                cell.font = fail_font
                cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border

    # -----------------------------------------------------------------------
    # Sheet 6: Salesman_Collection_Slips
    # -----------------------------------------------------------------------
    ws6 = wb.create_sheet(title="Salesman_Collection_Slips")
    headers6 = [
        "Slip_ID", "Collection_Date", "Salesman_Name", "Retail_Shop_Name",
        "Amount_Collected_INR", "Payment_Mode", "Linked_Invoice_No",
        "Drawer_Deposit_Date", "Drawer_Tally_Status"
    ]
    ws6.append(headers6)
    for cell in ws6[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r in salesman_slips:
        ws6.append([r.get(k, "") for k in headers6])

    ws6.auto_filter.ref = ws6.dimensions
    ws6.freeze_panes = "A2"

    for row in ws6.iter_rows(min_row=2):
        for cell in row:
            col_name = headers6[cell.column - 1]
            if col_name == "Amount_Collected_INR":
                cell.number_format = INR_CURRENCY_FORMAT
                cell.alignment = Alignment(horizontal="right")
            elif col_name in ("Collection_Date", "Drawer_Deposit_Date"):
                cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border

    # Auto-adjust column widths across all sheets
    for ws in wb.worksheets:
        for col in ws.columns:
            max_len = 0
            for cell in col:
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 13)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Object-Oriented Helper Classes (TDL & CA Exporters)
# ---------------------------------------------------------------------------
class TallyReceiptExporter:
    """TDL XML Receipt Voucher export engine."""

    def __init__(self, company_name: str = "Kaveri Distributors"):
        self.company_name = company_name

    def export_vouchers(self, vouchers: list[dict[str, Any]]) -> str:
        """Render explicit list of voucher dictionaries to XML."""
        return generate_tally_xml(self.company_name, vouchers)

    def export_from_pack(self, pack: Any, matches: Sequence[Any], biz: str) -> str:
        """Render D60 auto-reconciled matches from pack to XML."""
        return generate_tally_xml(pack, list(matches), biz, self.company_name)


class CAReconciliationExporter:
    """Chartered Accountant 6-Sheet Reconciliation Workbook export engine."""

    def __init__(self, company_name: str = "Kaveri Distributors", business_id: str = "SME-1"):
        self.company_name = company_name
        self.business_id = business_id

    def generate_workbook(self, *args: Any, **kwargs: Any) -> bytes:
        """Generate multi-tab Excel reconciliation pack."""
        if not args and "company" not in kwargs:
            kwargs["company"] = self.company_name
            kwargs["biz"] = self.business_id
        return generate_ca_excel_pack(*args, **kwargs)
