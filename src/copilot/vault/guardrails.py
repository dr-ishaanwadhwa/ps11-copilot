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


@dataclass
class ComplianceResult:
    is_safe: bool
    status: Literal["SAFE", "WARNING", "BLOCKED"]
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


# Rule 237 / Rule 159 / Form 165: Annual Statement of Financial Transactions (SFT) cash deposit alerts
def check_sft_deposit_threshold(
    deposit_amount: float,
    current_ytd_cash: float,
    account_type: str = "CURRENT",
    has_pan: bool = True
) -> ComplianceResult:
    new_ytd = current_ytd_cash + deposit_amount
    limit = 5_000_000.0 if account_type == "CURRENT" else (1_000_000.0 if has_pan else 500_000.0)
    label = "Current Account (₹50 Lakh)" if account_type == "CURRENT" else ("Savings Account (₹10 Lakh)" if has_pan else "Savings Account without PAN (₹5 Lakh)")

    if new_ytd >= limit:
        return ComplianceResult(
            is_safe=False,
            status="WARNING",
            citation="Income-tax Rules, 2026 Rule 237 & Rule 159 (Form 165 SFT Reporting)",
            message=(
                f"This cash deposit of ₹{deposit_amount:,.0f} pushes your annual aggregate cash deposits to "
                f"₹{new_ytd:,.0f}, crossing the {label} SFT surveillance threshold. Your bank will report this "
                f"directly into your Annual Information Statement (AIS)."
            ),
            lawful_remedy=(
                "Ensure verifiable source records exist before banking (prior withdrawal slips, declared B2C cash sales, "
                "or formal partner capital). Unsubstantiated credits risk 30%–84% tax under Section 195/102."
            )
        )
    elif new_ytd >= limit * 0.80:
        headroom = limit - new_ytd
        return ComplianceResult(
            is_safe=True,
            status="WARNING",
            citation="Income-tax Rules, 2026 Rule 237 (Form 165)",
            message=(
                f"Annual cash deposits reach ₹{new_ytd:,.0f} (80% of the {label} SFT limit)."
            ),
            lawful_remedy="Keep daily counter cash reconciliation slips ready to substantiate sources."
        )
    return ComplianceResult(
        is_safe=True,
        status="SAFE",
        citation="Income-tax Rules, 2026 Rule 237",
        message=f"Annual cash deposits of ₹{new_ytd:,.0f} are within normal SFT parameters (Limit: ₹{limit:,.0f})."
    )


# Pre-deposit readiness audit for capital infusions (Prakash's ₹46L anomaly pattern)
def audit_capital_infusion(
    amount: float,
    has_prior_bank_withdrawal: bool = False,
    has_retail_collection_chits: bool = False,
    is_gift_from_relative: bool = False
) -> dict:
    """
    Evaluates whether a planned cash deposit meets documentation requirements.
    """
    score = 0
    substantiated_sources = []
    
    if has_prior_bank_withdrawal:
        score += 40
        substantiated_sources.append("Matched to prior bank cash withdrawal (Redeposit)")
    if has_retail_collection_chits:
        score += 35
        substantiated_sources.append("Supported by daily retail collection slips (Sales turnover)")
    if is_gift_from_relative:
        score += 25
        substantiated_sources.append("Section 56(2)(x) relative gift declaration")
        
    readiness = "HIGH" if score >= 70 else ("MEDIUM" if score >= 35 else "VULNERABLE")
    
    return {
        "amount": amount,
        "readiness_tier": readiness,
        "score_percent": score,
        "substantiated_sources": substantiated_sources,
        "risk_explanation": (
            "Unsubstantiated cash credits are subject to high tax rates under Section 195 "
            "(legacy Section 115BBE: 84% effective tax and penalty; Tax Year 2026-27: 30% base + "
            "surcharge/cess + up to 200% misreporting penalty)."
            if readiness == "VULNERABLE" else
            "Source documentation provides verifiable evidence to rebut Section 102 deemed income additions."
        ),
        "recommendation": (
            "Consult your CA before banking this cash to ensure books document the exact source."
            if readiness != "HIGH" else "Clear to bank with matching source trail."
        )
    }
