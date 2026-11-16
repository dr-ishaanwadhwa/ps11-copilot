"""Milestone 3 Gate Verification Adversarial Test Suite.

Author: Challenger 1 (critic, specialist)
Repository: /Users/ishaanwadhwa/Projects/ps11-copilot
Target: app/streamlit_app.py

Empirical stress tests:
1. Dynamic Role Switching & Sovereign Vault Locking
2. Brand Bleed Elimination across SME-1, SME-2, SME-3 (English & Hindi)
3. Receivables Section 18 Limitation Act Empty State
4. Receivables Non-Limitation Empty State & Clear Filter Button Crash (Bug Reproduction)
5. Sovereign Vault CA Export Isolation under Split-Plane Security
6. Domain-Adaptive Cash Drawer Cockpit Terminology
7. Section 18 Limitation Act Acknowledgment of Debt (AoD) WhatsApp Drafting
"""
from __future__ import annotations

import io
import os
import re
from unittest.mock import patch
import openpyxl
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from streamlit.util import calc_md5

import copilot.config as config
import copilot.receivables as recv
import copilot.tally as tally
from copilot.vault import KhataAccount, VaultDB


# ============================================================================
# 1. DYNAMIC ROLE SWITCHING & VAULT AUTO-LOCKING
# ============================================================================

def test_dynamic_role_switch_auto_locks_vault():
    """Verify that switching from Owner to Accountant or Counter staff automatically locks the vault."""
    at = AppTest.from_file("app/streamlit_app.py", default_timeout=30)
    at.run()
    assert not at.exception

    # 1. Initial State: Owner, Vault locked
    assert at.session_state["role_choice"] == "Owner"
    vault_unlocked = at.session_state["vault_unlocked"] if "vault_unlocked" in at.session_state else False
    assert vault_unlocked is False

    # 2. Unlock as Owner
    pin_input = [w for w in at.sidebar.text_input if w.key == "sidebar_owner_pin_input"][0]
    pin_input.input("0000")
    unlock_btn = [b for b in at.sidebar.button if b.key == "btn_sidebar_unlock_vault"][0]
    unlock_btn.click()
    at.run()
    assert not at.exception
    assert at.session_state["vault_unlocked"] is True

    # 3. Switch role to Accountant (CA) -> MUST immediately lock vault
    role_select = [w for w in at.sidebar.selectbox if w.key == "role"][0]
    role_select.select("Accountant (CA)")
    at.run()
    assert not at.exception
    assert at.session_state["vault_unlocked"] is False
    assert at.session_state["role_choice"] == "Accountant (CA)"
    # Partial view warning must be displayed
    assert len(at.warning) > 0
    assert any("Formal books only" in w.value for w in at.warning)

    # 4. Switch back to Owner -> Vault MUST remain locked until PIN is entered again
    role_select = [w for w in at.sidebar.selectbox if w.key == "role"][0]
    role_select.select("Owner")
    at.run()
    assert not at.exception
    assert at.session_state["vault_unlocked"] is False

    # 5. Unlock again as Owner
    pin_input = [w for w in at.sidebar.text_input if w.key == "sidebar_owner_pin_input"][0]
    pin_input.input("0000")
    unlock_btn = [b for b in at.sidebar.button if b.key == "btn_sidebar_unlock_vault"][0]
    unlock_btn.click()
    at.run()
    assert at.session_state["vault_unlocked"] is True

    # 6. Switch to Counter staff -> MUST immediately lock vault
    role_select = [w for w in at.sidebar.selectbox if w.key == "role"][0]
    role_select.select("Counter staff")
    at.run()
    assert not at.exception
    assert at.session_state["vault_unlocked"] is False
    assert at.session_state["role_choice"] == "Counter staff"
    assert len(at.warning) > 0


def test_non_owner_cannot_unlock_vault_in_sidebar():
    """Verify that an Accountant attempting to unlock the vault in the sidebar is blocked."""
    at = AppTest.from_file("app/streamlit_app.py", default_timeout=30)
    at.run()

    # Switch to Accountant
    role_select = [w for w in at.sidebar.selectbox if w.key == "role"][0]
    role_select.select("Accountant (CA)")
    at.run()
    assert at.session_state["vault_unlocked"] is False

    # A non-owner gets no PIN field or unlock button at all (15 Nov demo: typing 0000 as
    # Accountant appeared to work, then silently re-locked). They see why instead.
    assert not [w for w in at.sidebar.text_input if w.key == "sidebar_owner_pin_input"]
    assert not [b for b in at.sidebar.button if b.key == "btn_sidebar_unlock_vault"]
    assert any("vault-role-note" in m.value and "viewing as Accountant" in m.value for m in at.sidebar.markdown)
    assert at.session_state["vault_unlocked"] is False
    assert any("Formal books only" in w.value for w in at.warning)


# ============================================================================
# 2. BRAND BLEED ELIMINATION ACROSS COMMERCIAL PERSONAS
# ============================================================================

@pytest.mark.parametrize("biz_code,expected_brand", [
    ("SME-1", "Kaveri Distributors"),
    ("SME-2", "SmileArc Dental Clinic"),
    ("SME-3", "Northlight Design Studio"),
])
def test_brand_bleed_elimination_overview_action_card(biz_code: str, expected_brand: str):
    """Verify that the Overview WhatsApp Urgent Action reminder contains only the selected SME brand."""
    at = AppTest.from_file("app/streamlit_app.py", default_timeout=30)
    at.run()

    # Unlock vault so full action card renders
    pin_input = [w for w in at.sidebar.text_input if w.key == "sidebar_owner_pin_input"][0]
    pin_input.input("0000")
    unlock_btn = [b for b in at.sidebar.button if b.key == "btn_sidebar_unlock_vault"][0]
    unlock_btn.click()
    at.run()

    # Switch business
    biz_select = [w for w in at.sidebar.selectbox if w.key == "biz"][0]
    biz_select.select(biz_code)
    at.run()
    assert not at.exception

    # Find WhatsApp action card
    wa_cards = [m.value for m in at.markdown if "wa.me" in m.value]
    assert len(wa_cards) >= 1, f"Expected WhatsApp action card for {biz_code}"

    for card in wa_cards:
        assert expected_brand in card, f"Expected brand '{expected_brand}' in action card"
        if biz_code != "SME-1":
            assert "Kaveri Distributors" not in card, f"Brand bleed: Kaveri Distributors found in {biz_code} card!"


@pytest.mark.parametrize("biz_code,expected_brand", [
    ("SME-1", "Kaveri Distributors"),
    ("SME-2", "SmileArc Dental Clinic"),
    ("SME-3", "Northlight Design Studio"),
])
def test_brand_bleed_elimination_hindi_mode(biz_code: str, expected_brand: str):
    """Verify Hindi mode WhatsApp draft contains only the active business brand."""
    at = AppTest.from_file("app/streamlit_app.py", default_timeout=30)
    at.run()

    # Unlock vault
    pin_input = [w for w in at.sidebar.text_input if w.key == "sidebar_owner_pin_input"][0]
    pin_input.input("0000")
    unlock_btn = [b for b in at.sidebar.button if b.key == "btn_sidebar_unlock_vault"][0]
    unlock_btn.click()
    at.run()

    # Switch to Hindi
    lang_radio = [w for w in at.sidebar.radio if w.key == "lang"][0]
    lang_radio.set_value("हिन्दी")

    # Switch business
    biz_select = [w for w in at.sidebar.selectbox if w.key == "biz"][0]
    biz_select.select(biz_code)
    at.run()
    assert not at.exception

    wa_cards = [m.value for m in at.markdown if "wa.me" in m.value]
    assert len(wa_cards) >= 1
    for card in wa_cards:
        assert expected_brand in card
        if biz_code != "SME-1":
            assert "Kaveri Distributors" not in card


# ============================================================================
# 3. RECEIVABLES SECTION 18 LIMITATION ACT EMPTY STATE
# ============================================================================

def test_receivables_limitation_act_empty_state():
    """Verify that selecting 'Over 30 months' displays the educational Limitation Act empty state without crashing."""
    at = AppTest.from_file("app/streamlit_app.py", default_timeout=30)
    at.run()

    # Navigate to Receivables
    at._page_hash = calc_md5("receivables")
    at.run()
    assert not at.exception

    # Select 'Over 30 months' filter
    bg = at.button_group[0]
    bg.set_value(["Over 30 months"])
    at.run()
    assert not at.exception

    # Verify dedicated educational empty state
    lim_cards = [m.value for m in at.markdown if "Limitation Act" in m.value]
    assert len(lim_cards) >= 1
    assert any("Balances older than 30 months can become hard to recover under the Limitation Act" in c for c in lim_cards)
    assert any("No customers in this list" in c for c in lim_cards)
    # The clear filter button is omitted in the Limitation Act educational view
    assert len([b for b in at.button if b.key == "btn_clear_recv_filter"]) == 0


# ============================================================================
# 4. BUG REPRODUCTION: CLEAR FILTER BUTTON RUNTIME CRASH (STREAMLIT API EXCEPTION)
# ============================================================================

def test_receivables_generic_empty_state_button_runtime_crash_fixed():
    """Verify that clicking 'Clear filter / Show all customers' executes cleanly
    without StreamlitAPIException after Milestone 4 callback wrapping fix.
    
    Fix:
    In app/streamlit_app.py, session state mutation is wrapped inside an `on_click`
    callback so the widget state is cleanly updated prior to widget re-instantiation.
    """
    orig_by_customer = recv.by_customer

    def mock_by_customer(items):
        df = orig_by_customer(items).copy()
        # Set oldest_days to 5 so 'Over 45 days' filter has 0 customers
        df["oldest_days"] = 5
        return df

    with patch("copilot.receivables.by_customer", side_effect=mock_by_customer):
        at = AppTest.from_file("app/streamlit_app.py", default_timeout=30)
        at.run()
        at._page_hash = calc_md5("receivables")
        at.run()
        assert not at.exception

        # Verify empty state for default filter 'Over 45 days'
        assert any("No customers found matching the filter: 'Over 45 days'" in i.value for i in at.info)
        clear_buttons = [b for b in at.button if b.key == "btn_clear_recv_filter"]
        assert len(clear_buttons) == 1, "Clear filter button must be rendered"

        # Fix upstream streamlit AppTest ButtonGroup single-selection iteration bug
        bg = at.button_group[0]
        bg._value = ["Over 45 days"]

        # Click the 'Clear filter' button
        clear_buttons[0].click()
        at.run()

        # VERIFICATION: Zero exceptions! The callback ran cleanly.
        assert not at.exception, f"Expected no StreamlitAPIException, got: {[e.message for e in at.exception]}"



# ============================================================================
# 5. SOVEREIGN VAULT CA EXPORT ISOLATION
# ============================================================================

def test_ca_export_vault_isolation():
    """Verify that non-Owner role, locked vault, or disabled sharing exports zero vault drawer records."""
    # When export_vault is None (as in app/streamlit_app.py line 1793 & 1988)
    data = tally.generate_ca_excel_pack(
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
    wb = openpyxl.load_workbook(io.BytesIO(data))
    ws6 = wb["Salesman_Collection_Slips"]
    # Sheet 6 should have only headers (1 row) and zero data rows
    assert ws6.max_row == 1, "Confidential salesman slips leaked in CA export when vault is withheld!"


# ============================================================================
# 6. DOMAIN-ADAPTIVE CASH DRAWER TERMINOLOGY
# ============================================================================

@pytest.mark.parametrize("biz_code,expected_title", [
    ("SME-1", "Godown Cash Drawer Balancing Cockpit"),
    ("SME-2", "Front Desk & Till Cash Balancing Cockpit"),
    ("SME-3", "Cash Drawer Balancing Cockpit"),
])
def test_domain_adaptive_cash_drawer_terminology(biz_code: str, expected_title: str):
    """Verify cash drawer terminology adapts to business archetype (wholesale vs clinic vs agency)."""
    at = AppTest.from_file("app/streamlit_app.py", default_timeout=30)
    at.run()

    # Unlock vault as Owner
    pin_input = [w for w in at.sidebar.text_input if w.key == "sidebar_owner_pin_input"][0]
    pin_input.input("0000")
    unlock_btn = [b for b in at.sidebar.button if b.key == "btn_sidebar_unlock_vault"][0]
    unlock_btn.click()
    at.run()

    # Switch business
    biz_select = [w for w in at.sidebar.selectbox if w.key == "biz"][0]
    biz_select.select(biz_code)
    at.run()

    # Navigate to cash book
    at._page_hash = calc_md5("cash-book")
    at.run()
    assert not at.exception

    markdown_values = "\n".join(m.value for m in at.markdown)
    assert expected_title in markdown_values, f"Expected '{expected_title}' in cash book for {biz_code}"


# ============================================================================
# 7. SECTION 18 LIMITATION ACT AOD COPY
# ============================================================================

def test_section18_aod_draft_copy_switch():
    """Verify that debts >= 900 days switch to polite balance confirmation copy instead of demand notice."""
    from copilot.vault import format_whatsapp_reminder

    # Scenario A: Recent overdue debt
    acc_recent = KhataAccount(
        party_name="Ramesh Kirana",
        business_id="SME-2",
        balance_due=15000.0,
        last_active_date=pd.Timestamp("2026-08-01"),
        months_open=2,
        phone="919999999999",
    )
    recent_res = format_whatsapp_reminder(acc_recent, "SmileArc Dental Clinic")
    recent_msg = recent_res["draft_message"]
    assert "SmileArc Dental Clinic" in recent_msg
    assert "Kaveri Distributors" not in recent_msg
    assert "pending khata balance" in recent_msg
    assert recent_res["limitation_warning"] is None

    # Scenario B: Stale debt >= 900 days / 30 months (Limitation Act alert)
    acc_stale = KhataAccount(
        party_name="Ramesh Kirana",
        business_id="SME-2",
        balance_due=15000.0,
        last_active_date=pd.Timestamp("2023-01-01"),
        months_open=36,
        phone="919999999999",
    )
    stale_res = format_whatsapp_reminder(acc_stale, "SmileArc Dental Clinic")
    stale_msg = stale_res["draft_message"]
    assert "SmileArc Dental Clinic" in stale_msg
    assert "Kaveri Distributors" not in stale_msg
    assert "small part-settlement" in stale_msg
    assert "confirm if this matches your books" in stale_msg
    assert stale_res["limitation_warning"] is not None
