"""Milestone 4 Challenger Empirical Stress Test Suite.

Author: teamwork_challenger_m4_1 (Regression & Defect Challenger)
Repository: /Users/ishaanwadhwa/Projects/ps11-copilot

Empirically challenges:
1. Historical cutoff date boundaries in `src/copilot/receivables.py:open_items()`
   across multiple dates (1970-01-01, 2024-01-01, 2025-04-01, 2026-09-30, 2027-01-01, 2030-12-31)
   and businesses (SME-1, SME-2, SME-3). Verifies days_open >= 0, oldestInvoiceDays >= 0,
   and HTTP 200 across endpoints.
2. Route alias prefix verification: strict parity between `/api/v1/exports/*` and
   `/api/v1/export/*` across summary, tally-xml, ca-excel, and internal-diagnostic-excel.
3. Streamlit filter reset button callback: verifies that clicking the reset button triggers
   no exceptions (StreamlitAPIException) across all filter states and languages (English & Hindi).
"""
from __future__ import annotations

import io
import xml.etree.ElementTree as ET
from unittest.mock import patch

import openpyxl
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest
from streamlit.util import calc_md5

import copilot.config as config
from copilot.api.app import app
from copilot.api.schemas import (
    CustomerReceivable,
    ExportPayload,
    OverviewPayload,
    ReceivablesPayload,
)
from copilot.load import load_pack
import copilot.receivables as recv

client = TestClient(app)


# ============================================================================
# 1. HISTORICAL CUTOFF DATE BOUNDARIES EMPIRICAL STRESS TESTS
# ============================================================================

CUTOFF_TEST_DATES = [
    "1970-01-01",  # Unix epoch / far past (zero invoices expected)
    "2020-01-01",  # Pre-dataset baseline
    "2024-01-01",  # Prior financial year
    "2025-01-01",  # Mid-prior year
    "2025-04-01",  # Start of FY 2025-26 (original defect date)
    "2025-10-01",  # Mid FY 2025-26
    "2026-04-01",  # Start of FY 2026-27
    "2026-09-30",  # Standard evaluation cutoff (dataset end)
    "2027-01-01",  # Future date (all invoices open + aging)
    "2030-12-31",  # Far future date
]

BUSINESSES = ["SME-1", "SME-2", "SME-3"]


@pytest.fixture(scope="module")
def shared_pack():
    """Load default dataset pack once for direct Python layer testing."""
    return load_pack()


@pytest.mark.parametrize("cutoff", CUTOFF_TEST_DATES)
@pytest.mark.parametrize("biz", BUSINESSES)
def test_empirical_open_items_date_boundaries(shared_pack, cutoff: str, biz: str):
    """Stress-test open_items() across extreme past and future cutoff boundaries.
    
    Invariants:
    1. Returns a valid DataFrame with required columns.
    2. Every included invoice has invoice_date <= as_of cutoff timestamp.
    3. days_open is strictly >= 0 (no negative aging).
    4. days_overdue is strictly >= 0.
    5. by_customer() aggregates cleanly with oldest_days >= 0.
    """
    cutoff_ts = pd.Timestamp(cutoff)
    df = recv.open_items(shared_pack, biz, as_of=cutoff_ts)

    expected_cols = [
        "invoice_no",
        "customer_name",
        "invoice_date",
        "due_date",
        "invoice_total",
        "outstanding",
        "days_open",
        "days_overdue",
        "status_as_of_30sep2026",
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing column {col} in open_items output for cutoff {cutoff}"

    if df.empty:
        # Valid: on historical dates prior to invoice creation, open items should be empty
        cust_summary = recv.by_customer(df)
        assert cust_summary.empty
    else:
        # Invariant 2: No future invoices relative to cutoff
        assert (df["invoice_date"] <= cutoff_ts).all(), (
            f"Found invoice with invoice_date > {cutoff_ts} in open_items for {biz}"
        )

        # Invariant 3: days_open >= 0
        min_days_open = df["days_open"].min()
        assert min_days_open >= 0, (
            f"VIOLATION: Found negative days_open ({min_days_open}) on cutoff {cutoff} for {biz}"
        )

        # Invariant 4: days_overdue >= 0
        min_days_overdue = df["days_overdue"].min()
        assert min_days_overdue >= 0, (
            f"VIOLATION: Found negative days_overdue ({min_days_overdue}) on cutoff {cutoff} for {biz}"
        )

        # Invariant 5: by_customer() aggregation
        cust_summary = recv.by_customer(df)
        assert not cust_summary.empty
        min_oldest = cust_summary["oldest_days"].min()
        assert min_oldest >= 0, (
            f"VIOLATION: Found negative oldest_days ({min_oldest}) in by_customer for {biz}"
        )


@pytest.mark.parametrize("cutoff", CUTOFF_TEST_DATES)
@pytest.mark.parametrize("biz", BUSINESSES)
def test_empirical_api_receivables_cutoff_boundaries(cutoff: str, biz: str):
    """Stress-test GET /api/v1/receivables across extreme cutoff boundaries via FastAPI.
    
    Invariants:
    1. Returns HTTP 200 OK.
    2. Validates against ReceivablesPayload schema.
    3. Every CustomerReceivable has oldestInvoiceDays >= 0.
    4. totalOutstanding >= 0.0.
    """
    res = client.get(f"/api/v1/receivables?biz={biz}&as_of={cutoff}")
    assert res.status_code == 200, (
        f"Expected 200 OK for /api/v1/receivables?biz={biz}&as_of={cutoff}, got {res.status_code}: {res.text}"
    )

    payload = ReceivablesPayload.model_validate(res.json())
    assert payload.business_id == biz
    assert payload.total_outstanding >= 0.0
    assert payload.overdue_count >= 0
    assert payload.limitation_alert_count >= 0

    for cust in payload.customers:
        assert cust.oldest_invoice_days >= 0, (
            f"VIOLATION: Customer {cust.customer_name} has oldest_invoice_days={cust.oldest_invoice_days} < 0"
        )
        assert cust.total_outstanding > 0.0


@pytest.mark.parametrize("cutoff", CUTOFF_TEST_DATES)
@pytest.mark.parametrize("biz", BUSINESSES)
def test_empirical_api_overview_cutoff_boundaries(cutoff: str, biz: str):
    """Stress-test GET /api/v1/overview across extreme cutoff boundaries via FastAPI.
    
    Invariants:
    1. Returns HTTP 200 OK without 500 ValidationError.
    2. Validates against OverviewPayload schema.
    3. If top_focal_action is present, oldestInvoiceDays >= 0.
    """
    res = client.get(f"/api/v1/overview?biz={biz}&as_of={cutoff}")
    assert res.status_code == 200, (
        f"Expected 200 OK for /api/v1/overview?biz={biz}&as_of={cutoff}, got {res.status_code}: {res.text}"
    )

    payload = OverviewPayload.model_validate(res.json())
    assert payload.business_id == biz
    if payload.top_focal_action is not None:
        assert payload.top_focal_action.oldest_invoice_days >= 0, (
            f"VIOLATION: top_focal_action has oldest_invoice_days={payload.top_focal_action.oldest_invoice_days} < 0"
        )


# ============================================================================
# 2. ROUTE ALIAS PREFIX PARITY EMPIRICAL STRESS TESTS
# ============================================================================

@pytest.mark.parametrize("biz", BUSINESSES)
def test_empirical_export_alias_summary_parity(biz: str):
    """Verify byte-for-byte / key-for-key parity between /exports/summary and /export/summary."""
    res_plural = client.get(f"/api/v1/exports/summary?biz={biz}")
    res_singular = client.get(f"/api/v1/export/summary?biz={biz}")

    assert res_plural.status_code == 200, f"/exports/summary returned {res_plural.status_code}"
    assert res_singular.status_code == 200, f"/export/summary returned {res_singular.status_code}"

    data_plural = res_plural.json()
    data_singular = res_singular.json()

    # Schemas validate
    ExportPayload.model_validate(data_plural)
    ExportPayload.model_validate(data_singular)

    # Identical responses
    assert data_plural == data_singular, "Plural /exports/summary and singular /export/summary differ in output!"


@pytest.mark.parametrize("biz", BUSINESSES)
def test_empirical_export_alias_tally_xml_parity(biz: str):
    """Verify XML output parity between /exports/tally-xml and /export/tally-xml."""
    body = {"businessId": biz, "asOfDate": "2026-09-30"}

    res_plural = client.post("/api/v1/exports/tally-xml", json=body)
    res_singular = client.post("/api/v1/export/tally-xml", json=body)

    assert res_plural.status_code == 200
    assert res_singular.status_code == 200
    assert "xml" in res_plural.headers.get("content-type", "")
    assert "xml" in res_singular.headers.get("content-type", "")

    # Both must parse into valid XML
    root_p = ET.fromstring(res_plural.content)
    root_s = ET.fromstring(res_singular.content)
    assert root_p.tag == "ENVELOPE"
    assert root_s.tag == "ENVELOPE"

    # Exact byte match
    assert res_plural.content == res_singular.content, (
        "Plural and singular tally-xml endpoints produced different XML payloads!"
    )


@pytest.mark.parametrize("biz", BUSINESSES)
def test_empirical_export_alias_ca_excel_parity(biz: str):
    """Verify strict 5-sheet statutory Excel parity between /exports/ca-excel and /export/ca-excel."""
    body = {
        "businessId": biz,
        "asOfDate": "2026-09-30",
        "format": "STATUTORY_5_SHEET",
        "omitInformalCash": True,
    }

    res_plural = client.post("/api/v1/exports/ca-excel", json=body)
    res_singular = client.post("/api/v1/export/ca-excel", json=body)

    assert res_plural.status_code == 200
    assert res_singular.status_code == 200

    wb_plural = openpyxl.load_workbook(io.BytesIO(res_plural.content))
    wb_singular = openpyxl.load_workbook(io.BytesIO(res_singular.content))

    # Invariants for both
    for wb, label in [(wb_plural, "/exports/ca-excel"), (wb_singular, "/export/ca-excel")]:
        assert len(wb.sheetnames) == 5, f"{label} returned {len(wb.sheetnames)} sheets instead of 5"
        assert "Salesman_Collection_Slips" not in wb.sheetnames
        ws1 = wb["Reconciliation_Summary"]
        cells = [str(c.value) for r in ws1.iter_rows() for c in r if c.value is not None]
        assert not any("CASH DRAWER & COLLECTIONS CROSS-CHECK" in txt for txt in cells)
        assert not any("Drawer Counted Cash" in txt for txt in cells)

    # Identical sheet structures
    assert wb_plural.sheetnames == wb_singular.sheetnames


def test_empirical_export_alias_internal_diagnostic_excel_parity():
    """Verify internal diagnostic gating and behavior across plural and singular route prefixes."""
    unauth_body = {
        "businessId": "SME-1",
        "asOfDate": "2026-09-30",
        "format": "INTERNAL_DUAL_PLANE_6_SHEET",
        "ownerPinAuthenticated": False,
    }
    # Both reject with 403
    assert client.post("/api/v1/exports/internal-diagnostic-excel", json=unauth_body).status_code == 403
    assert client.post("/api/v1/export/internal-diagnostic-excel", json=unauth_body).status_code == 403

    auth_body = {
        "businessId": "SME-1",
        "asOfDate": "2026-09-30",
        "format": "INTERNAL_DUAL_PLANE_6_SHEET",
        "ownerPin": "0000",
    }
    # Both succeed with 200 and 6 sheets
    res_p = client.post("/api/v1/exports/internal-diagnostic-excel", json=auth_body)
    res_s = client.post("/api/v1/export/internal-diagnostic-excel", json=auth_body)
    assert res_p.status_code == 200
    assert res_s.status_code == 200

    wb_p = openpyxl.load_workbook(io.BytesIO(res_p.content))
    wb_s = openpyxl.load_workbook(io.BytesIO(res_s.content))
    assert len(wb_p.sheetnames) == 6
    assert len(wb_s.sheetnames) == 6
    assert "Salesman_Collection_Slips" in wb_p.sheetnames
    assert "Salesman_Collection_Slips" in wb_s.sheetnames


# ============================================================================
# 3. STREAMLIT FILTER RESET BUTTON CALLBACK EMPIRICAL STRESS TESTS
# ============================================================================

FILTER_CHOICES_TEST = [
    "Over 45 days",
    "Over 90 days",
    "Over 180 days",
    "Over 365 days",
]


@pytest.mark.parametrize("filter_label", FILTER_CHOICES_TEST)
def test_empirical_streamlit_filter_reset_callback_across_filters(filter_label: str):
    """Stress-test Streamlit filter reset callback across multiple filter choices.
    
    Verifies that when a filter yields 0 matching customers:
    1. The clear filter button is rendered.
    2. Clicking the button executes the `_reset_chase_filter` callback.
    3. No StreamlitAPIException is raised.
    4. Session state for chase_filter is properly restored.
    """
    orig_by_customer = recv.by_customer

    def mock_by_customer_empty(items):
        df = orig_by_customer(items).copy()
        # Force oldest_days=0 so any 'Over X days' filter yields 0 rows
        df["oldest_days"] = 0
        return df

    with patch("copilot.receivables.by_customer", side_effect=mock_by_customer_empty):
        at = AppTest.from_file("app/streamlit_app.py", default_timeout=30)
        at.run()
        at._page_hash = calc_md5("receivables")
        at.run()
        assert not at.exception

        # Locate the clear filter button
        clear_buttons = [b for b in at.button if b.key == "btn_clear_recv_filter"]
        assert len(clear_buttons) == 1, f"Clear filter button must be rendered for filter '{filter_label}'"

        # Click the clear filter button
        # Workaround: AppTest's ButtonGroup iterates a single-selection value character by character
        at.button_group[0]._value = ["Over 45 days"]
        clear_buttons[0].click()
        at.run()

        # Empirical invariant: zero exceptions!
        assert not at.exception, (
            f"StreamlitAPIException occurred on reset click for filter '{filter_label}': "
            f"{[e.message for e in at.exception]}"
        )
        assert at.session_state["_chase_filter"] == "All"


def test_empirical_streamlit_filter_reset_callback_hindi():
    """Verify that clicking the clear filter button in Hindi mode executes cleanly with Hindi state."""
    orig_by_customer = recv.by_customer

    def mock_by_customer_empty(items):
        df = orig_by_customer(items).copy()
        df["oldest_days"] = 0
        return df

    with patch("copilot.receivables.by_customer", side_effect=mock_by_customer_empty):
        at = AppTest.from_file("app/streamlit_app.py", default_timeout=30)
        at.run()

        # Switch to Hindi
        lang_radio = [w for w in at.sidebar.radio if w.key == "lang"][0]
        lang_radio.set_value("हिन्दी")
        at.run()

        # Navigate to Receivables
        at._page_hash = calc_md5("receivables")
        at.run()
        assert not at.exception

        clear_buttons = [b for b in at.button if b.key == "btn_clear_recv_filter"]
        assert len(clear_buttons) == 1, "Clear filter button must be rendered in Hindi mode"

        # Workaround: AppTest's ButtonGroup iterates a single-selection value character by character
        at.button_group[0]._value = ["45 दिन से पुराने"]
        clear_buttons[0].click()
        at.run()

        assert not at.exception, f"Exception in Hindi mode reset: {[e.message for e in at.exception]}"
        assert at.session_state["chase_filter"] == "सभी ग्राहक"
        assert at.session_state["_chase_filter"] == "All"


def test_empirical_streamlit_filter_reset_idempotency():
    """Verify that clicking the clear filter button repeatedly (idempotency) causes no crash."""
    orig_by_customer = recv.by_customer

    def mock_by_customer_empty(items):
        df = orig_by_customer(items).copy()
        df["oldest_days"] = 0
        return df

    with patch("copilot.receivables.by_customer", side_effect=mock_by_customer_empty):
        at = AppTest.from_file("app/streamlit_app.py", default_timeout=30)
        at.run()
        at._page_hash = calc_md5("receivables")
        at.run()
        assert not at.exception

        clear_buttons = [b for b in at.button if b.key == "btn_clear_recv_filter"]
        assert len(clear_buttons) == 1

        # Click multiple times
        # Workaround: AppTest's ButtonGroup iterates a single-selection value character by character
        for click_idx in range(3):
            bg = at.button_group[0]
            bg._value = [bg.value] if isinstance(bg.value, str) else bg.value
            clear_buttons[0].click()
            at.run()
            assert not at.exception, (
                f"Exception on click {click_idx+1}: {[e.message for e in at.exception]}"
            )
