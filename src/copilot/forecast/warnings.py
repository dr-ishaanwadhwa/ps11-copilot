"""Shortfall warning triggers and 2-3 swing items selection (FR-FC-2; D40, D43, D50, ADR 0002).

Implements:
- Three warning triggers:
  1. Credit limit headroom (default ₹2.5L floor for distributor)
  2. Salary day run (projected balance on 1st vs required payroll)
  3. Owner floor (minimum committed liquidity floor)
- Two warning levels:
  - LIKELY: P50 path crosses
  - POSSIBLE: only P10 path crosses
- Naming 2-3 swing items (receipts late to P90, scheduled outflows)
- Zero advice verbs (strictly facts; taxes never marked movable)
"""
import pandas as pd
from ..fmt import inr
from .models import SwingItem, WarningCard, DailyPoint


# Prohibited advice verbs per boundary suite and Section 6
PROHIBITED_ADVICE = ["delay", "borrow", "take loan", "stretch supplier", "skip gst", "don't pay"]


def evaluate_warnings(
    daily_points: list[DailyPoint],
    candidate_swings: list[SwingItem],
    salary_amount: float,
    salary_dates: list[pd.Timestamp],
    credit_limit: float = 0.0,
    credit_headroom_floor: float = 250_000.0,
    owner_floor: float = 0.0,
) -> list[WarningCard]:
    """Evaluate the 3 triggers across the daily forecast path and build warning cards."""
    warnings: list[WarningCard] = []

    # ── Trigger 1: Credit Limit Headroom (SME-1 distributor) ──────────────────────────
    if credit_limit > 0:
        likely_p = next((p for p in daily_points if (credit_limit + p.balance_p50) < credit_headroom_floor), None)
        if likely_p is not None:
            swings = _select_top_swings(candidate_swings, likely_p.date)
            msg = _format_warning_message(
                trigger_title="Credit limit",
                date=likely_p.date,
                val_str=f"headroom is projected at {inr(credit_limit + likely_p.balance_p50)}",
                floor_str=inr(credit_headroom_floor),
                swings=swings,
            )
            warnings.append(
                WarningCard(
                    trigger_type="CREDIT_LIMIT",
                    trigger_name="Credit limit headroom",
                    level="LIKELY",
                    warning_date=likely_p.date,
                    projected_value=credit_limit + likely_p.balance_p50,
                    threshold=credit_headroom_floor,
                    swing_items=swings,
                    message=msg,
                )
            )
        else:
            possible_p = next((p for p in daily_points if (credit_limit + p.balance_p10) < credit_headroom_floor), None)
            if possible_p is not None:
                swings = _select_top_swings(candidate_swings, possible_p.date)
                msg = _format_warning_message(
                    trigger_title="Credit limit",
                    date=possible_p.date,
                    val_str=f"headroom is projected at {inr(credit_limit + possible_p.balance_p10)}",
                    floor_str=inr(credit_headroom_floor),
                    swings=swings,
                )
                warnings.append(
                    WarningCard(
                        trigger_type="CREDIT_LIMIT",
                        trigger_name="Credit limit headroom",
                        level="POSSIBLE",
                        warning_date=possible_p.date,
                        projected_value=credit_limit + possible_p.balance_p10,
                        threshold=credit_headroom_floor,
                        swing_items=swings,
                        message=msg,
                    )
                )

    # ── Trigger 2: Salary Day Run (Every business) ────────────────────────────────────
    for sal_date in salary_dates:
        matching = [p for p in daily_points if p.date.date() == sal_date.date()]
        if not matching:
            continue
        p = matching[0]
        # At salary date, check if balance covers salary run
        is_likely = p.balance_p50 < salary_amount
        is_possible = p.balance_p10 < salary_amount

        if is_likely or is_possible:
            level = "LIKELY" if is_likely else "POSSIBLE"
            swings = _select_top_swings(candidate_swings, p.date)
            msg = _format_warning_message(
                trigger_title="Salary day",
                date=p.date,
                val_str=f"projected balance is {inr(p.balance_p50 if is_likely else p.balance_p10)}",
                floor_str=f"salary run of {inr(salary_amount)}",
                swings=swings,
            )
            warnings.append(
                WarningCard(
                    trigger_type="SALARY_DAY",
                    trigger_name="Salary day run",
                    level=level,
                    warning_date=p.date,
                    projected_value=p.balance_p50 if is_likely else p.balance_p10,
                    threshold=salary_amount,
                    swing_items=swings,
                    message=msg,
                )
            )

    # ── Trigger 3: Owner Floor ────────────────────────────────────────────────────────
    if owner_floor > 0:
        likely_p = next((p for p in daily_points if p.balance_p50 < owner_floor), None)
        if likely_p is not None:
            swings = _select_top_swings(candidate_swings, likely_p.date)
            msg = _format_warning_message(
                trigger_title="Owner floor",
                date=likely_p.date,
                val_str=f"projected balance is {inr(likely_p.balance_p50)}",
                floor_str=inr(owner_floor),
                swings=swings,
            )
            warnings.append(
                WarningCard(
                    trigger_type="OWNER_FLOOR",
                    trigger_name="Owner minimum floor",
                    level="LIKELY",
                    warning_date=likely_p.date,
                    projected_value=likely_p.balance_p50,
                    threshold=owner_floor,
                    swing_items=swings,
                    message=msg,
                )
            )
        else:
            possible_p = next((p for p in daily_points if p.balance_p10 < owner_floor), None)
            if possible_p is not None:
                swings = _select_top_swings(candidate_swings, possible_p.date)
                msg = _format_warning_message(
                    trigger_title="Owner floor",
                    date=possible_p.date,
                    val_str=f"projected balance is {inr(possible_p.balance_p10)}",
                    floor_str=inr(owner_floor),
                    swings=swings,
                )
                warnings.append(
                    WarningCard(
                        trigger_type="OWNER_FLOOR",
                        trigger_name="Owner minimum floor",
                        level="POSSIBLE",
                        warning_date=possible_p.date,
                        projected_value=possible_p.balance_p10,
                        threshold=owner_floor,
                        swing_items=swings,
                        message=msg,
                    )
                )

    return warnings


def _select_top_swings(
    candidate_swings: list[SwingItem], target_date: pd.Timestamp, max_items: int = 3
) -> list[SwingItem]:
    """Select the 2-3 items between today and target date with largest swing impact (D40)."""
    relevant = [s for s in candidate_swings if s.date <= target_date]
    if not relevant:
        return []
    sorted_items = sorted(relevant, key=lambda s: abs(s.swing_amount), reverse=True)
    return sorted_items[:max_items]


def _format_warning_message(
    trigger_title: str,
    date: pd.Timestamp,
    val_str: str,
    floor_str: str,
    swings: list[SwingItem],
) -> str:
    """Format warning card copy strictly according to Section 6 (no advice verbs)."""
    date_str = date.strftime("%d %b %Y")
    base = f"Warning · {trigger_title}. On {date_str}, {val_str}, below your {floor_str}."

    if swings:
        parts = []
        for s in swings:
            parts.append(f"{s.description} of {inr(s.amount)} on {s.date.strftime('%d %b')}")
        swing_txt = " · ".join(parts)
        return f"{base} These would change it most: {swing_txt}."
    return base
