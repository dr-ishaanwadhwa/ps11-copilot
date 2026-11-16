"""Adversarial Empirical Stress-Testing Suite for Milestone 3 (FastAPI BFF Microservice).

Author: Challenger 1 (critic, specialist)
Repository: /Users/ishaanwadhwa/Projects/ps11-copilot
Target: src/copilot/api/ (app.py, schemas.py, routers/)

Empirical Stress Tests:
1. System Health, Root, and Middleware
2. Overview Cockpit: Multi-SME Personas, Brand Bleed, Cutoff Boundaries, and ADR-001 Invariants
3. Forecast & Monte Carlo Simulation: Horizon, Stress Parameter Clamping, and Milestone Invariants
4. Decision 60 Review Queue: Triage Counts and Exhaustive Tier Filtering (AUTO, SUGGEST, ASK, NO_DOC)
5. Review Reconcile: Decision States, 422 Rejections, and MCA Rule 11(g) SHA-256 Audit Hashes
6. Receivables: Section 18 Limitation Act (>=900 Days) Mathematical Exactness
7. Conversational Copilot SSE Stream: Chunk Hierarchy, Citations, and ADR-001 Template Tokens
8. Statutory Tally XML Export: Pure TDL XML, 8-Digit Dates, Voucher Structures, and 422 Handling
9. Statutory CA Excel Export: Strict 5-Sheet Isolation, Zero Sheet 6, Zero Block D Till Cash Leakage
10. Internal Diagnostic Excel: Owner PIN Gating (403 vs 200 Dual-Plane 6-Sheet)
11. Exports Summary Scorecard: 100% Tie-out and Sheet Count Verification
12. BUG REPRODUCTION: Unhandled HTTP 500 ValidationError on Past Cutoff Dates (start of FY25-26)
"""
from __future__ import annotations

import io
import json
import re
import xml.etree.ElementTree as ET
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
# 1. System Health, Root, and Middleware
# ============================================================================
def test_adv_health_and_root():
    """Stress-test health and root endpoints for status, timing headers, and 404 resilience."""
    # Health check
    res_h = client.get("/health")
    assert res_h.status_code == 200
    data_h = res_h.json()
    assert data_h["status"] == "ok"
    assert data_h["service"] == "copilot-api"
    assert "X-Process-Time" in res_h.headers
    assert res_h.headers["X-Process-Time"].endswith("ms")

    # Root endpoint
    res_r = client.get("/")
    assert res_r.status_code == 200
    data_r = res_r.json()
    assert data_r["status"] == "active"
    assert data_r["service"] == "SME Cash-Flow Copilot API"
    assert "X-Process-Time" in res_r.headers

    # Non-existent endpoint must return 404
    res_404 = client.get("/api/v1/nonexistent_endpoint")
    assert res_404.status_code == 404


# ============================================================================
# 2. Overview Cockpit: Multi-SME Personas & Cutoff Boundaries
# ============================================================================
@pytest.mark.parametrize("biz_code,expected_brand", [
    ("SME-1", "Kaveri Distributors"),
    ("SME-2", "SmileArc Dental Clinic"),
    ("SME-3", "Northlight Design Studio"),
])
def test_adv_overview_personas_and_brand_bleed(biz_code: str, expected_brand: str):
    """Verify Overview API resolves correct authentic business brand and eliminates brand bleed."""
    res = client.get(f"/api/v1/overview?biz={biz_code}")
    assert res.status_code == 200
    payload = OverviewPayload.model_validate(res.json())

    assert payload.business_id == biz_code
    assert payload.business_name == expected_brand
    if biz_code != "SME-1":
        assert "Kaveri Distributors" not in payload.business_name

    # Pulse metrics must contain exactly 4 vitals
    assert len(payload.pulse_metrics) == 4
    metric_ids = [m.id for m in payload.pulse_metrics]
    assert "bank_balance" in metric_ids
    assert "cc_headroom" in metric_ids
    assert "formal_receivables" in metric_ids
    assert "due_next_30" in metric_ids

    # ADR-001 Invariant: Solvency equation contains only formal parameters
    solv = payload.solvency_base
    assert solv.formal_bank_balance == payload.bank_current_balance
    assert solv.default_khata_realization_rate == 0.85
    assert not hasattr(solv, "drawer_cash")
    assert not hasattr(solv, "galla_cash")


@pytest.mark.parametrize("as_of_input", [
    "2026-09-30",
    "2026-06-30",
    "2026-01-15",
    "invalid-date-format",
    "9999-99-99",
    "",
])
def test_adv_overview_cutoff_boundary_resilience(as_of_input: str):
    """Verify overview handles valid dates, future dates, and malformed date strings gracefully."""
    url = f"/api/v1/overview?biz=SME-1&as_of={as_of_input}" if as_of_input else "/api/v1/overview?biz=SME-1"
    res = client.get(url)
    assert res.status_code == 200
    data = res.json()
    payload = OverviewPayload.model_validate(data)
    assert payload.business_id == "SME-1"
    assert isinstance(payload.bank_current_balance, float)
    assert isinstance(payload.runway_months, float)


def test_adv_overview_unknown_business_id():
    """Verify unknown business ID falls back gracefully without 500 error."""
    res = client.get("/api/v1/overview?biz=UNKNOWN_BIZ")
    assert res.status_code == 200
    data = res.json()
    assert data["businessId"] == "UNKNOWN_BIZ"
    assert data["businessName"] == "Business-UNKNOWN_BIZ"
    assert data["bankCurrentBalance"] == 0.0


# ============================================================================
# 3. Forecast & Monte Carlo Simulation Endpoints
# ============================================================================
@pytest.mark.parametrize("endpoint", ["/api/v1/forecast", "/api/v1/forecast/monte-carlo"])
@pytest.mark.parametrize("path_count", [1, 100, 500, 2500, -10])
def test_adv_forecast_path_clamping_and_statistical_invariants(endpoint: str, path_count: int):
    """Verify forecast Monte Carlo simulation clamps extreme path counts and enforces P10 <= P50 <= P90."""
    res = client.get(f"{endpoint}?biz=SME-1&paths={path_count}")
    assert res.status_code == 200
    data = res.json()
    payload = ForecastPayload.model_validate(data)

    assert payload.business_id == "SME-1"
    assert len(payload.simulation_points) == 90
    assert len(payload.monthly_matrix) >= 3

    # D31 Kill Metrics Calibration
    assert payload.holdout_mape_score <= 0.182
    assert payload.holdout_coverage_rate >= 0.85

    # Enforce P10 <= P50 <= P90 across every single day of the 90-day horizon
    for pt in payload.simulation_points:
        assert pt.p10_worst_case <= pt.p50_median <= pt.p90_optimistic, (
            f"Statistical violation on day {pt.day_index} ({pt.date}): "
            f"P10={pt.p10_worst_case}, P50={pt.p50_median}, P90={pt.p90_optimistic}"
        )

    # Verify statutory milestone events
    payroll_events = [p for p in payload.simulation_points if p.milestone_event and p.milestone_event.category == "SALARY"]
    assert len(payroll_events) >= 1
    gst_events = [p for p in payload.simulation_points if p.milestone_event and p.milestone_event.category == "GST_TAX"]
    assert len(gst_events) >= 1


# ============================================================================
# 4. Review Queue & Reconcile Endpoints (Decision 60 & MCA Rule 11(g))
# ============================================================================
@pytest.mark.parametrize("tier_filter", ["AUTO", "SUGGEST", "ASK", "NO_DOC", "ALL"])
def test_adv_review_queue_tier_filtering(tier_filter: str):
    """Verify Decision 60 review queue filtering returns strictly matching tier items."""
    res = client.get(f"/api/v1/review?biz=SME-1&tier={tier_filter}")
    assert res.status_code == 200
    payload = ReviewQueuePayload.model_validate(res.json())

    assert payload.total_count > 1000
    assert "AUTO" in payload.counts_by_tier
    assert "SUGGEST" in payload.counts_by_tier
    assert "ASK" in payload.counts_by_tier
    assert "NO_DOC" in payload.counts_by_tier
    assert sum(payload.counts_by_tier.values()) == payload.total_count

    if tier_filter != "ALL":
        for item in payload.items:
            assert item.tier == tier_filter, f"Item {item.txn_id} has tier {item.tier}, expected {tier_filter}"
    else:
        assert len(payload.items) > 0


def test_adv_review_queue_nonexistent_tier():
    """Verify unrecognized tier filter returns 0 items without 500 crash."""
    res = client.get("/api/v1/review?biz=SME-1&tier=NONEXISTENT_TIER")
    assert res.status_code == 200
    payload = ReviewQueuePayload.model_validate(res.json())
    assert len(payload.items) == 0
    assert payload.total_count > 1000


@pytest.mark.parametrize("decision,expected_status", [
    ("APPROVE", "APPROVED"),
    ("REJECT", "REJECTED"),
    ("REASSIGN", "REASSIGNED"),
])
def test_adv_review_reconcile_decisions_and_audit_hash(decision: str, expected_status: str):
    """Verify reconcile endpoint records MCA Rule 11(g) / BNS §241 64-char SHA-256 audit hashes."""
    body = {
        "txnId": f"TXN-ADV-{decision}-001",
        "decision": decision,
        "assignedPartyId": "PARTY-TEST-99",
        "note": f"Adversarial verification test for {decision}",
    }
    res = client.post("/api/v1/review/reconcile", json=body)
    assert res.status_code == 200
    data = res.json()

    assert data["success"] is True
    assert data["txnId"] == f"TXN-ADV-{decision}-001"
    assert data["newStatus"] == expected_status
    assert len(data["auditHash"]) == 64
    assert re.match(r"^[0-9a-f]{64}$", data["auditHash"])


def test_adv_review_reconcile_invalid_decision_validation():
    """Verify invalid reconcile decisions are rejected with HTTP 422 Unprocessable Entity."""
    body = {
        "txnId": "TXN-INV-01",
        "decision": "DELETE",  # Invalid decision not in Literal["APPROVE", "REJECT", "REASSIGN"]
    }
    res = client.post("/api/v1/review/reconcile", json=body)
    assert res.status_code == 422


# ============================================================================
# 5. Receivables & Section 18 Limitation Act Tripwire
# ============================================================================
@pytest.mark.parametrize("biz_code", ["SME-1", "SME-2", "SME-3"])
def test_adv_receivables_limitation_act_mathematical_consistency(biz_code: str):
    """Verify Section 18 Limitation Act tripwire is mathematically exact for oldestInvoiceDays >= 900."""
    res = client.get(f"/api/v1/receivables?biz={biz_code}")
    assert res.status_code == 200
    payload = ReceivablesPayload.model_validate(res.json())

    assert payload.business_id == biz_code
    assert payload.total_outstanding >= 0.0

    calculated_limitation_count = 0
    calculated_overdue_count = 0

    for cust in payload.customers:
        # Mathematical invariant: oldestInvoiceDays >= 900 <==> isLimitationAlert == True
        if cust.oldest_invoice_days >= 900:
            assert cust.is_limitation_alert is True, (
                f"Customer {cust.customer_name} has oldest days {cust.oldest_invoice_days} but isLimitationAlert is False"
            )
            calculated_limitation_count += 1
        else:
            assert cust.is_limitation_alert is False, (
                f"Customer {cust.customer_name} has oldest days {cust.oldest_invoice_days} but isLimitationAlert is True"
            )

        if cust.oldest_invoice_days >= 45:
            calculated_overdue_count += 1

    assert payload.limitation_alert_count == calculated_limitation_count
    assert payload.overdue_count == calculated_overdue_count


# ============================================================================
# 6. Conversational Copilot SSE Stream (ADR-001 Invariant)
# ============================================================================
@pytest.mark.parametrize("question", [
    "Can I pay salaries on 1 October?",
    "Who owes me the most money right now?",
    "What is my spendable cash headroom today?",
])
def test_adv_copilot_stream_sse_structure_and_template_tokens(question: str):
    """Verify SSE streaming chunk hierarchy and ADR-001 {{LOCAL_VAULT_GALLA_CASH}} template token emission."""
    req_body = {
        "question": question,
        "businessId": "SME-1",
        "asOfDate": "2026-09-30",
    }
    res = client.post("/api/v1/copilot/stream", json=req_body)
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    lines = res.text.strip().split("\n")
    events = []
    for line in lines:
        line_clean = line.strip()
        if line_clean.startswith("data: "):
            payload = json.loads(line_clean[6:])
            events.append(payload)

    event_types = [e.get("type") for e in events]
    assert "tool_start" in event_types
    assert "tool_done" in event_types
    assert "token" in event_types
    assert "done" in event_types

    # For queries referencing liquidity/salaries, ADR-001 template token MUST be emitted
    if "salar" in question.lower() or "headroom" in question.lower():
        template_events = [e for e in events if e.get("type") == "template_token"]
        assert len(template_events) >= 1
        assert template_events[0]["token"] == "{{LOCAL_VAULT_GALLA_CASH}}"
        assert template_events[0]["field"] == "gallaCash"

    # Invariant: Citations must be present and valid
    citation_events = [e for e in events if e.get("type") == "citation"]
    assert len(citation_events) >= 1
    for cit in citation_events:
        c_obj = cit["citation"]
        assert "id" in c_obj
        assert "source" in c_obj
        assert "badge" in c_obj


# ============================================================================
# 7. Statutory Tally XML Export
# ============================================================================
def test_adv_export_tally_xml_header_and_structure():
    """Verify POST /api/v1/exports/tally-xml produces valid XML with standard header and Tally envelope."""
    req_body = {
        "businessId": "SME-1",
        "asOfDate": "2026-09-30",
        "voucherType": "Receipt",
        "includeAutoOnly": True,
    }
    res = client.post("/api/v1/exports/tally-xml", json=req_body)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/xml"
    assert 'filename="tally_receipts_SME-1_2026-09-30.xml"' in res.headers["content-disposition"]

    # Verify XML Header
    xml_text = res.text
    assert xml_text.startswith('<?xml version="1.0" encoding="utf-8"?>')

    # Parse XML
    root = ET.fromstring(xml_text)
    assert root.tag == "ENVELOPE"

    header = root.find("HEADER")
    assert header is not None
    assert header.find("TALLYREQUEST").text == "Import Data"

    rep_name = root.find(".//REQUESTDESC/REPORTNAME")
    assert rep_name is not None and rep_name.text == "Vouchers"

    company_node = root.find(".//STATICVARIABLES/SVCURRENTCOMPANY")
    assert company_node is not None and company_node.text == "Kaveri Distributors"

    # Check vouchers
    vouchers = root.findall(".//TALLYMESSAGE/VOUCHER")
    assert len(vouchers) > 1000

    for vch in vouchers[:20]:
        assert vch.attrib.get("VOUCHERTYPE") == "Receipt"
        assert vch.attrib.get("ACTION") == "Create"
        date_node = vch.find("DATE")
        assert date_node is not None
        assert len(date_node.text) == 8 and date_node.text.isdigit()


def test_adv_export_tally_xml_invalid_voucher_type():
    """Verify invalid voucher types are rejected with 422."""
    req_body = {
        "businessId": "SME-1",
        "asOfDate": "2026-09-30",
        "voucherType": "Payment",  # Only 'Receipt' allowed in TallyExportRequest
    }
    res = client.post("/api/v1/exports/tally-xml", json=req_body)
    assert res.status_code == 422


# ============================================================================
# 8. Statutory CA Excel Export: Strict 5-Sheet Isolation (ADR-004)
# ============================================================================
@pytest.mark.parametrize("biz_code", ["SME-1", "SME-2", "SME-3"])
def test_adv_export_ca_excel_strict_5_sheet_isolation_all_smes(biz_code: str):
    """Verify statutory CA Excel export strictly enforces 5-sheet isolation across all SMEs.
    Salesman_Collection_Slips (Sheet 6) and Block D till cash cross-checks MUST NEVER exist!
    """
    req_body = {
        "businessId": biz_code,
        "asOfDate": "2026-09-30",
        "format": "STATUTORY_5_SHEET",
        "omitInformalCash": True,
    }
    res = client.post("/api/v1/exports/ca-excel", json=req_body)
    assert res.status_code == 200
    assert "spreadsheetml.sheet" in res.headers["content-type"]

    wb = openpyxl.load_workbook(io.BytesIO(res.content))

    # Invariant: EXACTLY 5 sheets, ZERO Sheet 6
    assert len(wb.sheetnames) == 5, f"Expected 5 sheets for {biz_code}, got {len(wb.sheetnames)}: {wb.sheetnames}"
    assert "Salesman_Collection_Slips" not in wb.sheetnames, (
        f"CRITICAL LEAK: Salesman_Collection_Slips found in {biz_code} statutory export!"
    )

    expected_sheets = [
        "Reconciliation_Summary",
        "Matched_Receipts_AUTO",
        "Suggested_Matches",
        "Unmatched_Bank_Credits",
        "Open_Invoices_Aging",
    ]
    assert wb.sheetnames == expected_sheets

    # Invariant: Sheet 1 MUST NOT contain Block D till cash cross checks
    ws1 = wb["Reconciliation_Summary"]
    all_cells_text = [str(cell.value) for row in ws1.iter_rows() for cell in row if cell.value is not None]
    assert not any("CASH DRAWER & COLLECTIONS CROSS-CHECK" in txt for txt in all_cells_text), (
        f"CRITICAL LEAK: Block D till cash found in Sheet 1 for {biz_code}!"
    )
    assert not any("Drawer Counted Cash" in txt for txt in all_cells_text), (
        f"CRITICAL LEAK: Drawer Counted Cash found in Sheet 1 for {biz_code}!"
    )


# ============================================================================
# 9. Internal Management Diagnostic Excel: Owner PIN Gating
# ============================================================================
def test_adv_export_internal_diagnostic_pin_gating():
    """Verify internal diagnostic export enforces 403 when unauthenticated and provides 6 sheets when authenticated."""
    # Unauthenticated attempt -> 403 Forbidden
    unauth_body = {
        "businessId": "SME-1",
        "asOfDate": "2026-09-30",
        "format": "INTERNAL_DUAL_PLANE_6_SHEET",
        "ownerPinAuthenticated": False,
    }
    res_unauth = client.post("/api/v1/exports/internal-diagnostic-excel", json=unauth_body)
    assert res_unauth.status_code == 403

    # The client's own claim is not authentication; the server checks the PIN (16 Nov review).
    claim_only = {**unauth_body, "ownerPinAuthenticated": True}
    assert client.post("/api/v1/exports/internal-diagnostic-excel", json=claim_only).status_code == 403

    # Correct owner PIN -> 200 OK with 6 sheets
    auth_body = {
        "businessId": "SME-1",
        "asOfDate": "2026-09-30",
        "format": "INTERNAL_DUAL_PLANE_6_SHEET",
        "ownerPin": "0000",
    }
    res_auth = client.post("/api/v1/exports/internal-diagnostic-excel", json=auth_body)
    assert res_auth.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(res_auth.content))
    assert len(wb.sheetnames) == 6
    assert "Salesman_Collection_Slips" in wb.sheetnames


# ============================================================================
# 10. Exports Summary Scorecard
# ============================================================================
def test_adv_exports_summary_tie_out():
    """Verify /api/v1/exports/summary reports 100% balance tie-out and 5 statutory sheets."""
    res = client.get("/api/v1/exports/summary?biz=SME-1")
    assert res.status_code == 200
    data = res.json()

    assert data["caWorkbookSheetCount"] == 5
    assert data["tallyVouchersAvailable"] > 1000
    assert data["tallyTotalCreditAmount"] > 0.0

    scorecard = data["integrityScorecard"]
    assert scorecard["totalBankLinesIngested"] > 1000
    assert scorecard["balanceBreaksDetected"] == 0
    assert scorecard["is100PercentTied"] is True
    assert abs(scorecard["tieVariance"]) < 1.0


# ============================================================================
# 11. EMPIRICAL CHALLENGER FINDING: PAST CUTOFF DATE 500 CRASH
# ============================================================================
def test_adv_past_cutoff_negative_days_fixed():
    """Verify past cutoff date handling after Milestone 4 defect fix:
    
    1. GET /api/v1/overview?as_of=2025-04-01 returns 200 OK without Pydantic ValidationError
    2. GET /api/v1/receivables?as_of=2025-04-01 returns 200 OK with oldestInvoiceDays >= 0
    
    Fix:
    In src/copilot/receivables.py:open_items(), the invoice set is filtered by
    `inv.invoice_date <= as_of_ts` and `days_open` is clipped at lower=0.
    """
    client_no_raise = TestClient(app, raise_server_exceptions=False)

    # 1. Overview endpoint succeeds with 200 on past cutoff
    res_ov = client_no_raise.get("/api/v1/overview?biz=SME-1&as_of=2025-04-01")
    assert res_ov.status_code == 200, (
        f"Expected 200 for past cutoff date 2025-04-01, got {res_ov.status_code}: {res_ov.text}"
    )
    ov_payload = OverviewPayload.model_validate(res_ov.json())
    assert ov_payload.business_id == "SME-1"

    # 2. Receivables endpoint succeeds with 200 on past cutoff
    res_rc = client_no_raise.get("/api/v1/receivables?biz=SME-1&as_of=2025-04-01")
    assert res_rc.status_code == 200, (
        f"Expected 200 for past cutoff date 2025-04-01, got {res_rc.status_code}: {res_rc.text}"
    )
    rc_payload = ReceivablesPayload.model_validate(res_rc.json())
    for cust in rc_payload.customers:
        assert cust.oldest_invoice_days >= 0

