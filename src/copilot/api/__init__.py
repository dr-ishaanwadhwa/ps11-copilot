"""FastAPI Headless Microservice for SME Cash-Flow Copilot.

Provides clean, typed REST and SSE streaming endpoints for:
- Overview Cockpit metrics & solvency equation (ADR-001)
- 90-day cash forecast & simulation points (ADR-002)
- Review queue triage & deterministic D60 reconciliation (ADR-002, ADR-004)
- Receivables aging, 45-day MSMED alerts & Section 18 Limitation Act tripwires (ADR-003)
- Grounded Copilot assistant with SSE stream & template tokens (ADR-001)
- Statutory Tally Prime XML & CA 5-sheet Excel workbook export (ADR-004)
"""
from .app import app

__all__ = ["app"]
