"""Conversational Copilot Streaming Router (`/api/v1/copilot/stream`).

Provides Server-Sent Events (SSE) token stream conforming to SPEC-API-005.
Preserves ADR-001 (Zero Plaintext Cash): Cloud/BFF never receives or transmits
plaintext counter cash numbers. Emits `template_token` chunks (e.g. `{{LOCAL_VAULT_GALLA_CASH}}`)
for browser-side RAM hydration.
"""
from __future__ import annotations

import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import pandas as pd

from ...answers import Copilot
from ...load import Pack
from ..deps import get_pack, parse_as_of_date
from ..schemas import CitationItem, CopilotStreamRequest

router = APIRouter(prefix="/copilot", tags=["copilot"])


async def _generate_copilot_stream(
    req: CopilotStreamRequest, pack: Pack
) -> AsyncGenerator[str, None]:
    as_of_dt = parse_as_of_date(req.as_of_date)
    biz = req.business_id
    q_lower = req.question.lower()

    # 1. Tool execution event
    yield f"data: {json.dumps({'type': 'tool_start', 'toolName': 'ledger_and_solvency_lookup'})}\n\n"

    # Compute formal figures
    copilot_engine = Copilot(pack)
    bank_bal, last_txn_id = copilot_engine.closing_balance(biz, as_of_dt)
    credit_limit = copilot_engine.credit_limit(biz)
    total_spendable = bank_bal + credit_limit

    yield f"data: {json.dumps({'type': 'tool_done', 'toolName': 'ledger_and_solvency_lookup', 'result': f'Bank Balance: ₹{bank_bal:,.2f}, Sanctioned CC Limit: ₹{credit_limit:,.2f}'})}\n\n"

    # 2. Answer generation logic
    citations: list[CitationItem] = []

    if "salar" in q_lower or "pay" in q_lower:
        month = (as_of_dt - pd.offsets.MonthBegin(1)).strftime("%Y-%m") if hasattr(as_of_dt, "month") else "2026-09"
        salary_amt, sal_txns = copilot_engine.salary_run(biz, month)

        intro = (
            f"Based on your formal bank ledger as of {as_of_dt.strftime('%d %b %Y')}, "
            f"your closing bank balance is ₹{bank_bal:,.0f}"
            + (f" with ₹{total_spendable:,.0f} total usable liquidity including CC headroom." if credit_limit else ".")
            + f" Prior month salary obligations were ₹{salary_amt:,.0f}. "
            f"Taking into account your physical counter till cash of "
        )
        for word in intro.split(" "):
            yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"

        # Emit ADR-001 template token (Preserving zero plaintext vault cash leakage)
        yield f"data: {json.dumps({'type': 'template_token', 'token': '{{LOCAL_VAULT_GALLA_CASH}}', 'field': 'gallaCash'})}\n\n"

        conclusion = (
            ", your True Solvency runway indicates you have sufficient spendable cash buffer to disburse salaries comfortably on schedule."
            if total_spendable >= salary_amt
            else ", note that your bank balance alone requires tight collection monitoring before salary day."
        )
        for word in conclusion.split(" "):
            yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"

        citations.append(
            CitationItem(
                id="CIT-BANK-01",
                source="Bank Statement Current A/c",
                amount=bank_bal,
                date=as_of_dt.strftime("%Y-%m-%d"),
                badge="BANK_FORMAL",
            )
        )
        if sal_txns:
            citations.append(
                CitationItem(
                    id="CIT-SAL-01",
                    source=f"Salary Payroll Run ({len(sal_txns)} transactions)",
                    amount=salary_amt,
                    date=as_of_dt.strftime("%Y-%m-%d"),
                    badge="BANK_FORMAL",
                )
            )

    elif "owe" in q_lower or "customer" in q_lower or "chase" in q_lower:
        ans = copilot_engine.who_owes_most(biz)
        for word in ans.text.split(" "):
            yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"

        citations.append(
            CitationItem(
                id="CIT-REC-01",
                source=f"Open Sales Invoices ({len(ans.sources)} invoices)",
                amount=float(ans.numbers.get("outstanding", 0.0)),
                badge="GST_INVOICE",
            )
        )

    else:
        general_reply = (
            f"As of {as_of_dt.strftime('%d %b %Y')}, your formal bank liquidity stands at ₹{bank_bal:,.0f}"
            + (f" with ₹{credit_limit:,.0f} sanctioned cash-credit limit." if credit_limit else ".")
            + " Accounting for your sovereign vault drawer cash of "
        )
        for word in general_reply.split(" "):
            yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"

        # Emit ADR-001 template token
        yield f"data: {json.dumps({'type': 'template_token', 'token': '{{LOCAL_VAULT_GALLA_CASH}}', 'field': 'gallaCash'})}\n\n"

        trailer = ", all operational accounts and formal commitments remain actively balanced."
        for word in trailer.split(" "):
            yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"

        citations.append(
            CitationItem(
                id="CIT-BANK-01",
                source="Bank Current A/c Ledger",
                amount=bank_bal,
                date=as_of_dt.strftime("%Y-%m-%d"),
                badge="BANK_FORMAL",
            )
        )

    # 3. Emit Citations
    for cit in citations:
        yield f"data: {json.dumps({'type': 'citation', 'citation': cit.model_dump(by_alias=True)})}\n\n"

    # 4. Done event
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/stream")
async def stream_copilot_chat(
    req: CopilotStreamRequest,
    pack: Pack = Depends(get_pack),
) -> StreamingResponse:
    return StreamingResponse(
        _generate_copilot_stream(req, pack),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
