"""Unit and integration test suite for Milestone 3: CA Tally Export Pack.

Tests:
1. TallyPrime / Tally.ERP 9 XML Receipt Vouchers Generator (sign rules, Agst Ref, GUID, TDS, round-off).
2. Standardized 6-sheet CA Reconciliation Excel Workbook (openpyxl, balance tie, aging, parchi slips).
3. Public safety and language ban compliance.
"""
from __future__ import annotations

import io
import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from copilot.load import load_pack
from copilot.match.engine import Matcher
from copilot.tally import (
    CAReconciliationExporter,
    TallyReceiptExporter,
    generate_ca_excel_pack,
    generate_tally_xml,
)
from copilot.vault.models import Collection, GallaEntry


# ==============================================================================
# 1. Tally XML Envelope & Hierarchy Tests
# ==============================================================================

def test_tally_xml_envelope_and_header_structure():
    """Verify generated XML contains standard ENVELOPE, HEADER, BODY, IMPORTDATA, and TALLYMESSAGE."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-ENV-01",
        "party_name": "Laxmi Super Mart",
        "amount": 50000.0,
        "bank_ledger": "HDFC Bank Current A/c",
    }]
    xml_str = generate_tally_xml("Kaveri Distributors", vouchers)
    root = ET.fromstring(xml_str)

    assert root.tag == "ENVELOPE"
    header = root.find("HEADER")
    assert header is not None
    assert header.find("TALLYREQUEST").text == "Import Data"

    body = root.find("BODY")
    assert body is not None
    import_data = body.find("IMPORTDATA")
    assert import_data is not None

    req_desc = import_data.find("REQUESTDESC")
    assert req_desc is not None
    assert req_desc.find("REPORTNAME").text == "Vouchers"
    assert req_desc.find(".//SVCURRENTCOMPANY").text == "Kaveri Distributors"

    req_data = import_data.find("REQUESTDATA")
    assert req_data is not None
    tally_msg = req_data.find("TALLYMESSAGE")
    assert tally_msg is not None
    assert len(tally_msg.findall("VOUCHER")) == 1


def test_tally_xml_voucher_attributes_and_elements():
    """Verify VOUCHER tag has required attributes and child elements."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-ATTR-01",
        "party_name": "Balaji Stores",
        "amount": 25000.0,
        "narration": "Payment via NEFT",
    }]
    xml_str = generate_tally_xml("Kaveri Distributors", vouchers)
    root = ET.fromstring(xml_str)
    vch = root.find(".//VOUCHER")
    assert vch is not None
    assert vch.attrib.get("VOUCHERTYPE") == "Receipt"
    assert vch.attrib.get("VCHTYPE") == "Receipt"
    assert vch.attrib.get("ACTION") == "Create"
    assert vch.attrib.get("OBJVIEW") == "Accounting Voucher View"

    assert vch.find("DATE").text == "20260930"
    assert vch.find("EFFECTIVEDATE").text == "20260930"
    assert vch.find("VOUCHERTYPENAME").text == "Receipt"
    assert vch.find("VOUCHERNUMBER").text == "RCPT-ATTR-01"
    assert vch.find("PARTYLEDGERNAME").text == "Balaji Stores"
    assert vch.find("NARRATION").text == "Payment via NEFT"
    assert vch.find("ISINVOICE").text == "No"


def test_tally_xml_date_format_strictly_8_digits():
    """Verify Tally date is strictly YYYYMMDD with no hyphens or slashes."""
    dates_to_test = [
        "2026-09-30",
        "2026/09/30",
        pd.Timestamp("2026-09-30"),
        pd.Timestamp("2025-04-03 14:30:00"),
    ]
    for d in dates_to_test:
        vouchers = [{
            "date": d,
            "voucher_no": "RCPT-DATE",
            "party_name": "Test Party",
            "amount": 1000.0,
        }]
        xml_str = generate_tally_xml("Kaveri Distributors", vouchers)
        root = ET.fromstring(xml_str)
        date_text = root.find(".//VOUCHER/DATE").text
        assert len(date_text) == 8
        assert date_text.isdigit()
        assert "-" not in date_text
        assert "/" not in date_text


# ==============================================================================
# 2. Tally Double-Entry Accounting Sign Rules & Allocations
# ==============================================================================

def test_tally_xml_double_entry_sign_rules():
    """Verify Bank debit is negative (ISDEEMEDPOSITIVE=Yes) and Party credit is positive (ISDEEMEDPOSITIVE=No)."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-SIGN-01",
        "party_name": "Laxmi Super Mart",
        "amount": 75000.0,
        "bank_ledger": "HDFC Bank Current A/c",
    }]
    xml_str = generate_tally_xml("Kaveri Distributors", vouchers)
    root = ET.fromstring(xml_str)
    ledgers = root.findall(".//ALLLEDGERENTRIES.LIST")
    assert len(ledgers) == 2

    # Bank debit
    bank = ledgers[0]
    assert bank.find("LEDGERNAME").text == "HDFC Bank Current A/c"
    assert bank.find("ISDEEMEDPOSITIVE").text == "Yes"
    assert float(bank.find("AMOUNT").text) == -75000.0

    # Party credit
    party = ledgers[1]
    assert party.find("LEDGERNAME").text == "Laxmi Super Mart"
    assert party.find("ISDEEMEDPOSITIVE").text == "No"
    assert float(party.find("AMOUNT").text) == 75000.0

    # Net voucher balance must be zero
    debit_sum = abs(float(bank.find("AMOUNT").text))
    credit_sum = float(party.find("AMOUNT").text)
    assert round(debit_sum - credit_sum, 2) == 0.0


def test_tally_xml_bill_allocations_agst_ref():
    """Verify bill allocations generate <BILLALLOCATIONS.LIST> with Agst Ref and invoice number."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-ALLOC-01",
        "party_name": "Balaji Provision Stores",
        "amount": 45000.0,
        "allocations": [
            {"invoice_no": "INV-2026-0412", "amount": 45000.0, "bill_type": "Agst Ref"},
        ],
    }]
    xml_str = generate_tally_xml("Kaveri Distributors", vouchers)
    root = ET.fromstring(xml_str)
    party_entry = root.findall(".//ALLLEDGERENTRIES.LIST")[1]
    ballocs = party_entry.findall("BILLALLOCATIONS.LIST")
    assert len(ballocs) == 1
    assert ballocs[0].find("NAME").text == "INV-2026-0412"
    assert ballocs[0].find("BILLTYPE").text == "Agst Ref"
    assert float(ballocs[0].find("AMOUNT").text) == 45000.0


def test_tally_xml_multi_invoice_clubbed_allocations():
    """Verify clubbed payment settling multiple invoices produces multiple <BILLALLOCATIONS.LIST>."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-CLUBBED-01",
        "party_name": "Balaji Provision Stores",
        "amount": 73500.0,
        "allocations": [
            {"invoice_no": "INV-2026-0412", "amount": 45000.0, "bill_type": "Agst Ref"},
            {"invoice_no": "INV-2026-0415", "amount": 28500.0, "bill_type": "Agst Ref"},
        ],
    }]
    xml_str = generate_tally_xml("Kaveri Distributors", vouchers)
    root = ET.fromstring(xml_str)
    ballocs = root.findall(".//BILLALLOCATIONS.LIST")
    assert len(ballocs) == 2
    allocated_names = {b.find("NAME").text for b in ballocs}
    assert allocated_names == {"INV-2026-0412", "INV-2026-0415"}
    total_allocated = sum(float(b.find("AMOUNT").text) for b in ballocs)
    assert total_allocated == 73500.0


def test_tally_xml_round_off_ledger():
    """Verify fractional rupee round-off produces Round Off ledger entry tying debits and credits."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-RO-01",
        "party_name": "Balaji Provision Stores",
        "amount": 73500.0,
        "round_off": 0.50,
        "allocations": [
            {"invoice_no": "INV-2026-0412", "amount": 45000.0, "bill_type": "Agst Ref"},
            {"invoice_no": "INV-2026-0415", "amount": 28499.50, "bill_type": "Agst Ref"},
        ],
    }]
    xml_str = generate_tally_xml("Kaveri Distributors", vouchers)
    root = ET.fromstring(xml_str)
    ledgers = root.findall(".//ALLLEDGERENTRIES.LIST")
    assert len(ledgers) == 3

    ro_entry = next((l for l in ledgers if l.find("LEDGERNAME").text == "Round Off"), None)
    assert ro_entry is not None
    assert ro_entry.find("ISDEEMEDPOSITIVE").text == "No"
    assert float(ro_entry.find("AMOUNT").text) == 0.50

    # Party credit must be net of round off
    party_entry = next(l for l in ledgers if l.find("LEDGERNAME").text == "Balaji Provision Stores")
    assert float(party_entry.find("AMOUNT").text) == 73499.50

    # Debits equal credits
    debits = sum(abs(float(l.find("AMOUNT").text)) for l in ledgers if l.find("ISDEEMEDPOSITIVE").text == "Yes")
    credits = sum(float(l.find("AMOUNT").text) for l in ledgers if l.find("ISDEEMEDPOSITIVE").text == "No")
    assert round(debits, 2) == round(credits, 2)


def test_tally_xml_section_194j_tds_deduction():
    """Verify Section 194J TDS deduction emits TDS Receivable debit entry."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-TDS-01",
        "party_name": "Corporate Retainer Client",
        "amount": 108000.0,      # Net received in bank
        "tds_amount": 10000.0,   # Section 194J TDS
        "bank_ledger": "HDFC Bank Current A/c",
    }]
    xml_str = generate_tally_xml("Northlight Design", vouchers)
    root = ET.fromstring(xml_str)
    ledgers = root.findall(".//ALLLEDGERENTRIES.LIST")
    assert len(ledgers) == 3

    tds_entry = next((l for l in ledgers if l.find("LEDGERNAME").text == "TDS Receivable"), None)
    assert tds_entry is not None
    assert tds_entry.find("ISDEEMEDPOSITIVE").text == "Yes"
    assert float(tds_entry.find("AMOUNT").text) == -10000.0

    party_entry = next(l for l in ledgers if l.find("LEDGERNAME").text == "Corporate Retainer Client")
    assert float(party_entry.find("AMOUNT").text) == 118000.0


def test_tally_xml_combined_tds_and_round_off_balanced():
    """Verify transaction with both TDS deduction and round-off adjustment balances exactly."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-COMBO-01",
        "party_name": "Tech Partners Ltd",
        "amount": 89999.50,
        "tds_amount": 10000.00,
        "round_off": 0.50,
        "bank_ledger": "HDFC Bank Current A/c",
    }]
    xml_str = generate_tally_xml("Northlight", vouchers)
    root = ET.fromstring(xml_str)
    ledgers = root.findall(".//ALLLEDGERENTRIES.LIST")
    assert len(ledgers) == 4  # Bank, TDS, Round Off, Party

    debits = sum(abs(float(l.find("AMOUNT").text)) for l in ledgers if l.find("ISDEEMEDPOSITIVE").text == "Yes")
    credits = sum(float(l.find("AMOUNT").text) for l in ledgers if l.find("ISDEEMEDPOSITIVE").text == "No")
    assert round(debits, 2) == round(credits, 2)


def test_tally_xml_deterministic_guid_idempotency():
    """Verify GUID is deterministic, reproducible, and at least 32 characters long."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-IDEMPOTENT-01",
        "party_name": "Stable Retailer",
        "amount": 35000.0,
    }]
    xml1 = generate_tally_xml("Kaveri Distributors", vouchers)
    xml2 = generate_tally_xml("Kaveri Distributors", vouchers)
    guid1 = ET.fromstring(xml1).find(".//VOUCHER/GUID").text
    guid2 = ET.fromstring(xml2).find(".//VOUCHER/GUID").text
    assert guid1 == guid2
    assert len(guid1) >= 32


def test_tally_xml_special_character_escaping():
    """Verify company and party names with '&', '<', '>' are properly escaped."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-ESCAPE-01",
        "party_name": "Balaji & Sons <General Store>",
        "amount": 12000.0,
    }]
    xml_str = generate_tally_xml("Kaveri & Partners <Distributors>", vouchers)
    assert "&amp;" in xml_str
    # Must parse without xml.etree.ElementTree syntax error
    root = ET.fromstring(xml_str)
    assert root.find(".//PARTYLEDGERNAME").text == "Balaji & Sons <General Store>"
    assert root.find(".//SVCURRENTCOMPANY").text == "Kaveri & Partners <Distributors>"


def test_tally_xml_bounced_cheque_reversal():
    """Verify bounced cheque transaction generates reversed voucher."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-REV-01",
        "party_name": "Defaulting Shop",
        "amount": 50000.0,
        "is_bounced": True,
        "narration": "BOUNCED: Cheque #102938 returned unpaid",
    }]
    xml_str = generate_tally_xml("Kaveri Distributors", vouchers)
    root = ET.fromstring(xml_str)
    ledgers = root.findall(".//ALLLEDGERENTRIES.LIST")
    # In reversal: Debtor is debited (positive deemed positive) and Bank is credited
    debit_entry = next(l for l in ledgers if l.find("ISDEEMEDPOSITIVE").text == "Yes")
    assert debit_entry.find("LEDGERNAME").text == "Defaulting Shop"
    credit_entry = next(l for l in ledgers if l.find("ISDEEMEDPOSITIVE").text == "No")
    assert "HDFC Bank" in credit_entry.find("LEDGERNAME").text


def test_tally_xml_empty_vouchers_list():
    """Verify empty vouchers list generates clean envelope without crash."""
    xml_str = generate_tally_xml("Kaveri Distributors", [])
    root = ET.fromstring(xml_str)
    assert root.tag == "ENVELOPE"
    tally_msg = root.find(".//TALLYMESSAGE")
    assert tally_msg is not None
    assert len(tally_msg.findall("VOUCHER")) == 0


def test_tally_xml_from_pack_and_matches():
    """Verify high-level calling convention generate_tally_xml(pack, matches, biz)."""
    pack = load_pack()
    matcher = Matcher(pack)
    sme1_bank = pack.bank[pack.bank["business_id"] == "SME-1"].sort_values(["txn_date", "seq"])
    matches = [matcher.match(r) for r in sme1_bank.itertuples()]

    xml_str = generate_tally_xml(pack, matches, "SME-1")
    root = ET.fromstring(xml_str)
    assert root.tag == "ENVELOPE"
    assert root.find(".//SVCURRENTCOMPANY").text == "Kaveri Distributors"
    vouchers = root.findall(".//VOUCHER")
    assert len(vouchers) > 1000  # SME-1 has ~1,170 AUTO matches under Decision 60

    # Inspect first voucher
    v0 = vouchers[0]
    assert v0.find("DATE").text.startswith("2025")
    assert "COPILOT-SME-1-" in v0.find("GUID").text
    assert len(v0.findall("ALLLEDGERENTRIES.LIST")) >= 2


# ==============================================================================
# 3. Standardized CA Reconciliation Excel Workbook Tests
# ==============================================================================

def test_ca_excel_pack_generates_all_6_sheets():
    """Verify workbook contains all 6 required sheets with exact names."""
    excel_bytes = generate_ca_excel_pack(
        company="Kaveri Distributors",
        biz="SME-1",
        as_of=pd.Timestamp("2026-09-30"),
        summary={},
        matched=[],
        suggest=[],
        unmatched=[],
        invs=[],
        slips=[],
    )
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0

    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    expected_sheets = [
        "Reconciliation_Summary",
        "Matched_Receipts_AUTO",
        "Suggested_Matches",
        "Unmatched_Bank_Credits",
        "Open_Invoices_Aging",
        "Salesman_Collection_Slips",
    ]
    for s in expected_sheets:
        assert s in wb.sheetnames, f"Missing sheet: {s}"


def test_ca_excel_pack_sheet1_balance_tie_pass():
    """Verify Sheet 1 displays bank balance tie PASS status when variance < ₹1.0."""
    summary_data = {
        "opening_balance": 1000000.0,
        "total_credits": 500000.0,
        "total_debits": 300000.0,
        "computed_closing": 1200000.0,
        "actual_closing": 1200000.0,
    }
    excel_bytes = generate_ca_excel_pack(
        company="Kaveri Distributors",
        biz="SME-1",
        as_of=pd.Timestamp("2026-09-30"),
        summary=summary_data,
        matched=[],
        suggest=[],
        unmatched=[],
        invs=[],
        slips=[],
    )
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    ws = wb["Reconciliation_Summary"]

    tie_row = next((r for r in ws.iter_rows(values_only=True) if r and r[0] == "Balance Tie Status"), None)
    assert tie_row is not None
    assert tie_row[1] == "PASS: 100% TIED"


def test_ca_excel_pack_sheet1_balance_break_flagged():
    """Verify Sheet 1 flags FAIL: BALANCE BREAK when variance >= ₹1.0."""
    summary_data = {
        "opening_balance": 1000000.0,
        "total_credits": 500000.0,
        "total_debits": 300000.0,
        "computed_closing": 1200000.0,
        "actual_closing": 1150000.0,  # ₹50,000 break
    }
    excel_bytes = generate_ca_excel_pack(
        company="Kaveri Distributors",
        biz="SME-1",
        as_of=pd.Timestamp("2026-09-30"),
        summary=summary_data,
        matched=[],
        suggest=[],
        unmatched=[],
        invs=[],
        slips=[],
    )
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    ws = wb["Reconciliation_Summary"]

    tie_row = next((r for r in ws.iter_rows(values_only=True) if r and r[0] == "Balance Tie Status"), None)
    assert tie_row is not None
    assert tie_row[1] == "FAIL: BALANCE BREAK"


def test_ca_excel_pack_sheet2_matched_receipts_auto_columns():
    """Verify Sheet 2 headers, rows, and formatting for D60 auto-matched lines."""
    matched = [{
        "Txn_ID": "TXN-AUTO-01",
        "Txn_Date": "2026-09-30",
        "Amount_INR": 118000.0,
        "Bank_Account": "HDFC Bank Current A/c (1928)",
        "Bank_Narration": "UPI-LAXMI SUPER MART-HDFC0001",
        "Channel": "UPI",
        "Payer_Party_Name": "Laxmi Super Mart",
        "Matching_Rule": "EXACT",
        "Matched_Doc_IDs": "INV-2026-0891",
        "Doc_Total_INR": 118000.0,
        "Round_Off_INR": 0.0,
        "TDS_Deducted_INR": 0.0,
        "Tally_Voucher_GUID": "COPILOT-SME-1-TXN-AUTO-01",
        "Tally_Post_Status": "READY_FOR_IMPORT",
    }]
    excel_bytes = generate_ca_excel_pack(
        company="Kaveri Distributors",
        biz="SME-1",
        as_of=pd.Timestamp("2026-09-30"),
        summary={},
        matched=matched,
        suggest=[],
        unmatched=[],
        invs=[],
        slips=[],
    )
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    ws = wb["Matched_Receipts_AUTO"]

    assert ws.max_row == 2
    row2 = [c.value for c in ws[2]]
    assert "TXN-AUTO-01" in row2
    assert "Laxmi Super Mart" in row2
    assert "READY_FOR_IMPORT" in row2


def test_ca_excel_pack_sheet5_debtor_aging_and_section18():
    """Verify Sheet 5 displays debtor aging and Section 18 Limitation Act alert."""
    invs = [
        {
            "Invoice_No": "INV-RECENT",
            "Invoice_Date": "2026-09-01",
            "Due_Date": "2026-09-15",
            "Customer_Name": "Active Retailer",
            "Taxable_Value_INR": 20000.0,
            "GST_INR": 3600.0,
            "Invoice_Total_INR": 23600.0,
            "Settled_INR": 0.0,
            "Outstanding_INR": 23600.0,
            "Days_Outstanding": 15,
            "Aging_Bucket": "0-30 Days",
            "Section_18_Alert": "NO",
        },
        {
            "Invoice_No": "INV-STALE",
            "Invoice_Date": "2023-01-01",
            "Due_Date": "2023-01-15",
            "Customer_Name": "Defaulted Retailer",
            "Taxable_Value_INR": 50000.0,
            "GST_INR": 9000.0,
            "Invoice_Total_INR": 59000.0,
            "Settled_INR": 0.0,
            "Outstanding_INR": 59000.0,
            "Days_Outstanding": 1300,
            "Aging_Bucket": ">30 Months",
            "Section_18_Alert": "YES: >30 MONTHS CLIFF",
        },
    ]
    excel_bytes = generate_ca_excel_pack(
        company="Kaveri Distributors",
        biz="SME-1",
        as_of=pd.Timestamp("2026-09-30"),
        summary={},
        matched=[],
        suggest=[],
        unmatched=[],
        invs=invs,
        slips=[],
    )
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    ws = wb["Open_Invoices_Aging"]

    assert ws.max_row == 3
    row2 = [c.value for c in ws[2]]
    row3 = [c.value for c in ws[3]]
    assert "INV-RECENT" in row2
    assert "NO" in row2
    assert "INV-STALE" in row3
    assert "YES: >30 MONTHS CLIFF" in row3


def test_ca_excel_pack_sheet6_salesman_collection_slips():
    """Verify Sheet 6 displays salesman collection slips with drawer tally status."""
    slips = [{
        "Slip_ID": "SLIP-TEST-01",
        "Collection_Date": "2026-09-30",
        "Salesman_Name": "Ramesh Kumar",
        "Retail_Shop_Name": "Laxmi Super Mart",
        "Amount_Collected_INR": 45000.0,
        "Payment_Mode": "CASH",
        "Linked_Invoice_No": "INV-2026-0891",
        "Drawer_Deposit_Date": "2026-09-30",
        "Drawer_Tally_Status": "BALANCED_IN_GALLA",
    }]
    excel_bytes = generate_ca_excel_pack(
        company="Kaveri Distributors",
        biz="SME-1",
        as_of=pd.Timestamp("2026-09-30"),
        summary={},
        matched=[],
        suggest=[],
        unmatched=[],
        invs=[],
        slips=slips,
    )
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    ws = wb["Salesman_Collection_Slips"]
    assert ws.max_row == 2
    row2 = [c.value for c in ws[2]]
    assert "SLIP-TEST-01" in row2
    assert "Ramesh Kumar" in row2
    assert "BALANCED_IN_GALLA" in row2


def test_ca_excel_pack_styling_and_number_formats():
    """Verify header fill #24509A, bold white text, and auto-filters."""
    matched = [{
        "Txn_ID": "TXN-01",
        "Txn_Date": "2026-09-30",
        "Amount_INR": 15000.0,
        "Bank_Account": "HDFC",
        "Bank_Narration": "NARR",
        "Channel": "UPI",
        "Payer_Party_Name": "Party",
        "Matching_Rule": "EXACT",
        "Matched_Doc_IDs": "INV-01",
        "Doc_Total_INR": 15000.0,
        "Round_Off_INR": 0.0,
        "TDS_Deducted_INR": 0.0,
        "Tally_Voucher_GUID": "G1",
        "Tally_Post_Status": "READY",
    }]
    excel_bytes = generate_ca_excel_pack(
        company="Kaveri Distributors",
        biz="SME-1",
        as_of=pd.Timestamp("2026-09-30"),
        summary={},
        matched=matched,
        suggest=[],
        unmatched=[],
        invs=[],
        slips=[],
    )
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    ws2 = wb["Matched_Receipts_AUTO"]

    # Header styling
    h1 = ws2["A1"]
    assert h1.fill.start_color.rgb in ("0024509A", "24509A")
    assert h1.font.bold is True
    assert h1.font.color.rgb in ("00FFFFFF", "FFFFFF")

    # Auto-filter enabled
    assert ws2.auto_filter.ref is not None

    # Freeze panes
    assert ws2.freeze_panes == "A2"


def test_ca_excel_pack_from_pack_matches_vault():
    """Verify end-to-end generation from Pack, Matcher, and Vault models."""
    pack = load_pack()
    matcher = Matcher(pack)
    sme1_bank = pack.bank[pack.bank["business_id"] == "SME-1"].sort_values(["txn_date", "seq"])
    matches = [matcher.match(r) for r in sme1_bank.itertuples()]

    excel_bytes = generate_ca_excel_pack(pack, matches, None, "SME-1")
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))

    ws1 = wb["Reconciliation_Summary"]
    tie_row = next((r for r in ws1.iter_rows(values_only=True) if r and r[0] == "Balance Tie Status"), None)
    assert tie_row is not None
    assert tie_row[1] == "PASS: 100% TIED"

    ws2 = wb["Matched_Receipts_AUTO"]
    assert ws2.max_row > 1000  # All D60 AUTO matches populated!

    ws5 = wb["Open_Invoices_Aging"]
    assert ws5.max_row > 1  # Open debtor invoices populated


# ==============================================================================
# 4. Helper Classes Tests
# ==============================================================================

def test_tally_exporter_classes():
    """Verify TallyReceiptExporter and CAReconciliationExporter helper classes."""
    tx = TallyReceiptExporter("Kaveri Distributors")
    xml_str = tx.export_vouchers([{
        "date": "2026-09-30",
        "voucher_no": "RCPT-CLS-01",
        "party_name": "Class Party",
        "amount": 20000.0,
    }])
    assert "<VOUCHER" in xml_str

    cx = CAReconciliationExporter("Kaveri Distributors", "SME-1")
    excel_bytes = cx.generate_workbook(
        company="Kaveri Distributors",
        biz="SME-1",
        as_of=pd.Timestamp("2026-09-30"),
        summary={},
        matched=[],
        suggest=[],
        unmatched=[],
        invs=[],
        slips=[],
    )
    assert len(excel_bytes) > 0


# ==============================================================================
# 5. Public Safety Ban Verification in Test Suite
# ==============================================================================

def test_no_forbidden_phrases_in_tally_module():
    """Verify src/copilot/tally.py and this test file contain zero banned phrases."""
    forbidden = [
        "presentation mode",
        "tax inspection",
        "audit trace",
        "golden pillars",
        "withstand",
        "readiness tier",
        "headroom before",
    ]
    tally_src = (Path(__file__).resolve().parent.parent / "src" / "copilot" / "tally.py").read_text(encoding="utf-8").lower()
    for phrase in forbidden:
        assert phrase not in tally_src, f"Found banned phrase '{phrase}' in src/copilot/tally.py"

    test_src = Path(__file__).read_text(encoding="utf-8").lower()
    for phrase in forbidden:
        # Check against test file lines that aren't the definition of the forbidden list itself
        occurrences = [line for line in test_src.splitlines() if phrase in line and '"' + phrase + '"' not in line]
        assert len(occurrences) == 0, f"Found banned phrase in test body: {occurrences}"
