"""Statutory & Diagnostic Exports Router (`/api/v1/exports`).

Provides:
- `POST /api/v1/exports/tally-xml`: Pure TDL XML receipt vouchers for TallyPrime.
- `POST /api/v1/exports/ca-excel`: Strict 5-sheet statutory reconciliation pack (ADR-004).
- `POST /api/v1/exports/internal-diagnostic-excel`: PIN-gated 6-sheet dual-plane management pack.
- `GET /api/v1/exports/summary`: Integrity scorecard and export metrics.
"""
from __future__ import annotations

import hmac
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
import pandas as pd

from ...load import Pack
from ...match.engine import Matcher
from ...vault.crypto import VaultCrypto
from ...tally import (
    generate_ca_excel_pack,
    generate_statutory_ca_excel_pack,
    generate_tally_xml,
)
from ..deps import get_pack, parse_as_of_date
from ..schemas import (
    CaExcelExportRequest,
    DataIntegrityScorecard,
    ExportPayload,
    InternalManagementExportRequest,
    TallyExportRequest,
)

router = APIRouter(tags=["exports"])


@router.post("/tally-xml")
def export_tally_xml(
    req: TallyExportRequest,
    pack: Pack = Depends(get_pack),
) -> Response:
    matcher = Matcher(pack)
    sme_bank = pack.bank[pack.bank.business_id == req.business_id].sort_values(["txn_date", "seq"])
    matches = [matcher.match(r) for r in sme_bank.itertuples()]

    xml_content = generate_tally_xml(pack, matches, req.business_id)

    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="tally_receipts_{req.business_id}_{req.as_of_date}.xml"'
        },
    )


@router.post("/ca-excel")
def export_ca_excel(
    req: CaExcelExportRequest,
    pack: Pack = Depends(get_pack),
) -> Response:
    """Export strict 5-sheet statutory reconciliation workbook under ADR-004.
    Sheet 6 (Salesman_Collection_Slips) and Block D (till cash cross-checks) are strictly omitted.
    """
    matcher = Matcher(pack)
    sme_bank = pack.bank[pack.bank.business_id == req.business_id].sort_values(["txn_date", "seq"])
    matches = [matcher.match(r) for r in sme_bank.itertuples()]

    # Strictly pass vault=None and statutory_5_sheet=True to enforce split-plane firewall
    excel_bytes = generate_statutory_ca_excel_pack(pack, matches, None, req.business_id)

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="ca_reconciliation_statutory_{req.business_id}_{req.as_of_date}.xlsx"'
        },
    )


@router.post("/internal-diagnostic-excel")
def export_internal_diagnostic_excel(
    req: InternalManagementExportRequest,
    pack: Pack = Depends(get_pack),
) -> Response:
    """Export PIN-gated 6-sheet dual-plane internal management diagnostic workbook."""
    # Verified here, not taken on the caller's word: a client-sent "authenticated: true" proves nothing.
    pin_ok = bool(req.owner_pin) and hmac.compare_digest(
        req.owner_pin.encode(), VaultCrypto.get_configured_pin().encode()
    )
    if not pin_ok:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Sovereign internal management exports require owner PIN authentication.",
        )

    matcher = Matcher(pack)
    sme_bank = pack.bank[pack.bank.business_id == req.business_id].sort_values(["txn_date", "seq"])
    matches = [matcher.match(r) for r in sme_bank.itertuples()]

    # Generate standard 6-sheet pack
    excel_bytes = generate_ca_excel_pack(
        pack, matches, None, req.business_id, statutory_5_sheet=False
    )

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="internal_management_dual_plane_{req.business_id}_{req.as_of_date}.xlsx"'
        },
    )


@router.get("/summary", response_model=ExportPayload, response_model_by_alias=True)
def get_exports_summary(
    biz: str = Query(default="SME-1", description="Business ID (SME-1, SME-2, SME-3)"),
    as_of: Optional[str] = Query(default=None, description="As-of cutoff date (YYYY-MM-DD)"),
    pack: Pack = Depends(get_pack),
) -> ExportPayload:
    as_of_dt = parse_as_of_date(as_of)
    matcher = Matcher(pack)
    sme_bank = pack.bank[(pack.bank.business_id == biz) & (pack.bank.txn_date <= as_of_dt)].sort_values(
        ["txn_date", "seq"]
    )
    matches = [matcher.match(r) for r in sme_bank.itertuples()]

    auto_matches = [m for m in matches if getattr(m, "tier", "") in ("AUTO", "CONFIRMED")]
    auto_count = len(auto_matches)

    bank_by_id = {r.txn_id: r for r in sme_bank.itertuples()}
    tally_total_credit = sum(
        float(getattr(bank_by_id[m.txn_id], "credit_inr", 0.0) or getattr(bank_by_id[m.txn_id], "amount", 0.0))
        for m in auto_matches
        if m.txn_id in bank_by_id
    )

    opening_bal = 0.0
    if pack.businesses is not None:
        b_df = pack.businesses[pack.businesses["business_id"] == biz]
        if not b_df.empty:
            opening_bal = float(b_df["opening_balance_1apr2025"].iloc[0])

    tot_credits = float(sme_bank["credit_inr"].sum()) if not sme_bank.empty else 0.0
    tot_debits = float(sme_bank["debit_inr"].sum()) if not sme_bank.empty else 0.0
    comp_closing = opening_bal + tot_credits - tot_debits
    act_closing = float(sme_bank.iloc[-1]["balance_inr"]) if not sme_bank.empty else comp_closing
    var = round(comp_closing - act_closing, 2)

    scorecard = DataIntegrityScorecard(
        totalBankLinesIngested=len(sme_bank),
        monthsAudited=18,
        balanceBreaksDetected=0 if abs(var) < 1.0 else 1,
        openingBankBalance=round(opening_bal, 2),
        totalBankCredits=round(tot_credits, 2),
        totalBankDebits=round(tot_debits, 2),
        closingBankBalance=round(act_closing, 2),
        is100PercentTied=bool(abs(var) < 1.0),
        tieVariance=var,
    )

    return ExportPayload(
        tallyVouchersAvailable=auto_count,
        tallyTotalCreditAmount=round(tally_total_credit, 2),
        caWorkbookSheetCount=5,
        integrityScorecard=scorecard,
    )
