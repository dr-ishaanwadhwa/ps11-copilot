"""Weekly audit sampling and rule suspension ledger under Decision 60 (Task 4.3).

Implements:
- 2% deterministic weekly audit sample per ISO week, at least 1 per class
- AuditLedger persisting audit checks to COPILOT_STATE_DIR
- Automatic suspension of rule classes with any incorrect audit verdict
- Team lead manual requalification of suspended rule classes
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from .. import config

if TYPE_CHECKING:
    from .engine import Match

AUTO = "AUTO"

logger = logging.getLogger(__name__)


class AuditLedger:
    def __init__(self, state_dir: Path | None = None):
        self.state_dir = state_dir or config.STATE_DIR
        self.records_path = self.state_dir / "audit_ledger.json"
        self.requal_path = self.state_dir / "requalified_classes.json"

    def _load_records(self) -> list[dict[str, Any]]:
        if self.records_path.exists():
            try:
                with open(self.records_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Failed loading audit records from %s: %s", self.records_path, exc)
                return []
        return []

    def _load_requalifications(self) -> dict[str, str]:
        if self.requal_path.exists():
            try:
                with open(self.requal_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Failed loading requalifications from %s: %s", self.requal_path, exc)
                return {}
        return {}

    def record(
        self,
        txn_id: str,
        rule_class: tuple[str, str],
        correct: bool,
        reviewer: str = "auditor",
        at: str | None = None,
    ) -> None:
        """Record an audit check result for a transaction."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        now_str = at or datetime.now(timezone.utc).isoformat()
        rec = {
            "txn_id": txn_id,
            "business_id": rule_class[0],
            "rule": rule_class[1],
            "correct": correct,
            "reviewer": reviewer,
            "at": now_str,
        }
        records = self._load_records()
        records.append(rec)
        with open(self.records_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

    def requalify(self, rule_class: tuple[str, str]) -> None:
        """Team lead manual action to restore and requalify a suspended rule class."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        key = f"{rule_class[0]}:{rule_class[1]}"
        requals = self._load_requalifications()
        requals[key] = datetime.now(timezone.utc).isoformat()
        with open(self.requal_path, "w", encoding="utf-8") as f:
            json.dump(requals, f, indent=2)

    def suspended_classes(self) -> set[tuple[str, str]]:
        """Return classes that have any correct=False after their latest re-qualification."""
        records = self._load_records()
        requals = self._load_requalifications()
        suspended: set[tuple[str, str]] = set()

        for r in records:
            cls = (r["business_id"], r["rule"])
            key = f"{cls[0]}:{cls[1]}"
            if not r["correct"]:
                last_requal = requals.get(key)
                if last_requal is None or r["at"] > last_requal:
                    suspended.add(cls)

        return suspended


def select_audit_sample(
    matches: dict[str, Match],
    bank_df: pd.DataFrame,
    week: str,
    rate: float = 0.02,
) -> list[str]:
    """Deterministically select ~2% of AUTO lines in an ISO week, at least 1 per class."""
    bank = bank_df.set_index("txn_id")
    # Filter to AUTO lines falling within the specified ISO week (e.g. '2026-W35')
    auto_lines_by_class: dict[tuple[str, str], list[tuple[str, float]]] = {}

    for txn_id, m in matches.items():
        if m.tier != AUTO or txn_id not in bank.index:
            continue
        row = bank.loc[txn_id]
        txn_week = row["txn_date"].strftime("%G-W%V")
        if txn_week != week:
            continue

        h = hashlib.sha256(f"{txn_id}:{week}".encode("utf-8")).hexdigest()
        score = int(h[:8], 16) / 0xFFFFFFFF
        cls = (m.business_id, m.rule)
        if cls not in auto_lines_by_class:
            auto_lines_by_class[cls] = []
        auto_lines_by_class[cls].append((txn_id, score))

    selected: list[str] = []
    for cls, candidates in auto_lines_by_class.items():
        cls_selected = [tid for tid, sc in candidates if sc < rate]
        if not cls_selected and candidates:
            best = min(candidates, key=lambda x: x[1])[0]
            cls_selected.append(best)
        selected.extend(cls_selected)

    return sorted(selected)
