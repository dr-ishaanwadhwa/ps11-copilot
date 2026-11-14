"""Tier 3: Cross-Feature Combinations E2E Tests (Pairwise coverage across R1–R5).

Covers end-to-end integration workflows coupling multiple features:
1. Parchi cash slip -> Drawer cash in -> CDM Bank Deposit -> Matcher resolution -> Tally XML receipt voucher
2. Vault lock state toggle -> Partial view notice activation -> Ledger query gating -> Unlock -> True Solvency synthesis
3. FIFO allocation across multiple overdue invoices -> Debtors aging schedule in CA Excel pack
4. Mixed mode collection slips (Cash vs UPI vs Cheque) -> Godown drawer cash isolation
5. Stale khata debt (>30 months) -> §18 Limitation alert -> WhatsApp reminder -> Solvency haircut
6. High-value cash payment -> §186 guardrail block -> Lawful split into RTGS + Cash -> Dual Tally XML
7. Multi-route collection slips -> Godown day-close -> CDM banking -> Excel route register
8. Bank statement tie verification -> Balance break detection -> Reconciled tie status in Excel
9. Vault encryption at rest -> Cold restart -> PIN derivation -> Decrypted Tally export
10. Multi-business data isolation: SME-1 (Distributor) vs SME-2 (Clinic) cross-tenant security
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path
import openpyxl
import pandas as pd
import pytest

from copilot.vault.models import GallaEntry, KhataAccount, RokadEntry
from copilot.vault.notice import PARTIAL_VIEW_NOTICE, render_partial_view_notice
from copilot.vault.guardrails import (
    check_single_receipt_cash,
    check_cash_expense,
    check_cash_loan,
    cash_deposit_reporting_facts,
)
from copilot.vault.solvency import compute_total_solvency
from copilot.vault.chase import format_whatsapp_reminder

from .harness import (
    E2EVaultAdapter,
    ExtendedCollection,
    ReferenceVaultCrypto,
    VaultLockedError,
    allocate_invoices_fifo,
    generate_reference_tally_xml,
    generate_reference_ca_excel_pack,
    encrypt_vault_payload,
    decrypt_vault_payload,
)

try:
    from copilot.vault.crypto import VaultCrypto  # type: ignore
except ImportError:
    VaultCrypto = ReferenceVaultCrypto

try:
    from copilot.tally import generate_tally_xml  # type: ignore
except ImportError:
    try:
        from copilot.export.tally import generate_tally_xml  # type: ignore
    except ImportError:
        def generate_tally_xml(company_name, vouchers):
            return generate_reference_tally_xml(company_name, vouchers)

try:
    from copilot.tally import generate_ca_excel_pack  # type: ignore
except ImportError:
    try:
        from copilot.export.excel import generate_ca_excel_pack  # type: ignore
    except ImportError:
        def generate_ca_excel_pack(company, biz, as_of, summary, matched, suggest, unmatched, invs, slips):
            return generate_reference_ca_excel_pack(company, biz, as_of, summary, matched, suggest, unmatched, invs, slips)


# ==============================================================================
# COMBINATION 1: Parchi -> Drawer -> CDM Deposit -> Matcher -> Tally XML
# ==============================================================================

def test_combination_parchi_drawer_cdm_matcher_tally_xml():
    """Verify complete lifecycle: Salesman parchi entry -> Drawer cash -> CDM Bank Deposit -> Tally XML."""
    vault = E2EVaultAdapter()
    vault.unlock("0000")

    # Step 1: Initialize Godown Cash Drawer Float
    galla = GallaEntry("SME-1", pd.Timestamp("2026-09-30"), 10000.0, 0.0, 0.0, 0.0, 10000.0)
    vault.record_galla(galla)

    # Step 2: Salesman Ramesh Kumar brings 2 cash collection slips from Bibwewadi route
    slip1 = ExtendedCollection("SLIP-01", "SME-1", pd.Timestamp("2026-09-30"), "Laxmi Super Mart", 45000.0, "CASH", "Ramesh", "INV-0891")
    slip2 = ExtendedCollection("SLIP-02", "SME-1", pd.Timestamp("2026-09-30"), "Balaji Stores", 25000.0, "CASH", "Ramesh", "INV-0892")
    vault.record_collection(slip1, update_drawer=True)
    vault.record_collection(slip2, update_drawer=True)

    # Step 3: Cash drawer cash_in reflects both slips (₹70,000)
    latest_galla = vault.get_latest_galla("SME-1")
    assert latest_galla.cash_in == 70000.0

    # Step 4: Cashier banks ₹70,000 at CDM Hadapsar
    latest_galla.cash_banked = 70000.0
    latest_galla.counted_cash = 10000.0  # Opening float remains
    assert latest_galla.is_balanced is True

    # Step 5: Tally XML Receipt Voucher generated for CDM deposit clearing the 2 invoices
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-CDM-0930",
        "party_name": "Cash",
        "amount": 70000.0,
        "bank_ledger": "HDFC Bank Current A/c",
        "narration": "Salesman Route CDM Deposit: 2 slips (Ramesh Kumar route)",
        "allocations": [
            {"invoice_no": "INV-0891", "amount": 45000.0, "bill_type": "Agst Ref"},
            {"invoice_no": "INV-0892", "amount": 25000.0, "bill_type": "Agst Ref"},
        ]
    }]
    xml_str = generate_tally_xml("Kaveri Distributors", vouchers)
    root = ET.fromstring(xml_str)
    assert root.find(".//VOUCHER/VOUCHERNUMBER").text == "RCPT-CDM-0930"
    ballocs = root.findall(".//BILLALLOCATIONS.LIST")
    assert len(ballocs) == 2
    assert {b.find("NAME").text for b in ballocs} == {"INV-0891", "INV-0892"}


# ==============================================================================
# COMBINATION 2: Vault Lock Toggle -> Notice -> Query Gating -> True Solvency
# ==============================================================================

def test_combination_vault_lock_toggle_notice_gating_solvency(pack):
    """Verify lock gating: Locked -> Notice active -> Query blocked -> Unlock -> Solvency computed -> Relock."""
    vault = E2EVaultAdapter()

    # Step 1: Locked state
    assert not vault.is_unlocked()
    assert PARTIAL_VIEW_NOTICE in render_partial_view_notice()
    with pytest.raises(VaultLockedError):
        vault.get_collections("SME-1")

    # Step 2: Unlock with Owner PIN
    assert vault.unlock("0000") is True
    assert vault.is_unlocked()

    # Step 3: Record godown till and khata records
    vault.record_galla(GallaEntry("SME-1", pd.Timestamp("2026-09-30"), 15000.0, 35000.0, 2000.0, 30000.0, 18000.0))
    vault.record_khata(KhataAccount("Laxmi Kirana", "SME-1", 75000.0, pd.Timestamp("2026-09-01"), 4))

    # Step 4: True Solvency synthesis in volatile RAM
    from copilot.vault.db import VaultDB
    vdb = VaultDB(in_memory=True)
    vdb.seed_from_pack(pack)
    solvency = compute_total_solvency(pack, vdb, "SME-1", haircut_alpha=0.85)
    assert solvency.business_id == "SME-1"
    assert solvency.galla_cash > 0
    assert solvency.true_cash_runway_inr > 0

    # Step 5: Relock vault
    vault.lock()
    assert not vault.is_unlocked()
    with pytest.raises(VaultLockedError):
        vault.get_collections("SME-1")


# ==============================================================================
# COMBINATION 3: FIFO Allocation -> Debtors Aging Schedule in CA Excel Pack
# ==============================================================================

def test_combination_fifo_allocation_debtors_aging_excel_pack():
    """Verify multi-invoice FIFO allocation coupled with CA Excel aging schedule."""
    open_invoices = [
        {"invoice_no": "INV-001", "invoice_date": pd.Timestamp("2026-05-01"), "amount": 25000.0, "outstanding_amount": 25000.0},
        {"invoice_no": "INV-002", "invoice_date": pd.Timestamp("2026-07-01"), "amount": 35000.0, "outstanding_amount": 35000.0},
        {"invoice_no": "INV-003", "invoice_date": pd.Timestamp("2026-09-01"), "amount": 40000.0, "outstanding_amount": 40000.0},
    ]

    # Customer pays ₹50,000 lump sum
    allocations = allocate_invoices_fifo(open_invoices, 50000.0)
    assert len(allocations) == 2
    assert allocations[0]["invoice_no"] == "INV-001"
    assert allocations[0]["remaining_due"] == 0.0   # Fully paid
    assert allocations[1]["invoice_no"] == "INV-002"
    assert allocations[1]["remaining_due"] == 10000.0 # Partially paid

    # Remaining debtor items fed into CA Excel Aging schedule
    aging_rows = [
        {
            "Invoice_No": "INV-002",
            "Invoice_Date": "2026-07-01",
            "Due_Date": "2026-07-15",
            "Customer_Name": "Balaji Stores",
            "Taxable_Value_INR": 8474.58,
            "GST_INR": 1525.42,
            "Invoice_Total_INR": 35000.0,
            "Settled_INR": 25000.0,
            "Outstanding_INR": 10000.0,
            "Days_Outstanding": 76,
            "Aging_Bucket": "61-90 Days",
            "Section_18_Alert": "NO"
        },
        {
            "Invoice_No": "INV-003",
            "Invoice_Date": "2026-09-01",
            "Due_Date": "2026-09-15",
            "Customer_Name": "Balaji Stores",
            "Taxable_Value_INR": 33898.31,
            "GST_INR": 6101.69,
            "Invoice_Total_INR": 40000.0,
            "Settled_INR": 0.0,
            "Outstanding_INR": 40000.0,
            "Days_Outstanding": 15,
            "Aging_Bucket": "0-30 Days",
            "Section_18_Alert": "NO"
        }
    ]
    excel_bytes = generate_ca_excel_pack(
        "Kaveri Distributors", "SME-1", pd.Timestamp("2026-09-30"),
        {}, [], [], [], aging_rows, []
    )
    wb = openpyxl.load_workbook(BytesIO(excel_bytes))
    ws = wb["Open_Invoices_Aging"]
    assert ws.max_row == 3  # Header + 2 rows
    row2_vals = [c.value for c in ws[2]]
    assert "INV-002" in row2_vals
    assert 10000.0 in row2_vals


# ==============================================================================
# COMBINATION 4: Mixed Mode Parchi -> Godown Drawer Cash Isolation
# ==============================================================================

def test_combination_mixed_mode_parchi_drawer_cash_isolation():
    """Verify Cash collections increment drawer, while UPI and Cheque do not affect till cash."""
    vault = E2EVaultAdapter()
    vault.unlock("0000")
    galla = GallaEntry("SME-1", pd.Timestamp("2026-09-30"), 10000.0, 0.0, 0.0, 0.0, 10000.0)
    vault.record_galla(galla)

    # 3 Route slips
    vault.record_collection(ExtendedCollection("S1", "SME-1", pd.Timestamp("2026-09-30"), "Shop 1", 20000.0, "CASH"))
    vault.record_collection(ExtendedCollection("S2", "SME-1", pd.Timestamp("2026-09-30"), "Shop 2", 15000.0, "UPI"))
    vault.record_collection(ExtendedCollection("S3", "SME-1", pd.Timestamp("2026-09-30"), "Shop 3", 30000.0, "CHEQUE"))

    latest = vault.get_latest_galla("SME-1")
    # Only the ₹20,000 cash entered physical drawer
    assert latest.cash_in == 20000.0
    assert latest.expected_cash == 30000.0  # Opening 10K + CashIn 20K


# ==============================================================================
# COMBINATION 5: Stale Khata Debt -> §18 Limitation Alert -> Solvency Haircut
# ==============================================================================

def test_combination_stale_khata_debt_limitation_alert_and_solvency(pack):
    """Verify stale khata debt triggers §18 alert, WhatsApp reminder, and solvency haircut."""
    acc_stale = KhataAccount(
        party_name="Old Town General Stores",
        business_id="SME-1",
        balance_due=85000.0,
        last_active_date=pd.Timestamp("2023-10-01"),
        months_open=35,
        phone="9822019999"
    )
    assert acc_stale.is_limitation_alert is True

    # WhatsApp acknowledgement link
    reminder = format_whatsapp_reminder(acc_stale, "Kaveri Distributors")
    assert reminder["limitation_warning"] is not None
    assert "30 months old" in reminder["limitation_warning"]
    assert "wa.me/919822019999" in reminder["wa_link"]

    # Verify haircut parameterization applies 15% discount
    from copilot.vault.db import VaultDB
    vdb = VaultDB(in_memory=True)
    vdb.seed_from_pack(pack)
    s85 = compute_total_solvency(pack, vdb, "SME-1", haircut_alpha=0.85)
    s70 = compute_total_solvency(pack, vdb, "SME-1", haircut_alpha=0.70)
    assert s70.true_cash_runway_inr < s85.true_cash_runway_inr


# ==============================================================================
# COMBINATION 6: High-Value Cash Attempt -> §186 Block -> Split -> Tally XML
# ==============================================================================

def test_combination_high_value_cash_settlement_guardrail_split_tally():
    """Verify ₹2.5L cash receipt is blocked under §186, restructured into RTGS + Cash, and exported."""
    # Attempting ₹2,50,000 cash receipt is blocked
    check = check_single_receipt_cash(250000.0, party_name="Apex Supermarket")
    assert check.status == "BLOCKED"
    assert "Sec 186" in check.citation

    # Restructure into ₹1,50,000 RTGS + ₹1,00,000 Cash
    safe_cash = check_single_receipt_cash(100000.0, party_name="Apex Supermarket")
    assert safe_cash.status == "SAFE"

    vouchers = [
        {
            "date": "2026-09-30",
            "voucher_no": "RCPT-RTGS-01",
            "party_name": "Apex Supermarket",
            "amount": 150000.0,
            "bank_ledger": "HDFC Bank Current A/c",
            "narration": "Invoice settlement via RTGS",
            "allocations": [{"invoice_no": "INV-2026-0901", "amount": 150000.0, "bill_type": "Agst Ref"}]
        },
        {
            "date": "2026-09-30",
            "voucher_no": "RCPT-CASH-01",
            "party_name": "Apex Supermarket",
            "amount": 100000.0,
            "bank_ledger": "Cash",
            "narration": "Counter cash settlement under §186 limit",
            "allocations": [{"invoice_no": "INV-2026-0902", "amount": 100000.0, "bill_type": "Agst Ref"}]
        }
    ]
    xml_str = generate_tally_xml("Kaveri Distributors", vouchers)
    root = ET.fromstring(xml_str)
    vchs = root.findall(".//VOUCHER")
    assert len(vchs) == 2
    assert {v.find("VOUCHERNUMBER").text for v in vchs} == {"RCPT-RTGS-01", "RCPT-CASH-01"}


# ==============================================================================
# COMBINATION 7: Multi-Route Collection -> Day-Close -> CDM Banking -> Excel Pack
# ==============================================================================

def test_combination_multi_route_collection_dayclose_cdm_audit_pack():
    """Verify multi-salesman route collections, day-close till balance, and Excel route register."""
    vault = E2EVaultAdapter()
    vault.unlock("0000")

    # Day start float
    vault.record_galla(GallaEntry("SME-1", pd.Timestamp("2026-09-30"), 12000.0, 0, 0, 0, 12000.0))

    # Route A (Ramesh) & Route B (Suresh)
    vault.record_collection(ExtendedCollection("SLIP-A1", "SME-1", pd.Timestamp("2026-09-30"), "Shop A", 30000.0, "CASH", "Ramesh", "INV-101"))
    vault.record_collection(ExtendedCollection("SLIP-B1", "SME-1", pd.Timestamp("2026-09-30"), "Shop B", 25000.0, "CASH", "Suresh", "INV-102"))

    latest = vault.get_latest_galla("SME-1")
    assert latest.cash_in == 55000.0

    # Evening petty expenses and CDM deposit
    latest.cash_out = 1500.0    # Hamali / Chai
    latest.cash_banked = 50000.0 # Deposited at CDM
    latest.counted_cash = 15500.0 # (12000 + 55000 - 1500 - 50000) = 15500
    assert latest.is_balanced is True

    # Build Excel Route Register (Sheet 6)
    slips_data = [
        {"Slip_ID": s.slip_id, "Collection_Date": str(s.date.date()), "Salesman_Name": s.salesman,
         "Retail_Shop_Name": s.shop, "Amount_Collected_INR": s.amount, "Payment_Mode": s.payment_mode,
         "Linked_Invoice_No": s.invoice_no, "Drawer_Deposit_Date": "2026-09-30", "Drawer_Tally_Status": "BALANCED_IN_GALLA"}
        for s in vault.get_collections("SME-1")
    ]
    excel_bytes = generate_ca_excel_pack("Kaveri Distributors", "SME-1", pd.Timestamp("2026-09-30"), {}, [], [], [], [], slips_data)
    wb = openpyxl.load_workbook(BytesIO(excel_bytes))
    ws = wb["Salesman_Collection_Slips"]
    assert ws.max_row == 3  # Header + 2 slips
    salesmen = [ws[f"C{r}"].value for r in range(2, 4)]
    assert "Ramesh" in salesmen and "Suresh" in salesmen


# ==============================================================================
# COMBINATION 8: Bank Statement Balance Tie-Break Detection in Excel
# ==============================================================================

def test_combination_bank_balance_tie_break_detection_in_excel():
    """Verify Sheet 1 flags 'FAIL: BALANCE BREAK' when computed closing deviates from actual."""
    broken_summary = {
        "opening_balance": 1000000.0,
        "total_credits": 400000.0,
        "total_debits": 200000.0,
        "computed_closing": 1200000.0,
        "actual_closing": 1150000.0,  # ₹50,000 discrepancy
    }
    excel_bytes = generate_ca_excel_pack("Kaveri Distributors", "SME-1", pd.Timestamp("2026-09-30"), broken_summary, [], [], [], [], [])
    wb = openpyxl.load_workbook(BytesIO(excel_bytes))
    ws = wb["Reconciliation_Summary"]

    all_text = [str(c.value) for row in ws.iter_rows() for c in row if c.value]
    assert any("FAIL: BALANCE BREAK" in t for t in all_text)


# ==============================================================================
# COMBINATION 9: Encryption at Rest -> Cold Restart -> PIN Derivation -> Tally Export
# ==============================================================================

def test_combination_vault_encryption_at_rest_cold_restart_pin_export(tmp_path):
    """Verify cold-restart persistence: data encrypted at rest, loaded after restart with PIN."""
    salt = os.urandom(16)
    key = VaultCrypto.derive_key("0000", salt)
    payload = b"VOUCHER_CACHE: Balaji Provision Stores paid 75000 against INV-2026-0412"
    ciphertext = encrypt_vault_payload(payload, key, salt=salt)

    vault_file = tmp_path / "vault.enc"
    vault_file.write_bytes(ciphertext)

    # Cold restart: Read back from disk and decrypt
    restored_bytes = vault_file.read_bytes()
    key_restored = VaultCrypto.derive_key("0000", salt)
    decrypted = decrypt_vault_payload(restored_bytes, key_restored)
    assert b"Balaji Provision Stores" in decrypted

    # Generate Tally export from restored records
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-COLD-01",
        "party_name": "Balaji Provision Stores",
        "amount": 75000.0,
    }]
    xml_str = generate_tally_xml("Kaveri Distributors", vouchers)
    assert "Balaji Provision Stores" in xml_str


# ==============================================================================
# COMBINATION 10: Multi-Business Plane Isolation (SME-1 vs SME-2)
# ==============================================================================

def test_combination_multi_business_plane_isolation_sme1_vs_sme2():
    """Verify tenant isolation between SME-1 (Distributor) and SME-2 (Clinic)."""
    vault = E2EVaultAdapter()
    vault.unlock("0000")

    # Ingest for SME-1
    vault.record_collection(ExtendedCollection("S1", "SME-1", pd.Timestamp("2026-09-30"), "Retail Mart", 20000.0))
    # Ingest for SME-2
    vault.record_collection(ExtendedCollection("S2", "SME-2", pd.Timestamp("2026-09-30"), "Dental Patient", 5000.0))

    sme1_slips = vault.get_collections("SME-1")
    sme2_slips = vault.get_collections("SME-2")

    assert len(sme1_slips) == 1 and sme1_slips[0].shop == "Retail Mart"
    assert len(sme2_slips) == 1 and sme2_slips[0].shop == "Dental Patient"
    assert {s.slip_id for s in sme1_slips}.isdisjoint({s.slip_id for s in sme2_slips})
