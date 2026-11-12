"""Statutory check matrix and compliance guardrails for SME cash transactions.

Updated as of November 2026:
- Income-tax Act, 2025 & Income-tax Rules, 2026 (effective 1 April 2026).
- Rule 237 / Rule 159 / Form 165 SFT Reporting.
- Section 186 (old 269ST) single-receipt cash limit.
- Section 36(4) (old 40A(3)) cash expense limits.
- Section 185 & 188 (old 269SS & 269T) cash loan/deposit limits.
- Section 102-107 & 195 (old 68-69D & 115BBE) deemed income additions.

Guiding principle: Fact-only deterministic calculations. The copilot NEVER
recommends tax evasion, invoice splitting, or illegal structuring.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..fmt import inr


@dataclass
class ComplianceResult:
    is_safe: bool
    status: Literal["SAFE", "WARNING", "BLOCKED", "INFO"]
    citation: str
    message: str
    lawful_remedy: str = ""


# Section 186 (old 269ST): Cash receipts >= ₹2 Lakh from a person in a day / single transaction
def check_single_receipt_cash(amount: float, party_name: str = "") -> ComplianceResult:
    if amount >= 200_000.0:
        return ComplianceResult(
            is_safe=False,
            status="BLOCKED",
            citation="Income-tax Act, 2025 Sec 186 (formerly Sec 269ST)",
            message=(
                f"Receipt of ₹{amount:,.0f} in cash from {party_name or 'a customer'} exceeds the statutory "
                f"ceiling of ₹2,00,000. Under Section 451, a penalty of 100% of the cash received applies to the receiver."
            ),
            lawful_remedy=(
                "Accept payment via formal digital banking (IMPS/NEFT/RTGS/UPI) or account-payee cheque. "
                "Splitting the bill into multiple smaller cash receipts is illegal structuring."
            ),
        )
    return ComplianceResult(
        is_safe=True,
        status="SAFE",
        citation="Income-tax Act, 2025 Sec 186",
        message=f"Cash receipt of ₹{amount:,.0f} is within the daily ₹2,00,000 single-party limit."
    )


# Section 36(4)–(6) (old 40A(3)): Business cash expense > ₹10,000 / day / person (> ₹35,000 for transport)
def check_cash_expense(amount: float, is_transport: bool = False, party_name: str = "") -> ComplianceResult:
    threshold = 35_000.0 if is_transport else 10_000.0
    limit_label = "₹35,000 for goods transport" if is_transport else "₹10,000"

    if amount > threshold:
        return ComplianceResult(
            is_safe=False,
            status="WARNING",
            citation="Income-tax Act, 2025 Sec 36(4)–(6) (formerly Sec 40A(3))",
            message=(
                f"Cash payment of ₹{amount:,.0f} to {party_name or 'payee'} exceeds the daily ceiling of {limit_label}. "
                f"100% of this expense will be disallowed as a deductible business expense in your tax audit."
            ),
            lawful_remedy="Settle via bank transfer (UPI, NEFT, Net Banking) to preserve full business expense deduction."
        )
    return ComplianceResult(
        is_safe=True,
        status="SAFE",
        citation="Income-tax Act, 2025 Sec 36(4)",
        message=f"Cash expense of ₹{amount:,.0f} is within the allowable {limit_label} threshold."
    )


# Section 185 & 188 (old 269SS & 269T): Cash loans/deposits >= ₹20,000
def check_cash_loan(amount: float, direction: str = "BORROW") -> ComplianceResult:
    if amount >= 20_000.0:
        action = "accepting" if direction == "BORROW" else "repaying"
        citation = "Sec 185 (old 269SS)" if direction == "BORROW" else "Sec 188 (old 269T)"
        penalty_sec = "Sec 450 (old 271D)" if direction == "BORROW" else "Sec 453 (old 271E)"
        return ComplianceResult(
            is_safe=False,
            status="BLOCKED",
            citation=f"Income-tax Act, 2025 {citation}",
            message=(
                f"{action.capitalize()} a loan or deposit of ₹{amount:,.0f} in cash violates {citation}. "
                f"Under {penalty_sec}, a mandatory 100% penalty applies equal to the loan amount."
            ),
            lawful_remedy="Route all business borrowing or repayments strictly through account-payee banking channels."
        )
    return ComplianceResult(
        is_safe=True,
        status="SAFE",
        citation="Income-tax Act, 2025 Sec 185/188",
        message=f"Amount of ₹{amount:,.0f} is within the ₹20,000 informal loan limit."
    )


# Rule 237: Annual Statement of Financial Transactions (SFT) cash deposit facts (D68)
def cash_deposit_reporting_facts(
    ytd_cash_deposits: float,
    account_type: str = "CURRENT",
    has_pan: bool = True
) -> ComplianceResult:
    """Facts about bank reporting of cash deposits. No countdown, no remaining amount, no advice."""
    msg = (
        f"Cash deposited this financial year: {inr(ytd_cash_deposits)}. "
        "Banks report yearly cash deposits of ₹10 lakh or more in savings accounts "
        "(₹5 lakh without PAN) and ₹50 lakh or more in current accounts to the tax department. "
        "Keep records of where deposited cash came from. Your CA can advise."
    )
    return ComplianceResult(
        is_safe=True,
        status="INFO",
        citation="Income-tax Rules 2026, Rule 237 (to be confirmed by a CA)",
        message=msg,
        lawful_remedy="",
    )


def deposit_records_checklist() -> dict:
    """Documents worth keeping before depositing cash. Facts plus a CA referral; no score."""
    return {
        "documents": [
            "Bank withdrawal slips, if this cash was withdrawn earlier",
            "Daily sales records or cash memos for the takings being deposited",
            "The day-close cash count for each day the cash came from",
        ],
        "referral": "Show these to your CA before depositing large amounts.",
    }
