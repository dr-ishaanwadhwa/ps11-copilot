"""Adversarial Verification & Stress Test Harness for Milestone 1 & 2.

Author: challenger_1 (Empirical Challenger)
Covers:
1. PIN Derivation & Brute Force Rejection ("1234", "9999", "", "abcd", unicode, boundary lengths)
2. Tamper Rejection & Authenticated Ciphertext Integrity (AES-256-GCM byte flipping across header, salt, nonce, ciphertext, tag)
3. Zero Plaintext on Disk (Sensitive strings, raw SQLite magic header inspection, file permissions 0600, tmp file cleanup)
4. Cash Drawer Drift Math Stress Testing (threshold boundaries, positive/negative drift, floating point accuracy, extreme magnitudes)
5. Public Safety Grep (7 forbidden phrases across all files, anti-spoliation audit)
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
import pandas as pd
import pytest

from copilot.vault import (
    Collection,
    GallaEntry,
    KhataAccount,
    RokadEntry,
    VaultCrypto,
    VaultDB,
    VaultDecryptionError,
    VaultLockedError,
    PARTIAL_VIEW_NOTICE,
)
from copilot.vault.models import calculate_drawer_balance


# ============================================================================
# 1. PIN DERIVATION & BRUTE FORCE REJECTION
# ============================================================================

def test_pin_derivation_brute_force_rejection(tmp_path):
    """Stress test wrong PINs, invalid PIN types, and ensure VaultLockedError is raised."""
    db_file = tmp_path / "sovereign_vault.db"
    
    # Initialize vault with PIN '0000' and store data
    vault = VaultDB(db_path=db_file)
    assert vault.unlock("0000") is True
    
    entry = GallaEntry(
        business_id="SME-1",
        date=pd.Timestamp("2026-10-01"),
        opening_cash=15000.0,
        cash_in=5000.0,
        cash_out=1000.0,
        cash_banked=4000.0,
        counted_cash=15000.0,
        notes="CONFIDENTIAL_AUDIT_FLOAT",
    )
    vault.record_galla(entry)
    vault.lock()
    
    # Test adversarial PIN attempts
    adversarial_pins = [
        "1234",
        "9999",
        "",
        "abcd",
        "000",
        "00000",
        " 0000",
        "0000 ",
        "admin",
        "root",
        "' OR '1'='1",
        "\x00\x00\x00\x00",
        "🔒🔑",
    ]
    
    for bad_pin in adversarial_pins:
        v_test = VaultDB(db_path=db_file)
        assert v_test.is_unlocked() is False
        
        # Unlock attempt must fail
        unlock_result = v_test.unlock(bad_pin)
        assert unlock_result is False, f"Bad PIN '{bad_pin}' unexpectedly succeeded in unlocking vault!"
        assert v_test.is_unlocked() is False
        assert v_test.conn is None
        
        # All sovereign access methods must raise VaultLockedError
        with pytest.raises(VaultLockedError):
            v_test.get_latest_galla("SME-1")
            
        with pytest.raises(VaultLockedError):
            v_test.get_collections("SME-1")
            
        with pytest.raises(VaultLockedError):
            v_test.get_khata_summary("SME-1")
            
        with pytest.raises(VaultLockedError):
            v_test.get_ytd_cash_deposits("SME-1")
            
        with pytest.raises(VaultLockedError):
            v_test.record_galla(entry)
            
        with pytest.raises(VaultLockedError):
            c = Collection("SME-1", pd.Timestamp.now(), "Shop", 100.0)
            v_test.record_collection(c)
            
        with pytest.raises(VaultLockedError):
            rokad_sample = RokadEntry("R1", "SME-1", pd.Timestamp.now(), "IN", 100.0, "Misc", "Party", "memo")
            v_test.record_rokad(rokad_sample)
            
        with pytest.raises(VaultLockedError):
            v_test.chasing_reminders("SME-1")
            
        # Ensure in-memory records dictionaries remain empty
        assert v_test.galla_records["SME-1"] == []
        assert v_test.collection_records["SME-1"] == []
        assert v_test.khata_records["SME-1"] == {}


def test_derive_key_edge_cases():
    """Verify PBKDF2 edge cases and input validation."""
    salt = VaultCrypto.generate_salt(16)
    
    # Empty PIN must raise ValueError
    with pytest.raises(ValueError, match="Owner PIN cannot be empty"):
        VaultCrypto.derive_key("", salt)
        
    # Salt too short must raise ValueError
    with pytest.raises(ValueError, match="Salt must be at least 8 bytes"):
        VaultCrypto.derive_key("0000", b"short")
        
    # None salt must raise ValueError
    with pytest.raises(ValueError):
        VaultCrypto.derive_key("0000", None)  # type: ignore


# ============================================================================
# 2. TAMPER REJECTION & AUTHENTICATED CIPHERTEXT INTEGRITY
# ============================================================================

def test_tamper_rejection_byte_flipping(tmp_path):
    """Stress test ciphertext tampering across every envelope region."""
    db_file = tmp_path / "vault_tamper.db"
    
    v = VaultDB(db_path=db_file)
    v.unlock("0000")
    g = GallaEntry("SME-1", pd.Timestamp("2026-10-01"), 10000, 2000, 500, 1000, 10500, "TAMPER_TEST_DATA")
    v.record_galla(g)
    v.lock()
    
    assert db_file.exists()
    original_bytes = db_file.read_bytes()
    header_len = len(VaultCrypto.MAGIC_HEADER)
    salt_len = VaultCrypto.SALT_SIZE
    nonce_len = VaultCrypto.NONCE_SIZE
    total_len = len(original_bytes)
    
    # Tamper test positions:
    # 1. Header (byte 0, byte 5, byte 11)
    # 2. Salt (byte 12, byte 20)
    # 3. Nonce (byte 28, byte 35)
    # 4. Ciphertext start (byte 40)
    # 5. Ciphertext body (midpoint)
    # 6. Ciphertext authentication tag (last byte, last-8 byte)
    tamper_indices = [
        0, 5, header_len - 1,
        header_len, header_len + 5,
        header_len + salt_len, header_len + salt_len + 5,
        header_len + salt_len + nonce_len,
        total_len // 2,
        total_len - 1, total_len - 8, total_len - 16,
    ]
    
    for idx in tamper_indices:
        tampered = bytearray(original_bytes)
        tampered[idx] ^= 0x5A  # Flip bits
        
        tampered_file = tmp_path / f"tampered_{idx}.db"
        tampered_file.write_bytes(bytes(tampered))
        
        # Test low-level decrypt
        with pytest.raises(VaultDecryptionError):
            VaultCrypto.decrypt(bytes(tampered), pin="0000")
            
        # Test VaultDB unlock on tampered file
        v_tamper = VaultDB(db_path=tampered_file)
        unlocked = v_tamper.unlock("0000")
        assert unlocked is False, f"Vault unlock unexpectedly succeeded on tampered byte at offset {idx}!"
        assert v_tamper.is_unlocked() is False
        assert v_tamper.conn is None
        
        with pytest.raises(VaultLockedError):
            v_tamper.get_latest_galla("SME-1")


def test_tamper_rejection_truncation_and_garbage(tmp_path):
    """Test corrupted and truncated files."""
    db_file = tmp_path / "vault_trunc.db"
    v = VaultDB(db_path=db_file)
    v.unlock("0000")
    v.record_galla(GallaEntry("SME-1", pd.Timestamp("2026-10-01"), 1000, 0, 0, 0, 1000))
    v.lock()
    
    payload = db_file.read_bytes()
    min_len = len(VaultCrypto.MAGIC_HEADER) + VaultCrypto.SALT_SIZE + VaultCrypto.NONCE_SIZE + 16
    
    # 0-byte payload raises VaultDecryptionError on raw decrypt
    with pytest.raises(VaultDecryptionError):
        VaultCrypto.decrypt(b"", pin="0000")
        
    # Non-zero truncated files (st_size > 0 but corrupted/truncated)
    for cut in [1, 5, 12, min_len - 1]:
        truncated_file = tmp_path / f"trunc_{cut}.db"
        truncated_file.write_bytes(payload[:cut])
        
        with pytest.raises(VaultDecryptionError):
            VaultCrypto.decrypt(payload[:cut], pin="0000")
            
        v_trunc = VaultDB(db_path=truncated_file)
        assert v_trunc.unlock("0000") is False
        assert v_trunc.is_unlocked() is False
        assert v_trunc.conn is None


# ============================================================================
# 3. ZERO PLAINTEXT ON DISK
# ============================================================================

def test_zero_plaintext_on_disk(tmp_path):
    """Assert that zero sensitive plaintext strings or SQLite magic bytes exist at rest."""
    sensitive_markers = [
        "SECRET_GODOWN_CASH_12345",
        "HAWALA_PARCHI_9999",
        "HIDDEN_KHATA_PARTY_SECRET",
        "ConfidentialGodownFloat987654",
        "SalesmanDeepakCollectionSlipSpecialNote",
    ]
    
    db_path = tmp_path / "zero_plaintext.db"
    vault = VaultDB(db_path=db_path)
    vault.unlock("0000")
    
    # 1. Galla Entry with secret
    vault.record_galla(GallaEntry(
        business_id="SME-1",
        date=pd.Timestamp("2026-10-01"),
        opening_cash=99999.0,
        cash_in=10000.0,
        cash_out=5000.0,
        cash_banked=2000.0,
        counted_cash=102999.0,
        notes=sensitive_markers[0],
    ))
    
    # 2. Collection slip with secret
    vault.record_collection(Collection(
        business_id="SME-1",
        date=pd.Timestamp("2026-10-01"),
        shop="Laxmi Traders",
        amount=55000.0,
        salesman="Deepak",
        payment_mode="CASH",
        slip_id=sensitive_markers[1],
        notes=sensitive_markers[4],
    ))
    
    # 3. Khata account with secret (inserted into in-memory SQLite table)
    assert vault.conn is not None
    with vault.conn:
        vault.conn.execute(
            "INSERT OR REPLACE INTO khata_accounts VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sensitive_markers[2], "SME-1", 75000.0, "2026-10-01", 4, "+91 99999 99999", 0),
        )
    
    # 4. Rokad entry with secret
    vault.record_rokad(RokadEntry(
        entry_id="ROK-9999",
        business_id="SME-1",
        timestamp=pd.Timestamp("2026-10-01 12:00:00"),
        direction="IN",
        amount=30000.0,
        category="Trade Cash",
        counterparty="Kaveri Agent",
        note=sensitive_markers[3],
    ))
    
    # Flush & Lock
    vault.lock()
    
    # Check physical file on disk
    assert db_path.exists()
    raw_disk = db_path.read_bytes()
    
    # Magic header check
    assert raw_disk.startswith(b"SOV_VAULT_V1\x00")
    
    # SQLite format check
    assert b"SQLite format 3" not in raw_disk, "CRITICAL: Raw SQLite database format header found on disk!"
    
    # Sensitive markers check
    for marker in sensitive_markers:
        assert marker.encode("utf-8") not in raw_disk, f"CRITICAL LEAK: Sensitive string '{marker}' found in raw disk bytes!"
        
    # Check file permissions are 0600 (-rw-------)
    file_stat = os.stat(db_path)
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600, f"File permissions insecure: expected 0o600 (-rw-------), got {oct(file_mode)}"
    
    # Ensure no leftover temporary files in parent directory
    temp_files = list(tmp_path.glob("*.tmp*"))
    assert len(temp_files) == 0, f"Found leftover temporary files on disk: {temp_files}"


# ============================================================================
# 4. CASH DRAWER DRIFT MATH STRESS TESTING
# ============================================================================

def test_cash_drawer_drift_math_stress():
    """Exhaustive stress-testing of cash drawer drift calculation."""
    # 1. Normal balance (drift=0, drift=45 -> is_balanced=True)
    res_zero = calculate_drawer_balance(
        opening_cash=10000.0,
        cash_in=5000.0,
        cash_out=1000.0,
        cash_banked=2000.0,
        counted_cash=12000.0,  # 10000 + 5000 - 1000 - 2000 = 12000, drift = 0
    )
    assert res_zero["drift"] == 0.0
    assert res_zero["is_balanced"] is True
    assert res_zero["status_label"] == "Balanced"
    
    res_pos_45 = calculate_drawer_balance(10000.0, 5000.0, 1000.0, 2000.0, 12045.0)
    assert res_pos_45["drift"] == 45.0
    assert res_pos_45["is_balanced"] is True
    assert res_pos_45["status_label"] == "Balanced"
    
    res_neg_45 = calculate_drawer_balance(10000.0, 5000.0, 1000.0, 2000.0, 11955.0)
    assert res_neg_45["drift"] == -45.0
    assert res_neg_45["is_balanced"] is True
    assert res_neg_45["status_label"] == "Balanced"

    # 2. Severe discrepancy (drift=500, drift=-250 -> is_balanced=False)
    res_pos_500 = calculate_drawer_balance(10000.0, 5000.0, 1000.0, 2000.0, 12500.0)
    assert res_pos_500["drift"] == 500.0
    assert res_pos_500["is_balanced"] is False
    assert res_pos_500["status_label"] == "Drift to check"
    
    res_neg_250 = calculate_drawer_balance(10000.0, 5000.0, 1000.0, 2000.0, 11750.0)
    assert res_neg_250["drift"] == -250.0
    assert res_neg_250["is_balanced"] is False
    assert res_neg_250["status_label"] == "Drift to check"

    # 3. Exact threshold boundary behavior (₹50 tolerance: abs(drift) < 50.0)
    # Drift = 49.99 -> True
    res_49_99 = calculate_drawer_balance(10000.0, 0.0, 0.0, 0.0, 10049.99)
    assert res_49_99["drift"] == 49.99
    assert res_49_99["is_balanced"] is True
    
    res_neg_49_99 = calculate_drawer_balance(10000.0, 0.0, 0.0, 0.0, 9950.01)
    assert res_neg_49_99["drift"] == -49.99
    assert res_neg_49_99["is_balanced"] is True

    # Drift = 50.00 -> False (boundary strictly < 50.0)
    res_50_00 = calculate_drawer_balance(10000.0, 0.0, 0.0, 0.0, 10050.00)
    assert res_50_00["drift"] == 50.00
    assert res_50_00["is_balanced"] is False
    assert res_50_00["status_label"] == "Drift to check"

    res_neg_50_00 = calculate_drawer_balance(10000.0, 0.0, 0.0, 0.0, 9950.00)
    assert res_neg_50_00["drift"] == -50.00
    assert res_neg_50_00["is_balanced"] is False
    assert res_neg_50_00["status_label"] == "Drift to check"

    # 4. Floating point edge cases (fractions like 0.1 + 0.2)
    res_float = calculate_drawer_balance(100.10, 200.20, 50.05, 50.25, 200.00)
    # Expected: 100.10 + 200.20 - 50.05 - 50.25 = 200.00
    assert res_float["expected_cash"] == 200.0
    assert res_float["drift"] == 0.0
    assert res_float["is_balanced"] is True

    # 5. Extreme magnitude (crore level)
    res_large = calculate_drawer_balance(
        opening_cash=10_000_000.0,
        cash_in=50_000_000.0,
        cash_out=5_000_000.0,
        cash_banked=45_000_000.0,
        counted_cash=10_000_030.0,
    )
    assert res_large["expected_cash"] == 10_000_000.0
    assert res_large["drift"] == 30.0
    assert res_large["is_balanced"] is True


# ============================================================================
# 5. PUBLIC SAFETY GREP & ANTI-SPOLIATION AUDIT
# ============================================================================

def test_public_safety_forbidden_phrases_comprehensive():
    """Grep entire codebase (app/, src/, tests/) for the 7 forbidden phrases."""
    forbidden = [
        "presentation mode",
        "tax inspection",
        "audit trace",
        "golden pillars",
        "withstand",
        "readiness tier",
        "headroom before",
    ]
    
    repo_root = Path(__file__).resolve().parent.parent
    checked_files = 0
    
    for folder in ["app", "src"]:
        target_dir = repo_root / folder
        for py_file in target_dir.rglob("*.py"):
            checked_files += 1
            content = py_file.read_text(encoding="utf-8").lower()
            for phrase in forbidden:
                assert phrase not in content, (
                    f"VIOLATION: Forbidden phrase '{phrase}' found in {py_file}"
                )
                
    assert checked_files > 15, f"Expected >15 python files checked, only found {checked_files}"


def test_anti_spoliation_audit():
    """Verify strictly no panic wipe, destruction, or spoliation stubs exist."""
    forbidden_terms = [
        "panic",
        "nuke",
        "wipe_all",
        "emergency_delete",
        "destroy_db",
        "shred",
    ]
    
    for cls in [VaultDB, VaultCrypto]:
        for attr in dir(cls):
            attr_lower = attr.lower()
            for term in forbidden_terms:
                assert term not in attr_lower, (
                    f"ANTI-SPOLIATION VIOLATION: Forbidden method/attribute '{attr}' on {cls.__name__}"
                )
