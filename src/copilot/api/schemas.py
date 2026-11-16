"""Pydantic Request & Response Schemas conforming strictly to SPEC-API-005.

Reference: docs/specs/05-api-contracts.md
Invariants:
- ADR-001 (Zero Plaintext Cash): No informal drawer cash in server request/response payloads.
- ADR-002 (Decision 60 Precision): Deterministic tier categories ('AUTO', 'SUGGEST', 'ASK', 'NO_DOC').
- ADR-003 (Limitation Act §18): 30+ months (>=900 days) alert flags.
- ADR-004 (MCA Rule 11(g) / BNS §241 & Split-Plane Firewall): Strict 5-sheet statutory exports.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# 1. Sovereign Vault Plane Types (ADR-001)
# ==========================================
class GallaEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    date: str
    opening_cash: float = Field(default=0.0, ge=0.0, alias="openingCash")
    cash_in: float = Field(default=0.0, ge=0.0, alias="cashIn")
    cash_out: float = Field(default=0.0, ge=0.0, alias="cashOut")
    cash_banked: float = Field(default=0.0, ge=0.0, alias="cashBanked")
    counted_cash: float = Field(default=0.0, ge=0.0, alias="countedCash")
    expected_cash: float = Field(default=0.0, ge=0.0, alias="expectedCash")
    drift: float = 0.0
    is_balanced: bool = Field(default=True, alias="isBalanced")
    notes: Optional[str] = None


class CollectionSlip(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    slip_id: str = Field(alias="slipId")
    date: str
    salesman: str
    shop_name: str = Field(alias="shopName")
    amount: float = Field(gt=0.0)
    payment_mode: Literal["CASH", "UPI", "CHEQUE"] = Field(alias="paymentMode")
    allocated_invoice_id: Optional[str] = Field(default=None, alias="allocatedInvoiceId")
    status: Literal["IN_TRANSIT", "IN_TILL", "BANKED"]


# ==========================================
# 2. Decision 60 Matching Types (ADR-002)
# ==========================================
MatchTier = Literal["AUTO", "SUGGEST", "ASK", "NO_DOC"]


class BankTransaction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    txn_id: str = Field(alias="txnId")
    date: str
    amount: float
    type: Literal["CREDIT", "DEBIT"]
    narration: str
    balance: float
    tier: MatchTier
    rule_applied: str = Field(alias="ruleApplied")
    candidate_payer: Optional[str] = Field(default=None, alias="candidatePayer")
    match_score: float = Field(default=0.0, ge=0.0, le=1.0, alias="matchScore")
    is_audited: bool = Field(default=False, alias="isAudited")
    verified_by_owner: bool = Field(default=False, alias="verifiedByOwner")


# ==========================================
# 3. Receivables & Section 18 Types (ADR-003)
# ==========================================
class CustomerReceivable(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer_id: str = Field(alias="customerId")
    customer_name: str = Field(alias="customerName")
    phone: str
    total_outstanding: float = Field(ge=0.0, alias="totalOutstanding")
    open_invoice_count: int = Field(ge=0, alias="openInvoiceCount")
    oldest_invoice_days: int = Field(ge=0, alias="oldestInvoiceDays")
    is_limitation_alert: bool = Field(alias="isLimitationAlert")  # Oldest >= 900 days (30+ months)
    has_salesman_collected_today: bool = Field(default=False, alias="hasSalesmanCollectedToday")
    recent_collection_note: Optional[str] = Field(default=None, alias="recentCollectionNote")
    salesman_name: Optional[str] = Field(default=None, alias="salesmanName")
    collected_today_amount: Optional[float] = Field(default=None, alias="collectedTodayAmount")
    collected_slip_id: Optional[str] = Field(default=None, alias="collectedSlipId")


# ==========================================
# 4. Cockpit Overview Types (View 1)
# ==========================================
class VitalPulseMetric(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    label: str
    amount: float
    tone: Literal["positive", "warning", "neutral", "critical"]
    subtitle: Optional[str] = None


class SolvencyEquation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    formal_bank_balance: float = Field(alias="formalBankBalance")
    cc_facility_drawn: float = Field(alias="ccFacilityDrawn")
    cc_facility_sanctioned: float = Field(alias="ccFacilitySanctioned")
    formal_due_next_30_days: float = Field(alias="formalDueNext30Days")
    formal_receivables: float = Field(alias="formalReceivables")
    default_khata_realization_rate: float = Field(
        default=0.85, ge=0.0, le=1.0, alias="defaultKhataRealizationRate"
    )


class OverviewPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    business_id: str = Field(alias="businessId")
    business_name: str = Field(alias="businessName")
    as_of_date: str = Field(alias="asOfDate")
    bank_current_balance: float = Field(alias="bankCurrentBalance")
    cc_sanctioned_limit: float = Field(alias="ccSanctionedLimit")
    cc_headroom: float = Field(alias="ccHeadroom")
    runway_months: float = Field(alias="runwayMonths")
    pulse_metrics: List[VitalPulseMetric] = Field(alias="pulseMetrics")
    top_focal_action: Optional[CustomerReceivable] = Field(default=None, alias="topFocalAction")
    solvency_base: SolvencyEquation = Field(alias="solvencyBase")
    audio_brief_url: str = Field(default="", alias="audioBriefUrl")


# ==========================================
# 5. 90-Day Forecast & Simulation Types (View 3)
# ==========================================
class MilestoneEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    amount: float
    category: Literal["SALARY", "GST_TAX", "ADVANCE_TAX", "VENDOR_DUE", "CUSTOMER_RECEIPT"]


class ForecastSimulationPoint(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    day_index: int = Field(ge=0, le=90, alias="dayIndex")
    date: str
    p10_worst_case: float = Field(alias="p10WorstCase")
    p50_median: float = Field(alias="p50Median")
    p90_optimistic: float = Field(alias="p90Optimistic")
    cc_facility_limit: float = Field(alias="ccFacilityLimit")
    milestone_event: Optional[MilestoneEvent] = Field(default=None, alias="milestoneEvent")


class MonthlyOutlookItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    month_name: str = Field(alias="monthName")
    inflows_p50: float = Field(alias="inflowsP50")
    inflows_p10: float = Field(alias="inflowsP10")
    committed_outflows: float = Field(alias="committedOutflows")
    net_cash_flow: float = Field(alias="netCashFlow")
    lowest_dip_point: float = Field(alias="lowestDipPoint")
    closing_balance: float = Field(alias="closingBalance")
    has_breached_credit_limit: bool = Field(alias="hasBreachedCreditLimit")


class StressTestParameters(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer_delay_days: int = Field(default=0, ge=0, le=60, alias="customerDelayDays")
    raw_material_expense_surge: float = Field(
        default=0.0, ge=0.0, alias="rawMaterialExpenseSurge"
    )
    collection_realization_alpha: float = Field(
        default=0.85, ge=0.5, le=1.0, alias="collectionRealizationAlpha"
    )


class TopCollectionAction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer_name: str = Field(alias="customerName")
    outstanding: float
    oldest_invoice_days: int = Field(alias="oldestInvoiceDays")


class PlainSummary(BaseModel):
    """Plain-English reading of a forecast run (no statistical jargon)."""

    model_config = ConfigDict(populate_by_name=True)

    lowest_balance: float = Field(alias="lowestBalance")
    lowest_date: str = Field(alias="lowestDate")
    worst_case_lowest_balance: float = Field(alias="worstCaseLowestBalance")
    credit_limit: float = Field(alias="creditLimit")
    breaches_credit_limit: bool = Field(alias="breachesCreditLimit")
    scenario_active: bool = Field(alias="scenarioActive")
    baseline_lowest_balance: Optional[float] = Field(default=None, alias="baselineLowestBalance")
    top_collection_action: Optional[TopCollectionAction] = Field(default=None, alias="topCollectionAction")
    headline: str
    detail: str


class ForecastPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    business_id: str = Field(alias="businessId")
    as_of_date: str = Field(alias="asOfDate")
    holdout_mape_score: float = Field(alias="holdoutMapeScore")
    holdout_coverage_rate: float = Field(alias="holdoutCoverageRate")
    holdout_mape_measured: Optional[float] = Field(default=None, alias="holdoutMapeMeasured")
    holdout_coverage_measured: Optional[float] = Field(default=None, alias="holdoutCoverageMeasured")
    lowest_projected_balance: float = Field(alias="lowestProjectedBalance")
    lowest_projected_date: str = Field(alias="lowestProjectedDate")
    simulation_points: List[ForecastSimulationPoint] = Field(alias="simulationPoints")
    monthly_matrix: List[MonthlyOutlookItem] = Field(alias="monthlyMatrix")
    plain_summary: Optional[PlainSummary] = Field(default=None, alias="plainSummary")


# ==========================================
# 6. Review Queue & Reconcile Types (View 4)
# ==========================================
class ReviewQueuePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    business_id: str = Field(alias="businessId")
    total_count: int = Field(alias="totalCount")
    counts_by_tier: Dict[str, int] = Field(alias="countsByTier")
    items: List[BankTransaction]


class ReconcileRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    txn_id: str = Field(alias="txnId")
    decision: Literal["APPROVE", "REJECT", "REASSIGN"]
    assigned_party_id: Optional[str] = Field(default=None, alias="assignedPartyId")
    note: Optional[str] = None


class ReconcileResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    txn_id: str = Field(alias="txnId")
    new_status: str = Field(alias="newStatus")
    audit_hash: str = Field(alias="auditHash")


# ==========================================
# 7. Receivables Payload Types (View 5)
# ==========================================
class ReceivablesPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    business_id: str = Field(alias="businessId")
    total_outstanding: float = Field(alias="totalOutstanding")
    overdue_count: int = Field(alias="overdueCount")
    limitation_alert_count: int = Field(alias="limitationAlertCount")
    customers: List[CustomerReceivable]


# ==========================================
# 8. Conversational Copilot Stream Types (View 6)
# ==========================================
class CitationItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    source: str
    amount: float
    date: Optional[str] = None
    deep_link: Optional[str] = Field(default=None, alias="deepLink")
    badge: Optional[Literal["BANK_FORMAL", "GST_INVOICE", "RAM_ONLY"]] = None


class CopilotStreamRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question: str
    business_id: str = Field(default="SME-1", alias="businessId")
    as_of_date: Optional[str] = Field(default=None, alias="asOfDate")


# ==========================================
# 9. Statutory & Diagnostic Export Types (View 7)
# ==========================================
class TallyExportRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    business_id: str = Field(alias="businessId")
    as_of_date: str = Field(alias="asOfDate")
    voucher_type: Literal["Receipt"] = Field(default="Receipt", alias="voucherType")
    include_auto_only: bool = Field(default=True, alias="includeAutoOnly")


class CaExcelExportRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    business_id: str = Field(alias="businessId")
    as_of_date: str = Field(alias="asOfDate")
    format: Literal["STATUTORY_5_SHEET"] = Field(default="STATUTORY_5_SHEET")
    omit_informal_cash: Literal[True] = Field(default=True, alias="omitInformalCash")


class InternalManagementExportRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    business_id: str = Field(alias="businessId")
    as_of_date: str = Field(alias="asOfDate")
    format: Literal["INTERNAL_DUAL_PLANE_6_SHEET"] = Field(
        default="INTERNAL_DUAL_PLANE_6_SHEET"
    )
    # The server checks the PIN itself. ownerPinAuthenticated is kept only so old clients get a
    # clear 403 instead of a validation error; on its own it no longer grants access.
    owner_pin: Optional[str] = Field(default=None, alias="ownerPin", min_length=1, max_length=64)
    owner_pin_authenticated: bool = Field(default=False, alias="ownerPinAuthenticated")


class DataIntegrityScorecard(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_bank_lines_ingested: int = Field(alias="totalBankLinesIngested")
    months_audited: int = Field(alias="monthsAudited")
    balance_breaks_detected: int = Field(alias="balanceBreaksDetected")
    opening_bank_balance: float = Field(alias="openingBankBalance")
    total_bank_credits: float = Field(alias="totalBankCredits")
    total_bank_debits: float = Field(alias="totalBankDebits")
    closing_bank_balance: float = Field(alias="closingBankBalance")
    is_100_percent_tied: bool = Field(alias="is100PercentTied")
    tie_variance: float = Field(alias="tieVariance")


class ExportPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tally_vouchers_available: int = Field(alias="tallyVouchersAvailable")
    tally_total_credit_amount: float = Field(alias="tallyTotalCreditAmount")
    ca_workbook_sheet_count: Literal[5] = Field(default=5, alias="caWorkbookSheetCount")
    integrity_scorecard: DataIntegrityScorecard = Field(alias="integrityScorecard")
