"""Comprehensive Test Suite for FastAPI Microservice & ADR Invariants.

Verifies:
1. SPEC-API-005 contract adherence across all endpoints.
2. ADR-001: Zero plaintext drawer cash leakage in server payloads & SSE stream template tokens.
3. ADR-002: Deterministic Decision 60 tiering (AUTO, SUGGEST, ASK, NO_DOC).
4. ADR-003: Section 18 Limitation Act tripwires for receivables >= 900 days.
5. ADR-004: Strict 5-sheet statutory export isolation omitting informal cash & route slips.
6. Brand bleed elimination across commercial personas (SME-1, SME-2, SME-3).
"""
import io
import json
import openpyxl
import pytest
from fastapi.testclient import TestClient

from copilot.api.app import app
from copilot.api.schemas import (
    ForecastPayload,
    OverviewPayload,
    ReceivablesPayload,
    ReviewQueuePayload,
)

client = TestClient(app)


# ============================================================================
# 1. System Health & Root Endpoints
# ============================================================================
def test_api_health_check():
    """Verify microservice health check endpoint."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "copilot-api"


def test_api_root():
    """Verify microservice root endpoint."""
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == "SME Cash-Flow Copilot API"
    assert data["status"] == "active"


# ============================================================================
# 2. Overview Cockpit Endpoint (View 1 & ADR-001)
# ============================================================================
def test_api_overview_contract_and_solvency():
    """Verify GET /api/v1/overview payload matches OverviewPayload schema and ADR-001."""
    res = client.get("/api/v1/overview?biz=SME-1")
    assert res.status_code == 200
    data = res.json()

    # Validate against Pydantic schema
    payload = OverviewPayload.model_validate(data)
    assert payload.business_id == "SME-1"
    assert payload.business_name == "Kaveri Distributors"
    assert payload.bank_current_balance != 0.0
    assert payload.cc_sanctioned_limit >= 0.0
    assert len(payload.pulse_metrics) == 4

    # ADR-001: Solvency equation contains only formal parameters
    solvency = payload.solvency_base
    assert solvency.formal_bank_balance == payload.bank_current_balance
    assert solvency.formal_receivables > 0.0
    assert solvency.default_khata_realization_rate == 0.85

    # Check top focal action
    if payload.top_focal_action:
        assert payload.top_focal_action.customer_name != ""
        assert payload.top_focal_action.total_outstanding > 0.0


@pytest.mark.parametrize("biz_code,expected_name", [
    ("SME-1", "Kaveri Distributors"),
    ("SME-2", "SmileArc Dental Clinic"),
    ("SME-3", "Northlight Design Studio"),
])
def test_api_overview_brand_bleed_elimination(biz_code: str, expected_name: str):
    """Verify overview API dynamically resolves authentic business name, eliminating brand bleed."""
    res = client.get(f"/api/v1/overview?biz={biz_code}")
    assert res.status_code == 200
    data = res.json()
    assert data["businessName"] == expected_name
    if biz_code != "SME-1":
        assert "Kaveri Distributors" not in data["businessName"]


# ============================================================================
# 3. Forecast & Simulation Endpoint (View 3 & ADR-002)
# ============================================================================
def test_api_forecast_monte_carlo():
    """Verify GET /api/v1/forecast returns 90 simulation points and monthly matrix."""
    res = client.get("/api/v1/forecast?biz=SME-1&paths=100")
    assert res.status_code == 200
    data = res.json()

    payload = ForecastPayload.model_validate(data)
    assert payload.business_id == "SME-1"
    assert len(payload.simulation_points) == 90
    assert len(payload.monthly_matrix) >= 3

    # Statistical validity
    p0 = payload.simulation_points[0]
    assert p0.p10_worst_case <= p0.p50_median <= p0.p90_optimistic
    assert payload.holdout_mape_score <= 0.182  # D31 kill metric
    assert payload.holdout_coverage_rate >= 0.85


# ============================================================================
# 4. Review Queue & Reconcile Endpoints (View 4 & ADR-002, ADR-004)
# ============================================================================
def test_api_review_queue_and_tier_filter():
    """Verify GET /api/v1/review triage counts and tier filtering."""
    res_all = client.get("/api/v1/review?biz=SME-1")
    assert res_all.status_code == 200
    data_all = res_all.json()

    payload_all = ReviewQueuePayload.model_validate(data_all)
    assert payload_all.total_count > 1000
    assert "AUTO" in payload_all.counts_by_tier
    assert "SUGGEST" in payload_all.counts_by_tier
    assert "ASK" in payload_all.counts_by_tier

    # Filter by SUGGEST
    res_sug = client.get("/api/v1/review?biz=SME-1&tier=SUGGEST")
    assert res_sug.status_code == 200
    data_sug = res_sug.json()
    for item in data_sug["items"]:
        assert item["tier"] == "SUGGEST"


def test_api_review_reconcile_audit_hash():
    """Verify POST /api/v1/review/reconcile generates immutable MCA Rule 11(g) audit hash."""
    reconcile_body = {
        "txnId": "TXN-TEST-123",
        "decision": "APPROVE",
        "assignedPartyId": "PARTY-001",
        "note": "Reconciled against verified delivery slip",
    }
    res = client.post("/api/v1/review/reconcile", json=reconcile_body)
    assert res.status_code == 200
    data = res.json()

    assert data["success"] is True
    assert data["txnId"] == "TXN-TEST-123"
    assert data["newStatus"] == "APPROVED"
    assert len(data["auditHash"]) == 64  # SHA-256


# ============================================================================
# 5. Receivables & Section 18 Tripwire Endpoint (View 5 & ADR-003)
# ============================================================================
def test_api_receivables_limitation_act_alerts():
    """Verify GET /api/v1/receivables flags Section 18 30-month debts."""
    res = client.get("/api/v1/receivables?biz=SME-1")
    assert res.status_code == 200
    data = res.json()

    payload = ReceivablesPayload.model_validate(data)
    assert payload.business_id == "SME-1"
    assert payload.total_outstanding > 0.0
    assert len(payload.customers) > 0

    # Ensure limitation alert flag is mathematically consistent with oldestInvoiceDays >= 900
    for cust in payload.customers:
        if cust.oldest_invoice_days >= 900:
            assert cust.is_limitation_alert is True
        else:
            assert cust.is_limitation_alert is False


# ============================================================================
# 6. Conversational Copilot SSE Stream Endpoint (View 6 & ADR-001)
# ============================================================================
def test_api_copilot_stream_adr001_template_tokens():
    """Verify POST /api/v1/copilot/stream emits SSE chunks with template tokens for vault cash."""
    chat_body = {
        "question": "Can I pay salaries on 1 October?",
        "businessId": "SME-1",
        "asOfDate": "2026-09-30",
    }
    res = client.post("/api/v1/copilot/stream", json=chat_body)
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    raw_text = res.text
    assert "data: " in raw_text

    # Parse SSE events
    events = []
    for line in raw_text.split("\n"):
        if line.startswith("data: "):
            payload = json.loads(line[6:])
            events.append(payload)

    event_types = [e.get("type") for e in events]
    assert "tool_start" in event_types
    assert "tool_done" in event_types
    assert "token" in event_types
    assert "template_token" in event_types
    assert "done" in event_types

    # Invariant: Template token must be exactly {{LOCAL_VAULT_GALLA_CASH}}
    template_events = [e for e in events if e.get("type") == "template_token"]
    assert len(template_events) >= 1
    assert template_events[0]["token"] == "{{LOCAL_VAULT_GALLA_CASH}}"
    assert template_events[0]["field"] == "gallaCash"


# ============================================================================
# 7. Statutory Tally & CA Excel Exports (View 7 & ADR-004 Split-Plane Firewall)
# ============================================================================
def test_api_export_tally_xml():
    """Verify POST /api/v1/exports/tally-xml generates valid TDL XML."""
    req_body = {
        "businessId": "SME-1",
        "asOfDate": "2026-09-30",
        "voucherType": "Receipt",
        "includeAutoOnly": True,
    }
    res = client.post("/api/v1/exports/tally-xml", json=req_body)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/xml"
    assert "<ENVELOPE>" in res.text
    assert "<TALLYREQUEST>Import Data</TALLYREQUEST>" in res.text
    assert "<REPORTNAME>Vouchers</REPORTNAME>" in res.text


def test_api_export_ca_excel_strict_5_sheets_no_vault_leak():
    """Verify POST /api/v1/exports/ca-excel strictly enforces the 5-sheet statutory firewall under ADR-004.
    Sheet 6 (Salesman_Collection_Slips) and Block D (till cash cross-checks) MUST NEVER be present!
    """
    req_body = {
        "businessId": "SME-1",
        "asOfDate": "2026-09-30",
        "format": "STATUTORY_5_SHEET",
        "omitInformalCash": True,
    }
    res = client.post("/api/v1/exports/ca-excel", json=req_body)
    assert res.status_code == 200
    assert "spreadsheetml.sheet" in res.headers["content-type"]

    wb = openpyxl.load_workbook(io.BytesIO(res.content))

    # Invariant: Exactly 5 sheets
    assert len(wb.sheetnames) == 5, f"Expected 5 sheets in statutory pack, got {len(wb.sheetnames)}: {wb.sheetnames}"
    assert "Salesman_Collection_Slips" not in wb.sheetnames, "LEAK: Salesman_Collection_Slips present in statutory export!"

    expected_sheets = [
        "Reconciliation_Summary",
        "Matched_Receipts_AUTO",
        "Suggested_Matches",
        "Unmatched_Bank_Credits",
        "Open_Invoices_Aging",
    ]
    for s in expected_sheets:
        assert s in wb.sheetnames

    # Invariant: Sheet 1 must NOT contain Block D till cash cross-checks
    ws1 = wb["Reconciliation_Summary"]
    all_cells_text = [str(cell.value) for row in ws1.iter_rows() for cell in row if cell.value is not None]
    assert not any("CASH DRAWER & COLLECTIONS CROSS-CHECK" in txt for txt in all_cells_text), (
        "LEAK: Block D till cash cross-checks found in Sheet 1 of statutory export!"
    )
    assert not any("Drawer Counted Cash" in txt for txt in all_cells_text), (
        "LEAK: Drawer Counted Cash found in Sheet 1 of statutory export!"
    )


def test_api_export_internal_diagnostic_excel_pin_gating():
    """Verify internal diagnostic export requires owner authentication."""
    # Unauthenticated attempt should fail with 403
    unauth_body = {
        "businessId": "SME-1",
        "asOfDate": "2026-09-30",
        "format": "INTERNAL_DUAL_PLANE_6_SHEET",
        "ownerPinAuthenticated": False,
    }
    res_unauth = client.post("/api/v1/exports/internal-diagnostic-excel", json=unauth_body)
    assert res_unauth.status_code == 403

    # The client's own "authenticated" claim is not enough; the server checks the PIN.
    claim_only = {**unauth_body, "ownerPinAuthenticated": True}
    assert client.post("/api/v1/exports/internal-diagnostic-excel", json=claim_only).status_code == 403

    # Correct owner PIN succeeds with 6 sheets
    auth_body = {
        "businessId": "SME-1",
        "asOfDate": "2026-09-30",
        "format": "INTERNAL_DUAL_PLANE_6_SHEET",
        "ownerPin": "0000",
    }
    res_auth = client.post("/api/v1/exports/internal-diagnostic-excel", json=auth_body)
    assert res_auth.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(res_auth.content))
    assert "Salesman_Collection_Slips" in wb.sheetnames


def test_api_exports_summary():
    """Verify GET /api/v1/exports/summary returns scorecard and sheet count."""
    res = client.get("/api/v1/exports/summary?biz=SME-1")
    assert res.status_code == 200
    data = res.json()
    assert data["caWorkbookSheetCount"] == 5
    assert data["tallyVouchersAvailable"] > 1000
    assert data["integrityScorecard"]["is100PercentTied"] is True


def test_api_export_alias_routing():
    """Verify singular /api/v1/export alias routes cleanly to export endpoints without 404."""
    # 1. Alias GET /api/v1/export/summary
    res_summary = client.get("/api/v1/export/summary?biz=SME-1")
    assert res_summary.status_code == 200
    assert res_summary.json()["caWorkbookSheetCount"] == 5

    # 2. Alias POST /api/v1/export/tally-xml
    res_tally = client.post("/api/v1/export/tally-xml", json={"businessId": "SME-1", "asOfDate": "2026-09-30"})
    assert res_tally.status_code == 200
    assert "xml" in res_tally.headers.get("content-type", "")

    # 3. Alias POST /api/v1/export/ca-excel
    res_ca = client.post(
        "/api/v1/export/ca-excel",
        json={"businessId": "SME-1", "asOfDate": "2026-09-30", "format": "STATUTORY_5_SHEET", "omitInformalCash": True},
    )
    assert res_ca.status_code == 200

