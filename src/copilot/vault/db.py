"""Vault local database and pilot seed engine.

Maintains on-device records for:
- Galla entries (cash drawer daily balancing).
- Rokad entries (cash book in/out).
- Khata accounts (informal receivables and payables).
- Collections (salesman route collection slips).

Architecture:
- Encrypted local-first sovereign storage (ADR-001, ADR-004).
- Key derivation from Owner PIN (default '0000', configurable via COPILOT_OWNER_PIN).
- Zero plaintext on disk: volatile in-memory SQLite connection while unlocked,
  AES-256-GCM encrypted persistence at rest in .copilot_state/sovereign_vault.db.
- Gated access: locked by default until unlocked with valid PIN.
- Zero cloud telemetry, zero remote network calls.
"""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional
import uuid
import pandas as pd

from .. import config
from ..load import Pack
from .crypto import VaultCrypto, VaultDecryptionError, VaultLockedError
from .models import Collection, GallaEntry, KhataAccount, RokadEntry, PARTIAL_VIEW_NOTICE


class VaultDB:
    def __init__(
        self,
        in_memory: bool = True,
        db_path: Optional[Path | str] = None,
        pin: Optional[str] = None,
    ):
        self.in_memory = in_memory
        if db_path is not None:
            self.db_path: Optional[Path] = Path(db_path)
            self.in_memory = False
        elif not in_memory:
            config.STATE_DIR.mkdir(parents=True, exist_ok=True)
            self.db_path = config.STATE_DIR / "sovereign_vault.db"
        else:
            self.db_path = None

        self._unlocked: bool = False
        self._current_pin: Optional[str] = None
        self.conn: Optional[sqlite3.Connection] = None

        self.galla_records: Dict[str, List[GallaEntry]] = {"SME-1": [], "SME-2": [], "SME-3": []}
        self.rokad_records: Dict[str, List[RokadEntry]] = {"SME-1": [], "SME-2": [], "SME-3": []}
        self.khata_records: Dict[str, Dict[str, KhataAccount]] = {"SME-1": {}, "SME-2": {}, "SME-3": {}}
        self.collection_records: Dict[str, List[Collection]] = {"SME-1": [], "SME-2": [], "SME-3": []}

        if pin is not None:
            self.unlock(pin)

    # ── Gated Access & Lifecycle ───────────────────────────────────────────
    def is_unlocked(self) -> bool:
        """Return True if the vault is currently unlocked."""
        return self._unlocked

    def _ensure_unlocked(self) -> None:
        if not self.is_unlocked():
            raise VaultLockedError(
                "Vault is locked. Owner PIN is required to access sovereign cash records."
            )

    def unlock(self, pin: str) -> bool:
        """Validate Owner PIN and load/decrypt database into volatile RAM.

        Returns True on successful unlock, False on authentication failure.
        """
        configured_pin = VaultCrypto.get_configured_pin()

        if self.db_path is not None and self.db_path.exists() and self.db_path.stat().st_size > 0:
            try:
                plaintext = VaultCrypto.decrypt_from_file(self.db_path, pin)
            except (VaultDecryptionError, Exception):
                return False

            self.conn = sqlite3.connect(":memory:", check_same_thread=False)
            self.conn.deserialize(plaintext)
            self._unlocked = True
            self._current_pin = pin
            self._load_records_from_db()
            return True

        if pin != configured_pin:
            return False

        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._init_tables()
        self._unlocked = True
        self._current_pin = pin

        if self.db_path is not None:
            self._flush_to_disk()

        return True

    def lock(self) -> None:
        """Wipe decrypted state from memory and lock the vault."""
        if self.is_unlocked() and self.db_path is not None and self._current_pin is not None:
            self._flush_to_disk()

        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

        self._unlocked = False
        self._current_pin = None

        self.galla_records = {"SME-1": [], "SME-2": [], "SME-3": []}
        self.rokad_records = {"SME-1": [], "SME-2": [], "SME-3": []}
        self.khata_records = {"SME-1": {}, "SME-2": {}, "SME-3": {}}
        self.collection_records = {"SME-1": [], "SME-2": [], "SME-3": []}

    def _flush_to_disk(self) -> None:
        """Encrypt volatile SQLite database and atomically persist to disk."""
        if self.db_path is None or self.conn is None:
            return
        pin = self._current_pin or VaultCrypto.get_configured_pin()
        raw_sqlite_bytes = self.conn.serialize()
        VaultCrypto.encrypt_to_file(raw_sqlite_bytes, pin=pin, dest_path=self.db_path)

    def _init_tables(self) -> None:
        if self.conn is None:
            return
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS collections (
                    slip_id TEXT PRIMARY KEY,
                    business_id TEXT,
                    date TEXT,
                    shop TEXT,
                    amount REAL,
                    salesman TEXT,
                    payment_mode TEXT,
                    invoice_no TEXT,
                    is_banked INTEGER,
                    bank_txn_id TEXT,
                    notes TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS galla_entries (
                    entry_id TEXT PRIMARY KEY,
                    business_id TEXT,
                    date TEXT,
                    opening_cash REAL,
                    cash_in REAL,
                    cash_out REAL,
                    cash_banked REAL,
                    counted_cash REAL,
                    notes TEXT,
                    is_demo INTEGER
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS rokad_entries (
                    entry_id TEXT PRIMARY KEY,
                    business_id TEXT,
                    timestamp TEXT,
                    direction TEXT,
                    amount REAL,
                    category TEXT,
                    counterparty TEXT,
                    note TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS khata_accounts (
                    party_name TEXT,
                    business_id TEXT,
                    balance_due REAL,
                    last_active_date TEXT,
                    months_open INTEGER,
                    phone TEXT,
                    is_demo INTEGER,
                    PRIMARY KEY (party_name, business_id)
                )
            """)

    def _load_records_from_db(self) -> None:
        """Hydrate in-memory collections and data structures from decrypted tables."""
        if self.conn is None:
            return

        self.galla_records = {"SME-1": [], "SME-2": [], "SME-3": []}
        self.rokad_records = {"SME-1": [], "SME-2": [], "SME-3": []}
        self.khata_records = {"SME-1": {}, "SME-2": {}, "SME-3": {}}
        self.collection_records = {"SME-1": [], "SME-2": [], "SME-3": []}

        # Hydrate galla
        try:
            cur = self.conn.execute(
                "SELECT business_id, date, opening_cash, cash_in, cash_out, cash_banked, counted_cash, notes, is_demo "
                "FROM galla_entries ORDER BY date"
            )
            for row in cur.fetchall():
                biz, d, op, ci, co, cb, cc, n, demo = row
                entry = GallaEntry(
                    business_id=biz,
                    date=pd.Timestamp(d),
                    opening_cash=float(op),
                    cash_in=float(ci),
                    cash_out=float(co),
                    cash_banked=float(cb),
                    counted_cash=float(cc),
                    notes=n or "",
                    is_demo=bool(demo),
                )
                self.galla_records.setdefault(biz, []).append(entry)
        except sqlite3.OperationalError:
            pass

        # Hydrate collections
        try:
            cur = self.conn.execute(
                "SELECT slip_id, business_id, date, shop, amount, salesman, payment_mode, invoice_no, is_banked, bank_txn_id, notes "
                "FROM collections ORDER BY date"
            )
            for row in cur.fetchall():
                sid, biz, d, s, a, sm, pm, inv, ib, btx, n = row
                col = Collection(
                    business_id=biz,
                    date=pd.Timestamp(d),
                    shop=s,
                    amount=float(a),
                    salesman=sm or "",
                    payment_mode=pm or "CASH",
                    slip_id=sid or "",
                    invoice_no=inv or "",
                    is_banked=bool(ib),
                    bank_txn_id=btx or "",
                    notes=n or "",
                )
                self.collection_records.setdefault(biz, []).append(col)
        except sqlite3.OperationalError:
            pass

        # Hydrate rokad
        try:
            cur = self.conn.execute(
                "SELECT entry_id, business_id, timestamp, direction, amount, category, counterparty, note "
                "FROM rokad_entries ORDER BY timestamp"
            )
            for row in cur.fetchall():
                eid, biz, ts, dr, amt, cat, cp, n = row
                rok = RokadEntry(
                    entry_id=eid,
                    business_id=biz,
                    timestamp=pd.Timestamp(ts),
                    direction=dr,
                    amount=float(amt),
                    category=cat,
                    counterparty=cp,
                    note=n or "",
                )
                self.rokad_records.setdefault(biz, []).append(rok)
        except sqlite3.OperationalError:
            pass

        # Hydrate khata
        try:
            cur = self.conn.execute(
                "SELECT party_name, business_id, balance_due, last_active_date, months_open, phone, is_demo "
                "FROM khata_accounts"
            )
            for row in cur.fetchall():
                pname, biz, bal, lad, mo, ph, demo = row
                kacc = KhataAccount(
                    party_name=pname,
                    business_id=biz,
                    balance_due=float(bal),
                    last_active_date=pd.Timestamp(lad),
                    months_open=int(mo),
                    phone=ph or "",
                    is_demo=bool(demo),
                )
                self.khata_records.setdefault(biz, {})[pname] = kacc
        except sqlite3.OperationalError:
            pass

    # ── Sovereign Operations (PIN-Gated) ───────────────────────────────────
    def record_galla(self, entry: GallaEntry) -> None:
        self._ensure_unlocked()
        self.galla_records.setdefault(entry.business_id, []).append(entry)
        entry_id = f"GAL-{uuid.uuid4().hex[:8].upper()}"
        if self.conn is not None:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO galla_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (entry_id, entry.business_id, str(entry.date), entry.opening_cash, entry.cash_in,
                     entry.cash_out, entry.cash_banked, entry.counted_cash, entry.notes, int(entry.is_demo)),
                )
            self._flush_to_disk()

    def record_collection(self, entry: Collection | dict, update_drawer: bool = True) -> str:
        """Persist route collection slip, optionally update cash drawer takings, and return slip_id."""
        self._ensure_unlocked()
        if isinstance(entry, dict):
            entry = Collection(**entry)
        if not entry.slip_id:
            entry.slip_id = f"SLIP-{uuid.uuid4().hex[:8].upper()}"

        self.collection_records.setdefault(entry.business_id, []).append(entry)

        if self.conn is not None:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO collections VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        entry.slip_id,
                        entry.business_id,
                        str(entry.date),
                        entry.shop,
                        entry.amount,
                        entry.salesman,
                        entry.payment_mode,
                        entry.invoice_no,
                        int(entry.is_banked),
                        entry.bank_txn_id,
                        entry.notes,
                    ),
                )

        if update_drawer and entry.payment_mode == "CASH":
            day_entry = None
            entry_date_norm = pd.Timestamp(entry.date).normalize()
            for g in reversed(self.galla_records.get(entry.business_id, [])):
                if pd.Timestamp(g.date).normalize() == entry_date_norm:
                    day_entry = g
                    break

            if day_entry is not None:
                day_entry.cash_in = round(day_entry.cash_in + entry.amount, 2)
                if self.conn is not None:
                    with self.conn:
                        self.conn.execute(
                            "UPDATE galla_entries SET cash_in = ? WHERE business_id = ? AND date = ?",
                            (day_entry.cash_in, day_entry.business_id, str(day_entry.date)),
                        )
            else:
                new_g = GallaEntry(
                    business_id=entry.business_id,
                    date=pd.Timestamp(entry.date),
                    opening_cash=0.0,
                    cash_in=round(entry.amount, 2),
                    cash_out=0.0,
                    cash_banked=0.0,
                    counted_cash=round(entry.amount, 2),
                    notes="Auto-initialized from cash collection",
                )
                self.record_galla(new_g)

        self._flush_to_disk()
        return entry.slip_id

    def get_collections(
        self,
        biz: str,
        start: Optional[pd.Timestamp] = None,
        end: Optional[pd.Timestamp] = None,
    ) -> List[Collection]:
        """Return decrypted collection slips for business within date range."""
        self._ensure_unlocked()
        records = self.collection_records.get(biz, [])
        res = []
        for c in records:
            if start is not None and c.date < start:
                continue
            if end is not None and c.date > end:
                continue
            res.append(c)
        return res

    def get_collections_since(
        self,
        biz: str,
        since_date: Optional[pd.Timestamp] = None,
        up_to_date: Optional[pd.Timestamp] = None,
    ) -> List[Collection]:
        self._ensure_unlocked()
        records = self.collection_records.get(biz, [])
        res = []
        for c in records:
            if since_date is not None and c.date <= since_date:
                continue
            if up_to_date is not None and c.date > up_to_date:
                continue
            res.append(c)
        return res

    def get_unbanked_collections(self, biz: str) -> List[Collection]:
        """Return decrypted collection slips for business that have not been deposited/banked."""
        self._ensure_unlocked()
        records = self.collection_records.get(biz, [])
        return [c for c in records if not c.is_banked]

    def get_collections_for_shop(self, biz: str, shop: str) -> List[Collection]:
        """Return decrypted collection slips for a specific shop / retailer."""
        self._ensure_unlocked()
        records = self.collection_records.get(biz, [])
        target = shop.strip().lower()
        return [c for c in records if c.shop == shop or c.shop.strip().lower() == target]

    def mark_collection_banked(self, slip_id: str, bank_txn_id: str = "") -> None:
        """Mark a collection slip as banked and link it to a bank deposit transaction."""
        self._ensure_unlocked()
        for biz_records in self.collection_records.values():
            for c in biz_records:
                if c.slip_id == slip_id:
                    c.is_banked = True
                    c.bank_txn_id = bank_txn_id
        if self.conn is not None:
            with self.conn:
                self.conn.execute(
                    "UPDATE collections SET is_banked = 1, bank_txn_id = ? WHERE slip_id = ?",
                    (bank_txn_id, slip_id),
                )
            self._flush_to_disk()

    def allocate_collection_to_invoices(
        self,
        collection: Collection | dict,
        open_invoices: pd.DataFrame,
        mode: str = "FIFO",
    ) -> list[dict]:
        """Allocate collection slip against open invoices (FIFO or explicit)."""
        return allocate_collection_to_invoices(collection, open_invoices, mode=mode)

    def record_rokad(self, entry: RokadEntry) -> None:
        self._ensure_unlocked()
        self.rokad_records.setdefault(entry.business_id, []).append(entry)
        if self.conn is not None:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO rokad_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        entry.entry_id,
                        entry.business_id,
                        str(entry.timestamp),
                        entry.direction,
                        entry.amount,
                        entry.category,
                        entry.counterparty,
                        entry.note,
                    ),
                )
            self._flush_to_disk()

    def get_latest_galla(self, biz: str) -> Optional[GallaEntry]:
        self._ensure_unlocked()
        records = self.galla_records.get(biz, [])
        return records[-1] if records else None

    def get_ytd_cash_deposits(self, biz: str) -> float:
        """Total cash banked recorded in the vault for this business."""
        self._ensure_unlocked()
        return sum(g.cash_banked for g in self.galla_records.get(biz, []))

    def get_khata_summary(self, biz: str) -> dict:
        self._ensure_unlocked()
        accounts = list(self.khata_records.get(biz, {}).values())
        receivables = sum(a.balance_due for a in accounts if a.balance_due > 0)
        payables = sum(abs(a.balance_due) for a in accounts if a.balance_due < 0)
        return {
            "receivables": receivables,
            "payables": payables,
            "account_count": len(accounts),
            "accounts": accounts,
        }

    def compute_solvency(
        self,
        pack: Pack,
        biz: str,
        as_of: pd.Timestamp = pd.Timestamp("2026-09-30"),
        haircut_alpha: float | None = None,
    ):
        """Compute the dual-plane true solvency position for an SME business."""
        self._ensure_unlocked()
        from .. import config
        from .solvency import compute_total_solvency

        alpha = haircut_alpha if haircut_alpha is not None else config.KHATA_COLLECTION_ASSUMPTION
        return compute_total_solvency(pack, self, biz, as_of=as_of, haircut_alpha=alpha)

    def chasing_reminders(
        self,
        biz: str,
        business_name: str | None = None,
        upi_handle: str = "",
    ) -> list[dict]:
        """Generate structured collection reminders for all khata accounts."""
        self._ensure_unlocked()
        from .. import config
        from .chase import format_whatsapp_reminder

        bname = business_name or config.BUSINESSES.get(biz, biz)
        reminders = []
        for name, account in self.khata_records.get(biz, {}).items():
            if account.balance_due > 0:
                reminders.append({
                    "customer": name,
                    "account": account,
                    "reminder": format_whatsapp_reminder(account, bname, upi_handle),
                })
        return reminders

    # ── Public Plane Interface (Accessible without PIN) ────────────────────
    def compliance_facts(
        self,
        ytd_cash_deposits: float,
        account_type: str = "CURRENT",
        has_pan: bool = True,
    ):
        """Retrieve factual compliance limits under Income-tax Rules Rule 237."""
        from .guardrails import cash_deposit_reporting_facts
        return cash_deposit_reporting_facts(ytd_cash_deposits, account_type=account_type, has_pan=has_pan)

    def deposit_checklist(self) -> dict:
        """Documents recommended for cash deposit verification."""
        from .guardrails import deposit_records_checklist
        return deposit_records_checklist()

    def get_view_notice(self) -> str:
        """Return the statutory partial view notice for public plane views."""
        return PARTIAL_VIEW_NOTICE

    # ── Seed Engine ────────────────────────────────────────────────────────
    def seed_from_pack(self, pack: Pack, pin: Optional[str] = None) -> None:
        """Populate realistic vault historical data from the PS-11 data pack."""
        if not self.is_unlocked():
            unlock_pin = pin or VaultCrypto.get_configured_pin()
            self.unlock(unlock_pin)

        # 1. SME-2 (Clinic) cash bridge seeding from pack.collections
        if hasattr(pack, "collections") and not pack.collections.empty:
            coll = pack.collections.sort_values("date")
            running_cash = 10_000.0  # initial till float
            for r in coll.itertuples():
                cash_in = float(r.cash_collected)
                cash_out = round(cash_in * 0.102, 2)
                cash_banked = round(cash_in * 0.895, 2) if running_cash > 40_000 else 0.0
                counted = round(running_cash + cash_in - cash_out - cash_banked, 2)

                entry = GallaEntry(
                    business_id="SME-2",
                    date=r.date,
                    opening_cash=running_cash,
                    cash_in=cash_in,
                    cash_out=cash_out,
                    cash_banked=cash_banked,
                    counted_cash=counted,
                    notes="Daily front-desk chair cash balancing",
                )
                self.record_galla(entry)
                running_cash = counted

        # 2. SME-1 (Distributor) Galla and Salesman collections (Demo data)
        galla_sme1 = GallaEntry(
            business_id="SME-1",
            date=pd.Timestamp("2026-09-30"),
            opening_cash=420_000.0,
            cash_in=185_000.0,
            cash_out=65_000.0,
            cash_banked=120_000.0,
            counted_cash=420_000.0,
            notes="Godown main till cash float",
            is_demo=True,
        )
        self.record_galla(galla_sme1)

        # Seed SME-1 informal retailer khata accounts (Demo data)
        sme1_retailers = [
            ("Laxmi Kirana Stores", 85_000.0, 12, "+91 00000 00001"),
            ("Gajanan Departmental Stores", 62_000.0, 8, "+91 00000 00002"),
            ("Matoshree Supermarket", 114_000.0, 31, "+91 00000 00003"),
            ("Jai Bhavani Traders", -45_000.0, 4, "+91 00000 00004"),
        ]
        for name, bal, months, phone in sme1_retailers:
            kacc = KhataAccount(
                party_name=name,
                business_id="SME-1",
                balance_due=bal,
                last_active_date=pd.Timestamp("2026-09-20"),
                months_open=months,
                phone=phone,
                is_demo=True,
            )
            self.khata_records["SME-1"][name] = kacc
            if self.conn is not None:
                with self.conn:
                    self.conn.execute(
                        "INSERT OR REPLACE INTO khata_accounts VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (name, "SME-1", bal, "2026-09-20", months, phone, 1),
                    )

        # 3. SME-3 (Agency, Demo data)
        galla_sme3 = GallaEntry(
            business_id="SME-3",
            date=pd.Timestamp("2026-09-30"),
            opening_cash=85_000.0,
            cash_in=25_000.0,
            cash_out=15_000.0,
            cash_banked=0.0,
            counted_cash=95_000.0,
            notes="Office emergency contingency petty cash",
            is_demo=True,
        )
        self.record_galla(galla_sme3)
        self._flush_to_disk()


def allocate_collection_to_invoices(
    collection: Collection | dict,
    open_invoices: pd.DataFrame,
    mode: str = "FIFO",
) -> list[dict]:
    """Allocate a collection slip amount against outstanding invoice balances.

    Supports:
    - FIFO allocation (oldest invoice first sorted by invoice_date ascending).
    - Explicit / targeted allocation if collection specifies invoice_no.

    Returns a list of allocation breakdown dictionaries.
    """
    if open_invoices is None or open_invoices.empty:
        return []

    # Normalize collection fields
    if isinstance(collection, dict):
        amt = float(collection.get("amount", 0.0))
        target_inv = str(collection.get("invoice_no", "") or "").strip()
        shop = str(collection.get("shop", "") or collection.get("shop_name", "") or "").strip()
        slip_id = str(collection.get("slip_id", "") or collection.get("slip_no", "") or "").strip()
    else:
        amt = float(getattr(collection, "amount", 0.0))
        target_inv = str(getattr(collection, "invoice_no", "") or "").strip()
        shop = str(getattr(collection, "shop", "") or getattr(collection, "shop_name", "") or "").strip()
        slip_id = str(getattr(collection, "slip_id", "") or getattr(collection, "slip_no", "") or "").strip()

    if amt <= 0:
        return []

    df = open_invoices.copy()

    # Filter to specific shop if customer_name / shop column exists and shop is specified
    cust_col = None
    for candidate in ["customer_name", "shop", "party_name", "shop_name"]:
        if candidate in df.columns:
            cust_col = candidate
            break

    if cust_col and shop:
        matched_mask = (df[cust_col] == shop) | (df[cust_col].astype(str).str.strip().str.lower() == shop.lower())
        if matched_mask.any():
            df = df[matched_mask].copy()

    # Determine outstanding balance per row
    def get_outstanding(row) -> float:
        for col in ["outstanding", "balance", "balance_due", "remaining"]:
            if col in row.index and pd.notna(row[col]):
                return float(row[col])
        if "invoice_total" in row.index:
            total = float(row.get("invoice_total", 0.0) or 0.0)
            rec = float(row.get("amount_received", 0.0) or 0.0) if "amount_received" in row.index and pd.notna(row["amount_received"]) else 0.0
            tds = float(row.get("tds_deducted_by_customer", 0.0) or 0.0) if "tds_deducted_by_customer" in row.index and pd.notna(row["tds_deducted_by_customer"]) else 0.0
            dis = float(row.get("disallowed_amount", 0.0) or 0.0) if "disallowed_amount" in row.index and pd.notna(row["disallowed_amount"]) else 0.0
            return max(0.0, total - rec - tds - dis)
        if "amount" in row.index and pd.notna(row["amount"]):
            return float(row["amount"])
        return 0.0

    df["_calc_outstanding"] = df.apply(get_outstanding, axis=1)
    df = df[df["_calc_outstanding"] > 0.001].copy()
    if df.empty:
        return []

    # Sort invoices according to mode and target invoice
    mode_upper = (mode or "FIFO").upper()
    if "invoice_date" in df.columns:
        df["_sort_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")
        df = df.sort_values("_sort_date", ascending=True)

    # If target invoice is specified and exists, prioritize it
    if target_inv and "invoice_no" in df.columns:
        target_mask = df["invoice_no"].astype(str).str.strip() == target_inv
        if target_mask.any():
            target_df = df[target_mask]
            other_df = df[~target_mask]
            if mode_upper in ("EXPLICIT", "SPECIFIC", "TARGETED"):
                df_ordered = target_df
            else:
                df_ordered = pd.concat([target_df, other_df], ignore_index=True)
        else:
            df_ordered = df
    else:
        df_ordered = df

    remaining_coll = amt
    allocations: list[dict] = []

    for _, row in df_ordered.iterrows():
        if remaining_coll <= 0.001:
            break

        inv_no = str(row.get("invoice_no", ""))
        inv_date = row.get("invoice_date", None)
        cust_name = str(row[cust_col]) if cust_col and cust_col in row else shop
        inv_total = float(row.get("invoice_total", row["_calc_outstanding"]))
        prev_bal = round(row["_calc_outstanding"], 2)

        alloc_amt = round(min(remaining_coll, prev_bal), 2)
        new_bal = round(max(0.0, prev_bal - alloc_amt), 2)
        remaining_coll = round(max(0.0, remaining_coll - alloc_amt), 2)

        allocations.append({
            "slip_id": slip_id,
            "invoice_no": inv_no,
            "invoice_date": inv_date,
            "customer_name": cust_name,
            "invoice_total": inv_total,
            "previous_balance": prev_bal,
            "outstanding": prev_bal,
            "allocated_amount": alloc_amt,
            "amount": alloc_amt,
            "remaining_balance": new_bal,
            "status": "PAID" if new_bal <= 0.01 else "PARTIALLY_PAID",
        })

    return allocations
