"""Decision 60 Review Queue & Reconciliation Router (`/api/v1/review`).

Wraps `match_all()`, `Matcher`, and `AuditLedger` in `src/copilot/match/`.
Preserves ADR-002 (Decision 60 Precision) and ADR-004 (MCA Rule 11(g) / BNS §241 Immutability).
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
import pandas as pd

from ...load import Pack
from ...match.engine import Matcher
from ...match.audit import AuditLedger
from ..deps import get_audit_ledger, get_pack
from ..schemas import (
    BankTransaction,
    MatchTier,
    ReconcileRequest,
    ReconcileResponse,
    ReviewQueuePayload,
)

router = APIRouter(prefix="/review", tags=["review"])


@router.get("", response_model=ReviewQueuePayload, response_model_by_alias=True)
def get_review_queue(
    biz: str = Query(default="SME-1", description="Business ID (SME-1, SME-2, SME-3)"),
    tier: Optional[str] = Query(default=None, description="Optional tier filter (AUTO, SUGGEST, ASK, NO_DOC)"),
    pack: Pack = Depends(get_pack),
    ledger: AuditLedger = Depends(get_audit_ledger),
) -> ReviewQueuePayload:
    from ...match.engine import match_all

    all_matches = match_all(pack, audit_ledger=ledger)
    biz_bank = pack.bank[pack.bank.business_id == biz].set_index("txn_id")

    counts: dict[str, int] = {"AUTO": 0, "SUGGEST": 0, "ASK": 0, "NO_DOC": 0}
    items: list[BankTransaction] = []

    for txn_id, m in all_matches.items():
        if m.business_id != biz:
            continue
        m_tier = m.tier if m.tier in ("AUTO", "SUGGEST", "ASK", "NO_DOC") else "ASK"
        counts[m_tier] = counts.get(m_tier, 0) + 1

        if tier and tier.upper() != "ALL" and m_tier != tier.upper():
            continue

        if txn_id not in biz_bank.index:
            continue
        row = biz_bank.loc[txn_id]

        txn_type = "CREDIT" if getattr(row, "credit_inr", 0.0) > 0 else "DEBIT"
        txn_amt = float(getattr(row, "amount", 0.0))
        txn_bal = float(getattr(row, "balance_inr", 0.0))
        txn_date_val = getattr(row, "txn_date", None)
        txn_date_str = txn_date_val.strftime("%Y-%m-%d") if hasattr(txn_date_val, "strftime") else str(txn_date_val or "")

        candidate_payer = m.payer or (str(m.docs[0][0]) if m.docs else str(getattr(row, "narration", "")))

        items.append(
            BankTransaction(
                txnId=m.txn_id,
                date=txn_date_str,
                amount=txn_amt,
                type=txn_type,
                narration=str(getattr(row, "narration", "")),
                balance=txn_bal,
                tier=m_tier,
                ruleApplied=m.rule or "DEFAULT",
                candidatePayer=candidate_payer,
                matchScore=float(getattr(m, "score", 1.0 if m_tier == "AUTO" else 0.8)),
                isAudited=False,
                verifiedByOwner=False,
            )
        )

    total_count = sum(counts.values())

    return ReviewQueuePayload(
        businessId=biz,
        totalCount=total_count,
        countsByTier=counts,
        items=items,
    )


@router.post("/reconcile", response_model=ReconcileResponse, response_model_by_alias=True)
def reconcile_match(
    req: ReconcileRequest,
    ledger: AuditLedger = Depends(get_audit_ledger),
) -> ReconcileResponse:
    now_iso = datetime.now(timezone.utc).isoformat()
    raw_signature = f"{req.txn_id}:{req.decision}:{now_iso}:{req.assigned_party_id or ''}:{req.note or ''}"
    audit_hash = hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()

    # Record verification in immutable audit ledger (MCA Rule 11(g))
    is_correct = (req.decision == "APPROVE")
    ledger.record(
        txn_id=req.txn_id,
        rule_class=("SME-1", "MANUAL_RECONCILE"),
        correct=is_correct,
        reviewer="owner",
        at=now_iso,
    )

    new_status = "APPROVED" if req.decision == "APPROVE" else ("REJECTED" if req.decision == "REJECT" else "REASSIGNED")

    return ReconcileResponse(
        success=True,
        txnId=req.txn_id,
        newStatus=new_status,
        auditHash=audit_hash,
    )
