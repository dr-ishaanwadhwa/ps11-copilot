"""Unit tests for the Sovereign Vault, Total Solvency Engine, and Statutory Guardrails."""
import pandas as pd
import pytest

from copilot import config
from copilot.vault import (
    GallaEntry,
    KhataAccount,
    VaultDB,
    cash_deposit_reporting_facts,
    check_cash_expense,
    check_cash_loan,
    check_single_receipt_cash,
    compute_total_solvency,
    deposit_records_checklist,
    format_solvency_report,
    format_whatsapp_reminder,
)


def test_galla_balancing_and_drift():
    # Balanced drawer
    balanced = GallaEntry(
        business_id="SME-1",
        date=pd.Timestamp("2026-09-30"),
        opening_cash=10_000.0,
        cash_in=25_000.0,
        cash_out=3_000.0,
        cash_banked=20_000.0,
        counted_cash=12_000.0,
    )
    assert balanced.expected_cash == 12_000.0
    assert balanced.drift == 0.0
    assert balanced.is_balanced
    assert balanced.status_label == "Balanced"

    # Drawer with drift
    unbalanced = GallaEntry(
        business_id="SME-1",
        date=pd.Timestamp("2026-09-30"),
        opening_cash=10_000.0,
        cash_in=25_000.0,
        cash_out=3_000.0,
        cash_banked=20_000.0,
        counted_cash=11_200.0,  # ₹800 short
    )
    assert unbalanced.drift == -800.0
    assert not unbalanced.is_balanced
    assert unbalanced.status_label == "Drift to check"


def test_vault_db_seeding(pack):
    vault = VaultDB(in_memory=True)
    vault.seed_from_pack(pack)

    # Verify SME-2 clinic cash records
    galla_sme2 = vault.get_latest_galla("SME-2")
    assert galla_sme2 is not None
    assert galla_sme2.counted_cash > 0

    # Verify SME-1 distributor khata records
    khata_sme1 = vault.get_khata_summary("SME-1")
    assert khata_sme1["account_count"] >= 3
    assert khata_sme1["receivables"] > 100_000.0
    assert khata_sme1["payables"] > 0


def test_total_solvency_engine(pack):
    vault = VaultDB(in_memory=True)
    vault.seed_from_pack(pack)

    solvency = compute_total_solvency(pack, vault, "SME-1")
    assert solvency.business_id == "SME-1"
    assert solvency.galla_cash > 0
    assert solvency.true_cash_runway_inr > 0

    rep = format_solvency_report(solvency)
    assert "business_id" in rep
    assert rep["galla_cash"] == solvency.galla_cash
    assert "true_cash_runway_inr" in rep

    # Test assumption parameterization (Task 5.2)
    assert solvency.haircut_alpha == config.KHATA_COLLECTION_ASSUMPTION
    assert solvency.haircut_alpha == 0.85

    s_adjusted = compute_total_solvency(pack, vault, "SME-1", haircut_alpha=0.60)
    assert s_adjusted.haircut_alpha == 0.60
    assert s_adjusted.total_expected_inflows == round(s_adjusted.informal_receivables * 0.60, 2)
    assert s_adjusted.true_cash_runway_inr < solvency.true_cash_runway_inr


def test_statutory_guardrails():
    # 1. Section 186 (old 269ST) - single receipt cash limit
    safe_rec = check_single_receipt_cash(150_000.0)
    assert safe_rec.is_safe and safe_rec.status == "SAFE"

    blocked_rec = check_single_receipt_cash(250_000.0, party_name="Apex Retailers")
    assert not blocked_rec.is_safe and blocked_rec.status == "BLOCKED"
    assert "Sec 186" in blocked_rec.citation
    assert "(to be confirmed by a CA)" in blocked_rec.citation
    assert "This may attract a penalty; your CA can confirm." in blocked_rec.message

    # 2. Section 36(4) (old 40A(3)) - cash expense limits
    safe_exp = check_cash_expense(8_000.0)
    assert safe_exp.is_safe and safe_exp.status == "SAFE"

    warn_exp = check_cash_expense(15_000.0, is_transport=False)
    assert not warn_exp.is_safe and warn_exp.status == "WARNING"
    assert "(to be confirmed by a CA)" in warn_exp.citation
    assert "This may attract a penalty; your CA can confirm." in warn_exp.message

    # Transport goods carriage ceiling (₹35,000)
    safe_trans = check_cash_expense(25_000.0, is_transport=True)
    assert safe_trans.is_safe and safe_trans.status == "SAFE"

    # 3. Section 185 / 188 - cash loans/deposits
    blocked_loan = check_cash_loan(50_000.0, direction="BORROW")
    assert not blocked_loan.is_safe and blocked_loan.status == "BLOCKED"
    assert "(to be confirmed by a CA)" in blocked_loan.citation
    assert "This may attract a penalty; your CA can confirm." in blocked_loan.message

    # 4. SFT Rule 237 facts (D68)
    sft_info = cash_deposit_reporting_facts(600_000.0, account_type="CURRENT")
    assert sft_info.is_safe and sft_info.status == "INFO"
    assert "Rule 237" in sft_info.citation


def test_capital_infusion_checklist():
    res = deposit_records_checklist()
    assert set(res.keys()) == {"documents", "referral"}
    assert len(res["documents"]) == 3


def test_confidential_chasing_and_limitation_act():
    acc_active = KhataAccount(
        party_name="Laxmi Kirana Stores",
        business_id="SME-1",
        balance_due=45_000.0,
        last_active_date=pd.Timestamp("2026-08-01"),
        months_open=6,
        phone="9822014521"
    )
    rem_active = format_whatsapp_reminder(acc_active, "Kaveri Distributors", "kaveri@okhdfcbank")
    assert "wa.me/919822014521" in rem_active["wa_link"]
    assert rem_active["limitation_warning"] is None

    # Stale debt (>30 months)
    acc_stale = KhataAccount(
        party_name="Old Town Retailers",
        business_id="SME-1",
        balance_due=60_000.0,
        last_active_date=pd.Timestamp("2023-11-01"),
        months_open=34,
        phone="9822014521"
    )
    rem_stale = format_whatsapp_reminder(acc_stale, "Kaveri Distributors")
    assert rem_stale["limitation_warning"] is not None
    assert "This balance is over 30 months old." in rem_stale["limitation_warning"]
    assert "your CA or lawyer can confirm" in rem_stale["limitation_warning"]


def test_deep_vault_interface(pack):
    """Test the consolidated deep interface on VaultDB."""
    vault = VaultDB(in_memory=True)
    vault.seed_from_pack(pack)

    # 1. Unified solvency call directly on vault
    solvency = vault.compute_solvency(pack, "SME-1", haircut_alpha=0.80)
    assert solvency.business_id == "SME-1"
    assert solvency.galla_cash > 0
    assert solvency.net_bank_liquidity > 0

    # 2. Compliance facts directly on vault
    facts = vault.compliance_facts(1_200_000.0)
    assert "Rule 237" in facts.citation
    assert facts.is_safe

    # 3. Deposit checklist directly on vault
    checklist = vault.deposit_checklist()
    assert len(checklist["documents"]) >= 3

    # 4. Chasing reminders directly on vault
    reminders = vault.chasing_reminders("SME-1")
    assert len(reminders) > 0
    assert "wa_link" in reminders[0]["reminder"]


def test_vault_crypto_key_derivation_and_salt(monkeypatch):
    from copilot.vault.crypto import VaultCrypto

    salt1 = VaultCrypto.generate_salt(16)
    salt2 = VaultCrypto.generate_salt(16)
    assert len(salt1) == 16
    assert len(salt2) == 16
    assert salt1 != salt2

    # Determinism with same salt and pin
    k1 = VaultCrypto.derive_key("0000", salt1)
    k2 = VaultCrypto.derive_key("0000", salt1)
    assert k1 == k2
    assert len(k1) == 32

    # Different salt produces different key
    k3 = VaultCrypto.derive_key("0000", salt2)
    assert k1 != k3

    # Different pin produces different key
    k4 = VaultCrypto.derive_key("1234", salt1)
    assert k1 != k4

    # Empty pin or invalid salt raises ValueError
    with pytest.raises(ValueError):
        VaultCrypto.derive_key("", salt1)
    with pytest.raises(ValueError):
        VaultCrypto.derive_key("0000", b"short")

    # Environment variable configurable pin
    monkeypatch.setenv("COPILOT_OWNER_PIN", "9999")
    assert VaultCrypto.get_configured_pin() == "9999"
    monkeypatch.delenv("COPILOT_OWNER_PIN", raising=False)
    assert VaultCrypto.get_configured_pin() == "0000"


def test_vault_crypto_aes_gcm_authenticated_encryption():
    from copilot.vault.crypto import VaultCrypto, VaultDecryptionError

    salt = VaultCrypto.generate_salt()
    key = VaultCrypto.derive_key("0000", salt)
    plaintext = b"Sensitive godown cash books and parchi entries"

    envelope = VaultCrypto.encrypt(plaintext, key=key, salt=salt)
    assert envelope.startswith(VaultCrypto.MAGIC_HEADER)

    # Decrypt with key
    decrypted, s = VaultCrypto.decrypt(envelope, key=key)
    assert decrypted == plaintext
    assert s == salt

    # Decrypt with pin
    decrypted2, _ = VaultCrypto.decrypt(envelope, pin="0000")
    assert decrypted2 == plaintext

    # Verify pin helper
    assert VaultCrypto.verify_pin(envelope, "0000") is True
    assert VaultCrypto.verify_pin(envelope, "1111") is False

    # Wrong pin raises VaultDecryptionError
    with pytest.raises(VaultDecryptionError):
        VaultCrypto.decrypt(envelope, pin="wrong_pin")

    # Tampered ciphertext fails authentication tag check
    tampered = bytearray(envelope)
    tampered[-5] ^= 0xFF
    with pytest.raises(VaultDecryptionError):
        VaultCrypto.decrypt(bytes(tampered), pin="0000")

    # Corrupted header raises VaultDecryptionError
    bad_header = b"BAD_HEADER\x00\x00" + envelope[12:]
    with pytest.raises(VaultDecryptionError):
        VaultCrypto.decrypt(bad_header, pin="0000")


def test_vault_db_gated_access_and_locking():
    from copilot.vault import Collection, GallaEntry, PARTIAL_VIEW_NOTICE, VaultDB, VaultLockedError

    # 1. Defaults to locked
    vault = VaultDB(in_memory=True)
    assert not vault.is_unlocked()

    # 2. Sovereign queries raise VaultLockedError when locked
    with pytest.raises(VaultLockedError):
        vault.get_latest_galla("SME-1")
    with pytest.raises(VaultLockedError):
        vault.get_collections("SME-1")
    with pytest.raises(VaultLockedError):
        vault.get_khata_summary("SME-1")
    with pytest.raises(VaultLockedError):
        vault.get_ytd_cash_deposits("SME-1")

    # Sovereign mutations raise VaultLockedError when locked
    g = GallaEntry("SME-1", pd.Timestamp("2026-09-30"), 1000, 500, 100, 200, 1200)
    with pytest.raises(VaultLockedError):
        vault.record_galla(g)

    c = Collection("SME-1", pd.Timestamp("2026-09-30"), "Shop X", 500)
    with pytest.raises(VaultLockedError):
        vault.record_collection(c)

    # 3. Public plane methods remain accessible without PIN
    facts = vault.compliance_facts(500_000.0)
    assert facts.is_safe
    checklist = vault.deposit_checklist()
    assert len(checklist["documents"]) >= 3
    assert vault.get_view_notice() == PARTIAL_VIEW_NOTICE

    # 4. Incorrect PIN unlock fails
    assert vault.unlock("9999") is False
    assert not vault.is_unlocked()

    # 5. Correct PIN unlock succeeds
    assert vault.unlock("0000") is True
    assert vault.is_unlocked()

    # 6. Operations succeed when unlocked
    vault.record_galla(g)
    assert vault.get_latest_galla("SME-1") is not None
    assert vault.get_latest_galla("SME-1").counted_cash == 1200

    # 7. Relocking wipes memory state
    vault.lock()
    assert not vault.is_unlocked()
    with pytest.raises(VaultLockedError):
        vault.get_latest_galla("SME-1")


def test_vault_encrypted_persistence_at_rest(tmp_path):
    from copilot.vault import Collection, GallaEntry, VaultDB

    db_file = tmp_path / "sub" / "sovereign_vault.db"

    # Create persistent vault and insert records
    v1 = VaultDB(db_path=db_file)
    assert not v1.is_unlocked()
    assert v1.unlock("0000") is True

    g_entry = GallaEntry(
        business_id="SME-1",
        date=pd.Timestamp("2026-09-30"),
        opening_cash=50_000.0,
        cash_in=20_000.0,
        cash_out=5_000.0,
        cash_banked=15_000.0,
        counted_cash=50_000.0,
        notes="UniqueGodownSecretMemo12345",
    )
    v1.record_galla(g_entry)

    c_entry = Collection(
        business_id="SME-1",
        date=pd.Timestamp("2026-09-30"),
        shop="SecretSupermarket777",
        amount=12_500.0,
        salesman="Deepak",
        payment_mode="CASH",
        notes="ParchiMemoXYZ",
    )
    slip_id = v1.record_collection(c_entry, update_drawer=True)
    assert slip_id.startswith("SLIP-")
    v1.lock()

    # Inspect file at rest on disk
    assert db_file.exists()
    disk_bytes = db_file.read_bytes()

    # Must have magic header
    assert disk_bytes.startswith(b"SOV_VAULT_V1\x00")

    # Zero unencrypted SQLite headers on disk
    assert b"SQLite format 3" not in disk_bytes

    # Zero plaintext confidential strings on disk
    assert b"UniqueGodownSecretMemo12345" not in disk_bytes
    assert b"SecretSupermarket777" not in disk_bytes
    assert b"ParchiMemoXYZ" not in disk_bytes

    # Reopen database in fresh instance
    v2 = VaultDB(db_path=db_file)
    assert not v2.is_unlocked()
    assert v2.unlock("wrong_pin") is False
    assert v2.unlock("0000") is True

    loaded_g = v2.get_latest_galla("SME-1")
    assert loaded_g is not None
    assert loaded_g.opening_cash == 50_000.0
    assert loaded_g.notes == "UniqueGodownSecretMemo12345"
    assert loaded_g.cash_in == 32_500.0  # 20_000 + 12_500 from cash collection

    loaded_cols = v2.get_collections("SME-1")
    assert len(loaded_cols) == 1
    assert loaded_cols[0].shop == "SecretSupermarket777"
    assert loaded_cols[0].amount == 12_500.0
    assert loaded_cols[0].salesman == "Deepak"


def test_collection_model_and_drawer_linkage():
    from copilot.vault import Collection, GallaEntry, VaultDB

    vault = VaultDB(in_memory=True)
    vault.unlock("0000")

    # Seed galla
    g0 = GallaEntry("SME-1", pd.Timestamp("2026-09-30"), 10000, 0, 0, 0, 10000)
    vault.record_galla(g0)

    # Record cash collection updates drawer
    c_cash = Collection("SME-1", pd.Timestamp("2026-09-30"), "Shop A", 3000.0, "Ramesh", payment_mode="CASH")
    assert c_cash.payment_mode == "CASH"
    assert c_cash.slip_id.startswith("SLIP-")
    vault.record_collection(c_cash, update_drawer=True)

    g1 = vault.get_latest_galla("SME-1")
    assert g1.cash_in == 3000.0

    # Record cheque collection does not increment physical cash drawer
    c_cheque = Collection("SME-1", pd.Timestamp("2026-09-30"), "Shop B", 5000.0, "Ramesh", payment_mode="CHEQUE")
    vault.record_collection(c_cheque, update_drawer=True)

    g2 = vault.get_latest_galla("SME-1")
    assert g2.cash_in == 3000.0  # Cheque did not change cash_in

    # Date range filtering
    c_future = Collection("SME-1", pd.Timestamp("2026-10-05"), "Shop C", 2000.0, "Suresh")
    vault.record_collection(c_future)

    filtered = vault.get_collections(
        "SME-1",
        start=pd.Timestamp("2026-09-01"),
        end=pd.Timestamp("2026-09-30"),
    )
    assert len(filtered) == 2
    assert {col.shop for col in filtered} == {"Shop A", "Shop B"}


def test_zero_cloud_telemetry_in_vault():
    import sys
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("copilot.vault"):
            mod = sys.modules[mod_name]
            # Ensure no remote networking client libraries imported
            for forbidden_mod in ["requests", "urllib.request", "httpx", "aiohttp", "socket", "ftplib"]:
                assert forbidden_mod not in getattr(mod, "__dict__", {}), (
                    f"Forbidden network library '{forbidden_mod}' imported in {mod_name}"
                )


def test_anti_spoliation_and_notice_compliance():
    from copilot.vault import PARTIAL_VIEW_NOTICE, VaultCrypto, VaultDB

    # Notice text exact match
    assert PARTIAL_VIEW_NOTICE == "Formal books only. The owner's cash memo is not included in this view."

    # Verify no panic-wipes, nuke, or emergency destroy methods exist
    forbidden_method_terms = ["panic", "nuke", "wipe_all", "emergency_delete", "destroy_db"]
    for cls in [VaultDB, VaultCrypto]:
        for attr in dir(cls):
            for term in forbidden_method_terms:
                assert term not in attr.lower(), f"Forbidden method '{attr}' found on {cls.__name__}"

