"""Unit tests for the Sovereign Vault, Total Solvency Engine, and Statutory Guardrails."""
import pandas as pd
import pytest

from copilot.vault import (
    GallaEntry,
    KhataAccount,
    VaultDB,
    audit_capital_infusion,
    check_cash_expense,
    check_cash_loan,
    check_sft_deposit_threshold,
    check_single_receipt_cash,
    compute_total_solvency,
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


def test_statutory_guardrails():
    # 1. Section 186 (old 269ST) - single receipt cash limit
    safe_rec = check_single_receipt_cash(150_000.0)
    assert safe_rec.is_safe and safe_rec.status == "SAFE"

    blocked_rec = check_single_receipt_cash(250_000.0, party_name="Apex Retailers")
    assert not blocked_rec.is_safe and blocked_rec.status == "BLOCKED"
    assert "Sec 186" in blocked_rec.citation
    assert "100%" in blocked_rec.message

    # 2. Section 36(4) (old 40A(3)) - cash expense limits
    safe_exp = check_cash_expense(8_000.0)
    assert safe_exp.is_safe and safe_exp.status == "SAFE"

    warn_exp = check_cash_expense(15_000.0, is_transport=False)
    assert not warn_exp.is_safe and warn_exp.status == "WARNING"
    assert "100% of this expense will be disallowed" in warn_exp.message

    # Transport goods carriage ceiling (₹35,000)
    safe_trans = check_cash_expense(25_000.0, is_transport=True)
    assert safe_trans.is_safe and safe_trans.status == "SAFE"

    # 3. Section 185 / 188 - cash loans/deposits
    blocked_loan = check_cash_loan(50_000.0, direction="BORROW")
    assert not blocked_loan.is_safe and blocked_loan.status == "BLOCKED"

    # 4. SFT Rule 237 / Form 165
    sft_alert = check_sft_deposit_threshold(600_000.0, current_ytd_cash=4_600_000.0, account_type="CURRENT")
    assert not sft_alert.is_safe and sft_alert.status == "WARNING"
    assert "Rule 237" in sft_alert.citation


def test_capital_infusion_readiness():
    # Unsubstantiated cash deposit
    vulnerable = audit_capital_infusion(500_000.0)
    assert vulnerable["readiness_tier"] == "VULNERABLE"
    assert vulnerable["score_percent"] == 0

    # Substantiated with prior bank withdrawal and daily retail chits
    solid = audit_capital_infusion(
        500_000.0,
        has_prior_bank_withdrawal=True,
        has_retail_collection_chits=True
    )
    assert solid["readiness_tier"] == "HIGH"
    assert solid["score_percent"] >= 70


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
    assert "Section 18 of the Limitation Act" in rem_stale["limitation_warning"]
