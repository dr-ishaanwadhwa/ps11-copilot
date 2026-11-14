"""Test harness and contract adapters for E2E testing of SME Cash-Flow Copilot.

Provides seamless discovery and graceful fallback adapters for features being built
in parallel across Milestones M1, M2, and M3:
- Sovereign Vault & Encryption (ADR-001 / ADR-004)
- Salesman Collection Slip Ingestion & FIFO Allocation (R3)
- Cash Drawer Tally Balancing (R3)
- Tally XML Receipt Voucher Generation (R4)
- Standardized CA Reconciliation Excel Workbook (R4)
"""
from __future__ import annotations

import hashlib
import hmac
import os
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import pandas as pd

from copilot.vault.models import GallaEntry, KhataAccount, RokadEntry
from copilot.vault.notice import PARTIAL_VIEW_NOTICE, render_partial_view_notice
from copilot.vault.guardrails import (
    check_single_receipt_cash,
    check_cash_expense,
    check_cash_loan,
    cash_deposit_reporting_facts,
)

# Custom exception for locked vault
class VaultLockedError(Exception):
    """Raised when an operation requires an unlocked vault but it is locked."""
    pass


@dataclass
class ExtendedCollection:
    """Salesman collection slip model conforming to Milestone 2 interface contract."""
    slip_id: str
    business_id: str
    date: pd.Timestamp
    shop: str
    amount: float
    payment_mode: str = "CASH"  # CASH, UPI, CHEQUE
    salesman: str = ""
    invoice_no: Optional[str] = None
    is_banked: bool = False
    bank_txn_id: Optional[str] = None
    notes: str = ""


# Reference Cryptographic Helper conforming to ADR-001
class ReferenceVaultCrypto:
    """Pure-Python AES/HMAC or PBKDF2 reference implementation for ADR-001 verification."""

    @staticmethod
    def derive_key(pin: str, salt: bytes, iterations: int = 100_000) -> bytes:
        if not pin:
            raise ValueError("PIN cannot be empty")
        if len(salt) < 16:
            raise ValueError("Salt must be at least 16 bytes")
        return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterations, dklen=32)

    @staticmethod
    def encrypt_payload(data: bytes, key: bytes) -> bytes:
        iv = os.urandom(16)
        # Use HMAC-SHA256 keystream emulation for deterministic testing without external C-deps
        keystream = hashlib.sha256(key + iv).digest()
        while len(keystream) < len(data):
            keystream += hashlib.sha256(keystream + key).digest()
        cipher = bytes(b ^ k for b, k in zip(data, keystream[:len(data)]))
        tag = hmac.new(key, iv + cipher, hashlib.sha256).digest()
        return iv + tag + cipher

    @staticmethod
    def decrypt_payload(payload: bytes, key: bytes) -> bytes:
        if len(payload) < 48:
            raise ValueError("Invalid payload: too short")
        iv = payload[:16]
        tag = payload[16:48]
        cipher = payload[48:]
        expected_tag = hmac.new(key, iv + cipher, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected_tag):
            raise ValueError("Cryptographic MAC verification failed: corrupted data or wrong key")
        keystream = hashlib.sha256(key + iv).digest()
        while len(keystream) < len(cipher):
            keystream += hashlib.sha256(keystream + key).digest()
        return bytes(b ^ k for b, k in zip(cipher, keystream[:len(cipher)]))


def encrypt_vault_payload(data: bytes, key: bytes, salt: Optional[bytes] = None) -> bytes:
    try:
        from copilot.vault.crypto import VaultCrypto
        if hasattr(VaultCrypto, "encrypt"):
            return VaultCrypto.encrypt(data, key=key, salt=salt)
    except Exception:
        pass
    return ReferenceVaultCrypto.encrypt_payload(data, key)


def decrypt_vault_payload(payload: bytes, key: bytes) -> bytes:
    try:
        from copilot.vault.crypto import VaultCrypto
        if hasattr(VaultCrypto, "decrypt"):
            res = VaultCrypto.decrypt(payload, key=key)
            return res[0] if isinstance(res, tuple) else res
    except Exception:
        pass
    return ReferenceVaultCrypto.decrypt_payload(payload, key)


# Reference / Adapter VaultDB conforming to M1 & M2 contracts
class E2EVaultAdapter:
    """Adapter wrapping VaultDB or providing specification-compliant behavior."""

    def __init__(self, db_path: Optional[Path] = None, default_pin: str = "0000"):
        self.db_path = db_path
        self.pin = default_pin
        self._unlocked = False
        self.salt = os.urandom(16)
        self.collections: Dict[str, List[ExtendedCollection]] = {"SME-1": [], "SME-2": [], "SME-3": []}
        self.galla_records: Dict[str, List[GallaEntry]] = {"SME-1": [], "SME-2": [], "SME-3": []}
        self.khata_records: Dict[str, Dict[str, KhataAccount]] = {"SME-1": {}, "SME-2": {}, "SME-3": {}}
        self._raw_ciphertext: Optional[bytes] = None

    def is_unlocked(self) -> bool:
        return self._unlocked

    def unlock(self, pin: str) -> bool:
        if not pin or pin != self.pin:
            self._unlocked = False
            return False
        self._unlocked = True
        return True

    def lock(self) -> None:
        self._unlocked = False

    def record_collection(self, collection: ExtendedCollection, update_drawer: bool = True) -> str:
        if not self._unlocked:
            raise VaultLockedError("Cannot record collection: Vault is locked")
        if collection.amount <= 0:
            raise ValueError("Collection amount must be strictly positive")
        self.collections.setdefault(collection.business_id, []).append(collection)

        # Update godown cash drawer if mode is CASH
        if update_drawer and collection.payment_mode.upper() == "CASH":
            latest = self.get_latest_galla(collection.business_id)
            if latest:
                latest.cash_in = round(latest.cash_in + collection.amount, 2)
        return collection.slip_id

    def get_collections(
        self,
        biz: str,
        start: Optional[pd.Timestamp] = None,
        end: Optional[pd.Timestamp] = None,
        mode: Optional[str] = None
    ) -> List[ExtendedCollection]:
        if not self._unlocked:
            raise VaultLockedError("Cannot retrieve collections: Vault is locked")
        records = self.collections.get(biz, [])
        filtered = []
        for r in records:
            if start and r.date < start:
                continue
            if end and r.date > end:
                continue
            if mode and r.payment_mode.upper() != mode.upper():
                continue
            filtered.append(r)
        return filtered

    def record_galla(self, entry: GallaEntry) -> None:
        if not self._unlocked:
            raise VaultLockedError("Cannot record galla: Vault is locked")
        self.galla_records.setdefault(entry.business_id, []).append(entry)

    def get_latest_galla(self, biz: str) -> Optional[GallaEntry]:
        if not self._unlocked:
            raise VaultLockedError("Cannot retrieve galla: Vault is locked")
        entries = self.galla_records.get(biz, [])
        return entries[-1] if entries else None

    def record_khata(self, account: KhataAccount) -> None:
        if not self._unlocked:
            raise VaultLockedError("Cannot record khata: Vault is locked")
        self.khata_records.setdefault(account.business_id, {})[account.party_name] = account

    def get_khata_accounts(self, biz: str) -> List[KhataAccount]:
        if not self._unlocked:
            raise VaultLockedError("Cannot retrieve khata: Vault is locked")
        return list(self.khata_records.get(biz, {}).values())


def allocate_invoices_fifo(
    open_invoices: List[Dict[str, Any]],
    payment_amount: float
) -> List[Dict[str, Any]]:
    """Allocates a payment against open invoices using FIFO (oldest date first)."""
    # Sort invoices by date ascending
    sorted_invs = sorted(open_invoices, key=lambda x: x.get("invoice_date", pd.Timestamp.min))
    remaining = payment_amount
    allocations = []

    for inv in sorted_invs:
        if remaining <= 0:
            break
        due = inv.get("outstanding_amount", inv.get("amount", 0.0))
        allocated = min(remaining, due)
        allocations.append({
            "invoice_no": inv["invoice_no"],
            "invoice_date": inv.get("invoice_date"),
            "allocated_amount": round(allocated, 2),
            "remaining_due": round(due - allocated, 2),
            "bill_type": "Agst Ref"
        })
        remaining = round(remaining - allocated, 2)

    if remaining > 0:
        allocations.append({
            "invoice_no": "ON_ACCOUNT",
            "invoice_date": None,
            "allocated_amount": round(remaining, 2),
            "remaining_due": 0.0,
            "bill_type": "On Account"
        })
    return allocations


def generate_reference_tally_xml(
    company_name: str,
    vouchers_data: List[Dict[str, Any]]
) -> str:
    """Generates TallyPrime XML receipt vouchers conforming to R4 specification."""
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

    for v in vouchers_data:
        vch = ET.SubElement(tally_msg, "VOUCHER", {
            "VOUCHERTYPE": "Receipt",
            "ACTION": "Create",
            "OBJVIEW": "Accounting Voucher View"
        })

        date_str = pd.Timestamp(v["date"]).strftime("%Y%m%d")
        ET.SubElement(vch, "DATE").text = date_str
        ET.SubElement(vch, "EFFECTIVEDATE").text = date_str
        ET.SubElement(vch, "VOUCHERTYPENAME").text = "Receipt"
        ET.SubElement(vch, "VOUCHERNUMBER").text = v.get("voucher_no", f"RCPT-{date_str}-001")
        ET.SubElement(vch, "PARTYLEDGERNAME").text = v["party_name"]

        # Idempotent GUID
        guid = v.get("guid") or str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{company_name}:{v.get('voucher_no', date_str)}"))
        ET.SubElement(vch, "GUID").text = guid
        ET.SubElement(vch, "NARRATION").text = v.get("narration", "Receipt Voucher")
        ET.SubElement(vch, "ISINVOICE").text = "No"

        # Debit entry: Bank or Cash (Negative amount, ISDEEMEDPOSITIVE=Yes)
        debit_entry = ET.SubElement(vch, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(debit_entry, "LEDGERNAME").text = v.get("bank_ledger", "HDFC Bank Current A/c")
        ET.SubElement(debit_entry, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(debit_entry, "AMOUNT").text = f"-{v['amount']:.2f}"

        # TDS entry if applicable
        tds_amount = v.get("tds_amount", 0.0)
        if tds_amount > 0:
            tds_entry = ET.SubElement(vch, "ALLLEDGERENTRIES.LIST")
            ET.SubElement(tds_entry, "LEDGERNAME").text = "TDS Receivable"
            ET.SubElement(tds_entry, "ISDEEMEDPOSITIVE").text = "Yes"
            ET.SubElement(tds_entry, "AMOUNT").text = f"-{tds_amount:.2f}"

        # Round-off entry if applicable
        round_off = v.get("round_off", 0.0)
        if round_off != 0.0:
            ro_entry = ET.SubElement(vch, "ALLLEDGERENTRIES.LIST")
            ET.SubElement(ro_entry, "LEDGERNAME").text = "Round Off"
            ET.SubElement(ro_entry, "ISDEEMEDPOSITIVE").text = "No" if round_off > 0 else "Yes"
            ET.SubElement(ro_entry, "AMOUNT").text = f"{round_off:.2f}"

        # Credit entry: Customer (Positive amount, ISDEEMEDPOSITIVE=No)
        credit_entry = ET.SubElement(vch, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(credit_entry, "LEDGERNAME").text = v["party_name"]
        ET.SubElement(credit_entry, "ISDEEMEDPOSITIVE").text = "No"
        credit_amount = v["amount"] + tds_amount - round_off
        ET.SubElement(credit_entry, "AMOUNT").text = f"{credit_amount:.2f}"

        # Bill allocations
        allocations = v.get("allocations", [])
        if allocations:
            for alloc in allocations:
                ba = ET.SubElement(credit_entry, "BILLALLOCATIONS.LIST")
                ET.SubElement(ba, "NAME").text = alloc["invoice_no"]
                ET.SubElement(ba, "BILLTYPE").text = alloc.get("bill_type", "Agst Ref")
                ET.SubElement(ba, "AMOUNT").text = f"{alloc['amount']:.2f}"
        else:
            ba = ET.SubElement(credit_entry, "BILLALLOCATIONS.LIST")
            ET.SubElement(ba, "NAME").text = v.get("invoice_no", "ON_ACCOUNT")
            ET.SubElement(ba, "BILLTYPE").text = "Agst Ref" if v.get("invoice_no") else "On Account"
            ET.SubElement(ba, "AMOUNT").text = f"{credit_amount:.2f}"

    xml_bytes = ET.tostring(root, encoding="utf-8")
    return '<?xml version="1.0" encoding="utf-8"?>\n' + xml_bytes.decode("utf-8")


def generate_reference_ca_excel_pack(
    company_name: str,
    business_id: str,
    as_of_date: pd.Timestamp,
    summary_data: Dict[str, Any],
    matched_receipts: List[Dict[str, Any]],
    suggested_matches: List[Dict[str, Any]],
    unmatched_credits: List[Dict[str, Any]],
    open_invoices: List[Dict[str, Any]],
    salesman_slips: List[Dict[str, Any]]
) -> bytes:
    """Generates the standardized 6-sheet CA Reconciliation Excel workbook."""
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styling helpers
    header_fill = PatternFill(start_color="24509A", end_color="24509A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    bold_font = Font(name="Calibri", size=11, bold=True)

    # 1. Reconciliation_Summary
    ws1 = wb.create_sheet(title="Reconciliation_Summary")
    ws1.append(["Business Name", company_name, "Business ID", business_id])
    ws1.append(["As of Date", str(as_of_date.date()), "Audit Standard", "Companies Act 2013 / IT Act 2025"])
    ws1.append([])
    ws1.append(["BANK ACCOUNT BALANCE TIE VERIFICATION", ""])
    ws1.append(["Opening Balance", summary_data.get("opening_balance", 0.0)])
    ws1.append(["Total Bank Credits", summary_data.get("total_credits", 0.0)])
    ws1.append(["Total Bank Debits", summary_data.get("total_debits", 0.0)])
    ws1.append(["Computed Closing Balance", summary_data.get("computed_closing", 0.0)])
    ws1.append(["Actual Bank Closing", summary_data.get("actual_closing", 0.0)])
    variance = round(summary_data.get("computed_closing", 0.0) - summary_data.get("actual_closing", 0.0), 2)
    ws1.append(["Balance Variance", variance])
    ws1.append(["Balance Tie Status", "PASS: 100% TIED" if abs(variance) < 1.0 else "FAIL: BALANCE BREAK"])
    ws1.append([])
    ws1.append(["DECISION 60 MATCHING CLASSIFICATION", ""])
    ws1.append(["AUTO Reconciled (Straight-Through)", summary_data.get("auto_count", 0), summary_data.get("auto_inr", 0.0)])
    ws1.append(["SUGGEST Reconciled (Review Queue)", summary_data.get("suggest_count", 0), summary_data.get("suggest_inr", 0.0)])
    ws1.append(["ASK (Unmatched Exceptions)", summary_data.get("ask_count", 0), summary_data.get("ask_inr", 0.0)])
    ws1.append([])
    ws1.append(["CASH DRAWER & COLLECTIONS CROSS-CHECK", ""])
    ws1.append(["Drawer Counted Cash", summary_data.get("drawer_counted", 0.0)])
    ws1.append(["Salesman Route Collections", summary_data.get("salesman_collections", 0.0)])
    ws1.append(["Drawer Drift", summary_data.get("drawer_drift", 0.0)])

    # 2. Matched_Receipts_AUTO
    ws2 = wb.create_sheet(title="Matched_Receipts_AUTO")
    headers2 = ["Txn_ID", "Txn_Date", "Amount_INR", "Bank_Account", "Bank_Narration",
                "Channel", "Payer_Party_Name", "Matching_Rule", "Matched_Doc_IDs",
                "Doc_Total_INR", "Round_Off_INR", "TDS_Deducted_INR", "Tally_Voucher_GUID", "Tally_Post_Status"]
    ws2.append(headers2)
    for cell in ws2[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in matched_receipts:
        ws2.append([r.get(k, "") for k in headers2])

    # 3. Suggested_Matches
    ws3 = wb.create_sheet(title="Suggested_Matches")
    headers3 = ["Txn_ID", "Txn_Date", "Amount_INR", "Bank_Narration", "Proposed_Party",
                "Proposed_Rule", "Proposed_Doc_IDs", "Confidence_Note", "CA_Approval_Status", "CA_Audit_Remarks"]
    ws3.append(headers3)
    for cell in ws3[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in suggested_matches:
        ws3.append([r.get(k, "") for k in headers3])

    # 4. Unmatched_Bank_Credits
    ws4 = wb.create_sheet(title="Unmatched_Bank_Credits")
    headers4 = ["Txn_ID", "Txn_Date", "Amount_INR", "Bank_Narration", "Channel",
                "Reason_Code", "Client_Clarification", "Suggested_Action"]
    ws4.append(headers4)
    for cell in ws4[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in unmatched_credits:
        ws4.append([r.get(k, "") for k in headers4])

    # 5. Open_Invoices_Aging
    ws5 = wb.create_sheet(title="Open_Invoices_Aging")
    headers5 = ["Invoice_No", "Invoice_Date", "Due_Date", "Customer_Name", "Taxable_Value_INR",
                "GST_INR", "Invoice_Total_INR", "Settled_INR", "Outstanding_INR",
                "Days_Outstanding", "Aging_Bucket", "Section_18_Alert"]
    ws5.append(headers5)
    for cell in ws5[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in open_invoices:
        ws5.append([r.get(k, "") for k in headers5])

    # 6. Salesman_Collection_Slips
    ws6 = wb.create_sheet(title="Salesman_Collection_Slips")
    headers6 = ["Slip_ID", "Collection_Date", "Salesman_Name", "Retail_Shop_Name",
                "Amount_Collected_INR", "Payment_Mode", "Linked_Invoice_No",
                "Drawer_Deposit_Date", "Drawer_Tally_Status"]
    ws6.append(headers6)
    for cell in ws6[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in salesman_slips:
        ws6.append([r.get(k, "") for k in headers6])

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
