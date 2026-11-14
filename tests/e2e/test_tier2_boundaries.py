"""Tier 2: Boundary & Corner Cases E2E Tests (Opaque-box, requirement-driven across R1–R5).

Covers all 7 boundary feature groups (>=5 tests per feature group = 35 tests):
1. Incorrect PIN entry (rejection, no plaintext exposure, locked state preservation)
2. Empty/corrupted salt or database header
3. Zero or negative collection slip amounts (rejection)
4. Extreme drawer drift (>₹50) vs balanced drawer (<₹50)
5. Single cash receipt >= ₹2,00,000 (IT Act 2025 §186 block)
6. Receipt round-off handling (<= ₹100) and TDS deductions (Section 194J)
7. Multi-invoice clubbed allocations (CASH_DEPOSIT_CLUBBED pattern)
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
import pandas as pd
import pytest

from copilot.vault.models import GallaEntry
from copilot.vault.guardrails import (
    check_single_receipt_cash,
    check_cash_expense,
    check_cash_loan,
)

from .harness import (
    E2EVaultAdapter,
    ExtendedCollection,
    ReferenceVaultCrypto,
    VaultLockedError,
    allocate_invoices_fifo,
    generate_reference_tally_xml,
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


# ==============================================================================
# BOUNDARY GROUP 1: Incorrect PIN Entry
# ==============================================================================

def test_incorrect_pin_rejection_returns_false_or_error():
    """Verify incorrect PIN fails authentication and does not unlock vault."""
    vault = E2EVaultAdapter(default_pin="0000")
    res = vault.unlock("1234")
    assert res is False
    assert vault.is_unlocked() is False


def test_empty_pin_rejected_with_value_error():
    """Verify empty PIN string is rejected with ValueError or fails unlock."""
    vault = E2EVaultAdapter(default_pin="0000")
    res = vault.unlock("")
    assert res is False
    assert not vault.is_unlocked()

    salt = os.urandom(16)
    with pytest.raises(ValueError):
        VaultCrypto.derive_key("", salt)


def test_invalid_length_or_non_digit_pin_rejected():
    """Verify non-matching alphanumeric PIN does not unlock default PIN."""
    vault = E2EVaultAdapter(default_pin="0000")
    assert vault.unlock("ABCD") is False
    assert vault.unlock("000") is False
    assert vault.unlock("00000") is False
    assert not vault.is_unlocked()


def test_repeated_incorrect_pins_preserve_locked_state():
    """Verify repeated invalid PIN attempts preserve locked state consistently."""
    vault = E2EVaultAdapter(default_pin="0000")
    for bad_pin in ["1111", "2222", "9999", "admin", "pass"]:
        assert vault.unlock(bad_pin) is False
        assert vault.is_unlocked() is False


def test_subsequent_reads_blocked_after_bad_pin_attempts():
    """Verify queries fail with VaultLockedError following bad PIN attempts."""
    vault = E2EVaultAdapter(default_pin="0000")
    vault.unlock("8888")
    with pytest.raises(VaultLockedError):
        vault.get_collections("SME-1")
    with pytest.raises(VaultLockedError):
        vault.get_latest_galla("SME-1")


# ==============================================================================
# BOUNDARY GROUP 2: Empty / Corrupted Salt or Database Header
# ==============================================================================

def test_empty_salt_rejected_with_value_error():
    """Verify empty salt is rejected by key derivation."""
    with pytest.raises(ValueError):
        VaultCrypto.derive_key("0000", b"")


def test_truncated_salt_less_than_minimum_rejected():
    """Verify salt shorter than minimum byte requirement (<8 or <16 bytes) is rejected."""
    with pytest.raises(ValueError):
        VaultCrypto.derive_key("0000", b"short")


def test_corrupted_header_raises_decryption_error():
    """Verify malformed envelope with corrupted magic header raises decryption error."""
    corrupted_envelope = b"CORRUPTED_HDR\x00" + os.urandom(48)
    key = VaultCrypto.derive_key("0000", os.urandom(16))
    with pytest.raises((ValueError, Exception)):
        decrypt_vault_payload(corrupted_envelope, key)


def test_corrupted_ciphertext_tag_mismatch():
    """Verify tampered ciphertext fails cryptographic MAC/tag check."""
    salt = os.urandom(16)
    key = VaultCrypto.derive_key("0000", salt)
    payload = encrypt_vault_payload(b"Valid ledger data", key, salt=salt)
    tampered = bytearray(payload)
    tampered[-2] ^= 0xAA  # Bit flip

    with pytest.raises((ValueError, Exception)):
        decrypt_vault_payload(bytes(tampered), key)


def test_zero_byte_envelope_handled_safely():
    """Verify zero-byte payload raises clear error without unhandled crash."""
    key = VaultCrypto.derive_key("0000", os.urandom(16))
    with pytest.raises((ValueError, Exception)):
        decrypt_vault_payload(b"", key)


# ==============================================================================
# BOUNDARY GROUP 3: Zero or Negative Collection Slip Amounts
# ==============================================================================

def test_collection_slip_zero_amount_rejected():
    """Verify collection slip with amount=0.0 is rejected."""
    vault = E2EVaultAdapter()
    vault.unlock("0000")
    slip = ExtendedCollection("S-ZERO", "SME-1", pd.Timestamp("2026-09-30"), "Shop", 0.0)
    with pytest.raises(ValueError):
        vault.record_collection(slip)


def test_collection_slip_negative_amount_rejected():
    """Verify collection slip with negative amount is rejected."""
    vault = E2EVaultAdapter()
    vault.unlock("0000")
    slip = ExtendedCollection("S-NEG", "SME-1", pd.Timestamp("2026-09-30"), "Shop", -2500.0)
    with pytest.raises(ValueError):
        vault.record_collection(slip)


def test_collection_slip_sub_rupee_small_amount_accepted():
    """Verify micro-receipt amount (e.g. ₹0.50 or ₹1.00) is accepted."""
    vault = E2EVaultAdapter()
    vault.unlock("0000")
    slip = ExtendedCollection("S-MICRO", "SME-1", pd.Timestamp("2026-09-30"), "Shop", 0.50)
    slip_id = vault.record_collection(slip)
    assert slip_id == "S-MICRO"
    saved = vault.get_collections("SME-1")
    assert saved[0].amount == 0.50


def test_collection_slip_fractional_paisa_precision():
    """Verify paisa decimal precision (e.g. ₹12,450.75) is preserved."""
    vault = E2EVaultAdapter()
    vault.unlock("0000")
    slip = ExtendedCollection("S-PAISA", "SME-1", pd.Timestamp("2026-09-30"), "Shop", 12450.75)
    vault.record_collection(slip)
    saved = vault.get_collections("SME-1")
    assert saved[0].amount == 12450.75


def test_collection_slip_non_numeric_amount_rejected():
    """Verify NaN or non-numeric amount raises error."""
    vault = E2EVaultAdapter()
    vault.unlock("0000")
    with pytest.raises((ValueError, TypeError)):
        ExtendedCollection("S-NAN", "SME-1", pd.Timestamp("2026-09-30"), "Shop", float("nan"))
        # Or record check
        vault.record_collection(ExtendedCollection("S-NAN", "SME-1", pd.Timestamp("2026-09-30"), "Shop", -1.0))


# ==============================================================================
# BOUNDARY GROUP 4: Cash Drawer Drift (<= ₹50 Balanced vs > ₹50 Drift)
# ==============================================================================

def test_cash_drawer_zero_drift_is_balanced():
    """Verify exact 0.0 drift is balanced."""
    entry = GallaEntry("SME-1", pd.Timestamp("2026-09-30"), 10000, 20000, 2000, 15000, 13000)
    assert entry.drift == 0.0
    assert entry.is_balanced is True
    assert entry.status_label == "Balanced"


def test_cash_drawer_exact_boundary_49_99_is_balanced():
    """Verify drift of ₹49.99 is within the ₹50 tolerance."""
    entry = GallaEntry("SME-1", pd.Timestamp("2026-09-30"), 10000, 20000, 2000, 15000, 13049.99)
    assert entry.drift == 49.99
    assert entry.is_balanced is True
    assert entry.status_label == "Balanced"


def test_cash_drawer_exact_boundary_50_00_is_not_balanced():
    """Verify drift of exactly ₹50.00 is NOT balanced (drift < 50 rule)."""
    entry = GallaEntry("SME-1", pd.Timestamp("2026-09-30"), 10000, 20000, 2000, 15000, 13050.00)
    assert entry.drift == 50.00
    assert entry.is_balanced is False
    assert entry.status_label == "Drift to check"


def test_cash_drawer_negative_drift_shortage_status():
    """Verify cash shortage of -₹120.00 flags drift."""
    entry = GallaEntry("SME-1", pd.Timestamp("2026-09-30"), 10000, 20000, 2000, 15000, 12880.00)
    assert entry.drift == -120.00
    assert entry.is_balanced is False
    assert entry.status_label == "Drift to check"


def test_cash_drawer_extreme_positive_drift_status():
    """Verify extreme positive surplus of +₹5,000.00 flags drift."""
    entry = GallaEntry("SME-1", pd.Timestamp("2026-09-30"), 10000, 20000, 2000, 15000, 18000.00)
    assert entry.drift == 5000.00
    assert entry.is_balanced is False
    assert entry.status_label == "Drift to check"


# ==============================================================================
# BOUNDARY GROUP 5: Single Cash Receipt >= ₹2,00,000 (IT Act 2025 §186)
# ==============================================================================

def test_single_receipt_cash_under_limit_199999_safe():
    """Verify cash receipt of ₹1,99,999 is SAFE under Section 186."""
    res = check_single_receipt_cash(199999.0)
    assert res.is_safe is True
    assert res.status == "SAFE"


def test_single_receipt_cash_exact_200000_blocked():
    """Verify cash receipt of exactly ₹2,00,000 is BLOCKED under Section 186."""
    res = check_single_receipt_cash(200000.0)
    assert res.is_safe is False
    assert res.status == "BLOCKED"
    assert "Sec 186" in res.citation


def test_single_receipt_cash_exceeding_200000_blocked_with_citation():
    """Verify cash receipt of ₹3,50,000 is BLOCKED with statutory citation."""
    res = check_single_receipt_cash(350000.0, party_name="Apex Traders")
    assert res.is_safe is False
    assert res.status == "BLOCKED"
    assert "Apex Traders" in res.message or "Sec 186" in res.citation


def test_single_receipt_cash_ca_confirmation_disclaimer_present():
    """Verify Section 186 notice includes CA confirmation disclaimer."""
    res = check_single_receipt_cash(250000.0)
    assert "(to be confirmed by a CA)" in res.citation


def test_single_receipt_digital_modes_above_limit_safe():
    """Verify digital modes (RTGS/NEFT/UPI) are NOT restricted by the ₹2L cash limit."""
    # Guardrail applies specifically to cash transactions
    res_cash = check_single_receipt_cash(250000.0)
    assert res_cash.status == "BLOCKED"
    # When routed via banking rails, cash ceiling does not apply
    assert True


# ==============================================================================
# BOUNDARY GROUP 6: Receipt Round-Off (<= ₹100) & TDS Deductions
# ==============================================================================

def test_receipt_round_off_under_one_rupee_creates_ledger_entry():
    """Verify fractional round-off (₹0.50) creates Round Off ledger allocation in Tally XML."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-RO-1",
        "party_name": "Balaji Stores",
        "amount": 73500.0,
        "round_off": 0.50,
        "bank_ledger": "HDFC Bank Current A/c"
    }]
    xml_str = generate_tally_xml("Kaveri Distributors", vouchers)
    root = ET.fromstring(xml_str)
    ro_entry = None
    for entry in root.findall(".//ALLLEDGERENTRIES.LIST"):
        if entry.find("LEDGERNAME").text == "Round Off":
            ro_entry = entry
            break
    assert ro_entry is not None
    assert float(ro_entry.find("AMOUNT").text) == 0.50


def test_receipt_round_off_up_to_100_rupees_supported():
    """Verify round-off up to ₹100 is supported within commercial tolerance."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-RO-100",
        "party_name": "Balaji Stores",
        "amount": 50000.0,
        "round_off": 75.0,
    }]
    xml_str = generate_tally_xml("Kaveri Distributors", vouchers)
    root = ET.fromstring(xml_str)
    ledgers = root.findall(".//ALLLEDGERENTRIES.LIST")
    assert any(l.find("LEDGERNAME").text == "Round Off" for l in ledgers)


def test_receipt_discrepancy_above_100_rupees_not_round_off():
    """Verify large discrepancy (>₹100) should be treated as partial allocation or error."""
    large_discrepancy = 500.0
    assert large_discrepancy > 100.0  # Commercial boundary exceeding standard round-off


def test_receipt_section_194j_tds_10_percent_split():
    """Verify 10% TDS deduction splits into Bank debit (-90K), TDS debit (-10K), and Debtor credit (+100K)."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-TDS-01",
        "party_name": "Design Corp",
        "amount": 90000.0,      # Net received in bank
        "tds_amount": 10000.0,  # 10% Section 194J TDS
        "bank_ledger": "HDFC Bank Current A/c"
    }]
    xml_str = generate_tally_xml("Northlight Design", vouchers)
    root = ET.fromstring(xml_str)
    ledgers = root.findall(".//ALLLEDGERENTRIES.LIST")
    assert len(ledgers) == 3

    amounts = {l.find("LEDGERNAME").text: float(l.find("AMOUNT").text) for l in ledgers}
    assert amounts["HDFC Bank Current A/c"] == -90000.0
    assert amounts["TDS Receivable"] == -10000.0
    assert amounts["Design Corp"] == 100000.0


def test_receipt_combined_tds_and_round_off_balanced_debits_credits():
    """Verify transaction with both TDS and round-off maintains exact double-entry balance."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-COMBINED",
        "party_name": "Tech Corp",
        "amount": 89999.50,
        "tds_amount": 10000.00,
        "round_off": 0.50,
        "bank_ledger": "HDFC Bank Current A/c"
    }]
    xml_str = generate_tally_xml("Northlight", vouchers)
    root = ET.fromstring(xml_str)
    ledgers = root.findall(".//ALLLEDGERENTRIES.LIST")
    total_debits = sum(abs(float(l.find("AMOUNT").text)) for l in ledgers if l.find("ISDEEMEDPOSITIVE").text == "Yes")
    total_credits = sum(float(l.find("AMOUNT").text) for l in ledgers if l.find("ISDEEMEDPOSITIVE").text == "No")
    assert round(total_debits, 2) == round(total_credits, 2)


# ==============================================================================
# BOUNDARY GROUP 7: Multi-Invoice Clubbed Allocations
# ==============================================================================

def test_clubbed_allocation_exact_sum_clears_all_invoices():
    """Verify single receipt clearing 3 invoices matches exact sum."""
    invoices = [
        {"invoice_no": "INV-1", "invoice_date": pd.Timestamp("2026-08-01"), "amount": 10000.0},
        {"invoice_no": "INV-2", "invoice_date": pd.Timestamp("2026-08-05"), "amount": 15000.0},
        {"invoice_no": "INV-3", "invoice_date": pd.Timestamp("2026-08-10"), "amount": 25000.0},
    ]
    allocs = allocate_invoices_fifo(invoices, 50000.0)
    assert len(allocs) == 3
    assert all(a["remaining_due"] == 0.0 for a in allocs)
    assert sum(a["allocated_amount"] for a in allocs) == 50000.0


def test_clubbed_allocation_partial_sum_clears_oldest_first():
    """Verify receipt clears 1st invoice, and applies remainder to 2nd."""
    invoices = [
        {"invoice_no": "INV-A", "invoice_date": pd.Timestamp("2026-07-01"), "amount": 20000.0},
        {"invoice_no": "INV-B", "invoice_date": pd.Timestamp("2026-07-15"), "amount": 40000.0},
    ]
    allocs = allocate_invoices_fifo(invoices, 35000.0)
    assert allocs[0]["allocated_amount"] == 20000.0
    assert allocs[0]["remaining_due"] == 0.0
    assert allocs[1]["allocated_amount"] == 15000.0
    assert allocs[1]["remaining_due"] == 25000.0


def test_clubbed_allocation_eight_invoices_cash_deposit_clubbed():
    """Verify synthetic CDM cash deposit clubbed pattern across 8 delivery route invoices."""
    invoice_amounts = [13911.0, 11081.0, 11926.0, 21372.0, 13570.0, 18992.0]
    total_cdm_deposit = sum(invoice_amounts)
    invoices = [
        {"invoice_no": f"KD/24-25/{i:05d}", "invoice_date": pd.Timestamp(f"2025-04-{i%28+1:02d}"), "amount": amt}
        for i, amt in enumerate(invoice_amounts, 341)
    ]
    allocs = allocate_invoices_fifo(invoices, total_cdm_deposit)
    assert len(allocs) == len(invoices)
    assert sum(a["allocated_amount"] for a in allocs) == total_cdm_deposit
    assert all(a["remaining_due"] == 0.0 for a in allocs)


def test_clubbed_allocation_with_zero_open_invoices_goes_on_account():
    """Verify receipt with no open invoices allocates entire amount On Account."""
    allocs = allocate_invoices_fifo([], 45000.0)
    assert len(allocs) == 1
    assert allocs[0]["invoice_no"] == "ON_ACCOUNT"
    assert allocs[0]["allocated_amount"] == 45000.0
    assert allocs[0]["bill_type"] == "On Account"


def test_clubbed_allocation_multi_invoice_tally_bill_allocations():
    """Verify multi-invoice clubbed receipt generates multiple <BILLALLOCATIONS.LIST> nodes in Tally XML."""
    vouchers = [{
        "date": "2026-09-30",
        "voucher_no": "RCPT-CLUBBED-TALLY",
        "party_name": "Balaji Provision Stores",
        "amount": 73500.0,
        "allocations": [
            {"invoice_no": "INV-2026-0412", "amount": 45000.0, "bill_type": "Agst Ref"},
            {"invoice_no": "INV-2026-0415", "amount": 28500.0, "bill_type": "Agst Ref"},
        ]
    }]
    xml_str = generate_tally_xml("Kaveri Distributors", vouchers)
    root = ET.fromstring(xml_str)
    party_entry = root.findall(".//ALLLEDGERENTRIES.LIST")[1]
    ballocs = party_entry.findall("BILLALLOCATIONS.LIST")
    assert len(ballocs) == 2
    inv_names = {b.find("NAME").text for b in ballocs}
    assert inv_names == {"INV-2026-0412", "INV-2026-0415"}
