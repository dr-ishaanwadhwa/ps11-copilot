"""FR-MA-1..5, FR-MA-3: rules-first reconciliation with confidence tiers.

Every bank line is walked in date order. A rule cascade (guide s.5) tries to explain it; the
combination search runs only for clubbed payments and checks whether its answer is UNIQUE (D18).

Tiers (GAP-ANALYSIS §2.1):
  AUTO     one rule, payer known, exactly one document set: posted without a human
  SUGGEST  a best answer exists but needs the accountant (payer inferred, part payment, >1 set)
  ASK      no rule fits; the right person is asked (owner for identity, accountant for allocation)
  NO_DOC   explained without a document (e.g. the owner putting in capital)

The answer key (`reconciliation_truth`) is never read here; it is used only in `score.py`.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

import pandas as pd

from .. import config
from ..load import Pack
from .audit import AuditLedger
from .names import PartyIndex, extract, norm

AUTO, SUGGEST, ASK, NO_DOC = "AUTO", "SUGGEST", "ASK", "NO_DOC"
_CHQ = re.compile(r"^CHQ (DEP|RET) - (\d+)")

# Decision 60 (Strict AUTO rule): upper bound error must be <= 1%
# ("SME-3", "EXACT_BILL") removed (193 lines, upper error bound 1.95% > 1%)
_AUTO_QUALIFIED = {
    ("SME-1", "EXACT"),      # distributor EXACT (sample size: 1,173)
    ("SME-2", "DAILY_UPI"),  # clinic DAILY_UPI (sample size: 5,991)
    ("SME-2", "MDR_NET"),    # clinic MDR_NET (sample size: 469)
}
_AUTO_MAX_AMOUNT = 100_000.0  # ₹1 Lakh materiality ceiling (D60)


@dataclass
class Match:
    txn_id: str
    business_id: str
    tier: str
    rule: str
    docs: list[tuple[str, float]] = field(default_factory=list)   # (document_id, amount applied)
    note: str = ""
    payer: str | None = None


@dataclass
class Doc:
    id: str
    kind: str            # inv | claim | bill | dc
    party: str
    date: pd.Timestamp
    remaining: float     # cash still expected (net of TDS / disallowance where the rule says so)
    due: pd.Timestamp | None = None
    paid_any: bool = False


def _paise(x: float) -> int:
    return int(round(x * 100))


def find_subsets(items: list[Doc], target: float, max_size: int, slack: float = 0.0,
                 budget: int = 200_000) -> tuple[list[list[Doc]], bool]:
    """Sets of open docs whose remaining sums to target (within +slack: round-off).

    Returns up to two solutions (enough to know whether the answer is unique) and whether the
    search finished inside its budget. Oldest documents are tried first.
    """
    vals = [_paise(d.remaining) for d in items]
    lo, hi = _paise(target), _paise(target + slack)
    sols: list[list[Doc]] = []
    nodes = 0
    suffix = [0] * (len(vals) + 1)
    for i in range(len(vals) - 1, -1, -1):
        suffix[i] = suffix[i + 1] + vals[i]

    def dfs(i: int, acc: int, chosen: list[int]) -> None:
        nonlocal nodes
        if len(sols) >= 2 or nodes > budget:
            return
        nodes += 1
        if lo <= acc <= hi and chosen:
            sols.append([items[j] for j in chosen])
            return
        if i >= len(vals) or len(chosen) >= max_size or acc + suffix[i] < lo:
            return
        if acc + vals[i] <= hi:
            dfs(i + 1, acc + vals[i], chosen + [i])
        dfs(i + 1, acc, chosen)

    dfs(0, 0, [])
    return sols, nodes <= budget


class Matcher:
    def __init__(
        self,
        pack: Pack,
        audit_ledger: AuditLedger | None = None,
        vault: Any | None = None,
        collections: list[Any] | None = None,
    ):
        self.pack = pack
        self.audit_ledger = audit_ledger if audit_ledger is not None else AuditLedger()
        self.vault = vault
        self._collections: list[Any] = list(collections or [])
        self.docs: dict[str, dict[str, list[Doc]]] = defaultdict(lambda: defaultdict(list))  # biz -> party -> docs
        self.by_id: dict[str, Doc] = {}
        self.dc: dict[str, pd.DataFrame] = {}
        self.owner_names: dict[str, list[str]] = {}
        self.cheques: dict[str, Match] = {}
        self.handle_memory: dict[str, str] = self._load_confirmed_handles()  # UPI handle -> party, learned ONLY from confirmed matches (D60)
        self.last_cash_deposit: dict[str, pd.Timestamp] = {}
        self._build()

    def record_collection(self, col: Any) -> None:
        self._collections.append(col)
        if self.vault and hasattr(self.vault, "record_collection"):
            self.vault.record_collection(col)

    def _get_collections(self, biz: str, since: pd.Timestamp | None, up_to: pd.Timestamp) -> list[Any]:
        vault_cols = self.vault.get_collections_since(biz, since, up_to) if (self.vault and hasattr(self.vault, "get_collections_since")) else []
        extra_cols = [
            c for c in self._collections
            if getattr(c, "business_id", None) == biz
            and (since is None or c.date > since)
            and c.date <= up_to
        ]
        all_cols = list(vault_cols)
        for c in extra_cols:
            if c not in all_cols:
                all_cols.append(c)
        return all_cols

    # ── documents ───────────────────────────────────────────────────────────
    def _add(self, biz: str, d: Doc) -> None:
        self.docs[biz][d.party].append(d)
        self.by_id[d.id] = d

    def _build(self) -> None:
        inv = self.pack.invoices.drop_duplicates("invoice_no")
        start = self.pack.bank.groupby("business_id")["txn_date"].min()
        for r in inv.itertuples():
            profile = config.get_profile(r.business_id)
            if profile.archetype == "clinic":            # clinic: TPA claims, net of TDS and disallowance (remittance advice)
                net = r.invoice_total - r.tds_deducted_by_customer - r.disallowed_amount
                d = Doc(r.invoice_no, "claim", r.customer_name, r.invoice_date, net, r.due_date)
            else:
                tds = config.TDS_RATE * r.taxable_value if (profile.has_tds and r.tds_applicable) else 0.0
                d = Doc(r.invoice_no, "inv", r.customer_name, r.invoice_date, r.invoice_total - tds, r.due_date)
            # Opening receivables: an invoice settled before the bank data starts is not open on day one
            if pd.notna(r.last_payment_date) and r.last_payment_date < start[r.business_id]:
                d.remaining = 0.0
            self._add(r.business_id, d)
        for r in self.pack.bills.itertuples():
            self._add(r.business_id, Doc(r.bill_no, "bill", r.supplier_name, r.bill_date, r.bill_total - r.tds_deducted_by_us, r.due_date))
        for d in self.docs.values():
            for lst in d.values():
                lst.sort(key=lambda x: (x.date, x.id))
        c = self.pack.collections.copy()
        c["dc_id"] = "DC-" + c["date"].dt.strftime("%Y-%m-%d")
        for b, prof in config.BUSINESS_PROFILES.items():
            if prof.archetype == "clinic":
                self.dc[b] = c.set_index("date")
        for r in self.pack.businesses.itertuples():
            self.owner_names[r.business_id] = [norm(r.owner_or_partner)]
        self.party_idx = {
            biz: {"in": PartyIndex([p for p, ds in parties.items() if ds and ds[0].kind in ("inv", "claim")]),
                  "out": PartyIndex([p for p, ds in parties.items() if ds and ds[0].kind == "bill"])}
            for biz, parties in self.docs.items()
        }

    def _open(self, biz: str, parties, kinds, on: pd.Timestamp, cap: int = 24) -> list[Doc]:
        pool = []
        for p in parties:
            pool += [d for d in self.docs[biz].get(p, []) if d.kind in kinds and d.date <= on and d.remaining > 0.5]
        pool.sort(key=lambda x: (x.date, x.id))
        return pool[:cap]

    def _all_open(self, biz: str, kinds, on: pd.Timestamp) -> list[Doc]:
        return [d for lst in self.docs[biz].values() for d in lst if d.kind in kinds and d.date <= on and d.remaining > 0.5]

    def _apply(self, m: Match, roundoff_doc: str | None = None) -> Match:
        for doc_id, amt in m.docs:
            d = self.by_id.get(doc_id)
            if d is None:
                continue
            d.remaining = 0.0 if doc_id == roundoff_doc else max(0.0, d.remaining - amt)
            d.paid_any = True
        return m

    # ── the cascade ─────────────────────────────────────────────────────────
    def match(self, r) -> Match | None:
        biz, amt, nar = r.business_id, abs(r.amount), str(r.narration)
        name, handle = extract(nar)
        chq = _CHQ.match(nar)

        if r.amount < 0 and chq and chq.group(1) == "RET":                 # bounce reversal (T5)
            dep = self.cheques.get(chq.group(2))
            if dep and (r.txn_date - dep.payer_date).days <= config.BOUNCE_WINDOW_DAYS:
                for doc_id, applied in dep.docs:
                    if doc_id in self.by_id:
                        self.by_id[doc_id].remaining += applied
                dep.rule, dep.tier = "BOUNCED", SUGGEST
                dep.docs = [(d, 0.0) for d, _ in dep.docs]
                return Match(r.txn_id, biz, SUGGEST, "BOUNCED", list(dep.docs), "cheque returned; invoices reopened")
            return None

        if any(o and o in norm(nar) for o in self.owner_names.get(biz, [])) or "CAPITAL" in nar.upper():
            return Match(r.txn_id, biz, NO_DOC, "OWNER_CAPITAL", [], "owner's own money: no document")

        if r.amount > 0:
            return self._receipt(r, biz, amt, name, handle, chq)
        return self._payment(r, biz, amt, name)

    def _receipt(self, r, biz, amt, name, handle, chq) -> Match | None:
        profile = config.get_profile(biz)
        if profile.archetype == "clinic":
            m = self._clinic_receipt(r, amt)
            if m:
                return m
        if r.channel == "CASH":
            if profile.archetype == "clinic":
                return None
            if profile.archetype == "distributor":
                start = self.last_cash_deposit.get(biz)
                self.last_cash_deposit[biz] = r.txn_date
                colls = self._get_collections(biz, start, r.txn_date)
                total_col = sum(c.amount for c in colls)
                if colls and abs(total_col - amt) <= 1.0:
                    shops = list(dict.fromkeys(c.shop for c in colls))
                    pool = []
                    for s in shops:
                        parties = self.party_idx[biz]["in"].resolve(s)
                        pool.extend(self._open(biz, parties if parties else [s], profile.doc_kinds, r.txn_date, cap=50))
                    pool.sort(key=lambda x: (x.date, x.id))
                    max_size = max(10, len(colls) + 2)
                    sols, done = find_subsets(pool, amt, max_size=max_size)
                    if not sols and profile.has_round_off:
                        sols, done = find_subsets(pool, amt, max_size=max_size, slack=config.ROUND_OFF_MAX)
                    if sols and len(sols) == 1 and done:
                        docs = [(d.id, d.remaining) for d in sols[0]]
                        note = f"cash deposit matched to {len(colls)} collection slips across {len(shops)} shops (D55)"
                        m = Match(r.txn_id, biz, SUGGEST, "CASH_DEPOSIT", docs, note=note)
                        return self._finish(m, None, True, r, None)
            return Match(r.txn_id, biz, ASK, "CASH_DEPOSIT",
                         note="cash deposit covering several shops: needs the salesman's collection slips")

        kinds = profile.doc_kinds
        parties = self.party_idx[biz]["in"].resolve(name)
        if not parties and handle and handle in self.handle_memory:
            parties = [self.handle_memory[handle]]
        # "known" means exactly one party: two shops with the same name in different areas is not known
        known = len(parties) == 1
        if profile.archetype == "clinic" and parties:
            # TPAs settle 30–75 days after the claim (guide s.1); older claims are pending or rejected, not due
            lo, hi = r.txn_date - pd.Timedelta(days=80), r.txn_date - pd.Timedelta(days=20)
            pool = [d for d in self._open(biz, parties, kinds, r.txn_date, cap=400) if lo <= d.date <= hi][:40]
        elif parties:
            pool = self._open(biz, parties, kinds, r.txn_date)
        else:
            pool = self._all_open(biz, kinds, r.txn_date)

        # A single exact document is AUTO when the narration names the payer (even if several same-name
        # shops exist, the one document settles which); a no-name line (cheque, personal UPI) stays SUGGEST.
        named = bool(parties)
        exact = [d for d in pool if abs(d.remaining - amt) < 0.01]
        if len(exact) == 1:
            m = Match(r.txn_id, biz, AUTO if named else SUGGEST, "EXACT", [(exact[0].id, amt)], payer=exact[0].party,
                      note="" if named else "payer inferred from the amount only: confirm")
            return self._finish(m, handle, named, r, chq)
        if profile.has_round_off:
            ro = [d for d in pool if 0 < d.remaining - amt <= config.ROUND_OFF_MAX]
            if len(ro) == 1 and not exact:
                m = Match(r.txn_id, biz, AUTO if named else SUGGEST, "ROUND_OFF", [(ro[0].id, amt)], payer=ro[0].party,
                          note=f"round-off ₹{ro[0].remaining - amt:,.0f}")
                return self._finish(m, handle, known, r, chq, roundoff_doc=ro[0].id)
        if exact:
            # Several open documents carry this amount (monthly retainers): suggest the one due nearest the payment
            best = min(exact, key=lambda d: (abs((r.txn_date - (d.due or d.date)).days), d.date))
            m = Match(r.txn_id, biz, SUGGEST, "EXACT_AMBIGUOUS", [(best.id, amt)], payer=best.party,
                      note=f"{len(exact)} open documents have this exact amount; suggested the one due nearest the payment")
            return self._finish(m, handle, named, r, chq)
        if not parties:
            return Match(r.txn_id, biz, ASK, "WHO_PAID", note="payer not recognised and no single document fits")

        max_size = profile.max_batch_size
        sols, done = find_subsets(pool, amt, max_size)
        rule = profile.batch_rule_name
        slack_used = False
        if not sols and profile.has_round_off:
            sols, done = find_subsets(pool, amt, max_size, slack=config.ROUND_OFF_MAX)
            slack_used = bool(sols)
        if sols:
            docs = [(d.id, d.remaining) for d in sols[0]]
            if slack_used:   # the last document absorbs the round-off
                short = sum(v for _, v in docs) - amt
                docs[-1] = (docs[-1][0], docs[-1][1] - short)
            # A TPA batch can hold up to 13 claims; the narration alone cannot prove which, so it is never AUTO.
            # (In production the TPA's remittance advice lists the claims; the pack does not include it.)
            unique = len(sols) == 1 and done and known and rule != "TPA_BATCH"
            m = Match(r.txn_id, biz, AUTO if unique else SUGGEST, rule, docs, payer=sols[0][0].party,
                      note="" if unique else "more than one set of invoices fits: pick one")
            return self._finish(m, handle, known, r, chq, roundoff_doc=docs[-1][0] if slack_used else None)
        if pool and amt < pool[0].remaining:
            m = Match(r.txn_id, biz, SUGGEST, "ON_ACCOUNT", [], payer=pool[0].party,
                      note=f"part payment: ₹{amt:,.0f} credited on account to {pool[0].party}; accountant to allocate")
            return self._finish(m, handle, known, r, chq)
        return Match(r.txn_id, biz, ASK, "NO_RULE", payer=parties[0], note="payer known; no rule explains the amount")

    def _clinic_receipt(self, r, amt) -> Match | None:
        biz = r.business_id
        dc = self.dc.get(biz)
        if dc is None:
            return None
        day = r.txn_date.normalize()
        if r.channel == "UPI":
            if day in dc.index:
                m = Match(r.txn_id, biz, AUTO, "DAILY_UPI", [(dc.loc[day, "dc_id"], amt)])
                return self._finish(m, None, True, r, None)
        if r.channel == "POS_SETTLEMENT":
            hits = [(d, dc.loc[d, "dc_id"]) for d in [day - pd.Timedelta(days=k) for k in (1, 2, 3)]
                    if d in dc.index and abs(dc.loc[d, "card_net_settled"] - amt) < 0.01]
            if len(hits) == 1:
                m = Match(r.txn_id, biz, AUTO, "MDR_NET", [(hits[0][1], amt)], note="card takings net of MDR")
                return self._finish(m, None, True, r, None)
        if r.channel == "CASH":
            start = self.last_cash_deposit.get(biz, day - pd.Timedelta(days=7))
            window = dc[(dc.index > start) & (dc.index <= day)]
            self.last_cash_deposit[biz] = day
            if len(window):
                total = window["cash_collected"].sum()
                docs = list(zip(window["dc_id"], window["cash_collected"]))
                tier = AUTO if abs(total - amt) < 1 else SUGGEST
                note = "" if tier == AUTO else f"₹{total - amt:,.0f} of cash taken since the last deposit is not in this deposit: to check"
                m = Match(r.txn_id, biz, tier, "CASH_DEPOSIT", docs, note)
                return self._finish(m, None, True, r, None)
        return None

    def _payment(self, r, biz, amt, name) -> Match | None:
        parties = self.party_idx[biz]["out"].resolve(name)
        if not parties:
            return None                                           # salary, GST, rent… categorised, not reconciled to a bill
        pool = self._open(biz, parties, ("bill",), r.txn_date + pd.Timedelta(days=3))
        exact = [d for d in pool if abs(d.remaining - amt) < 0.01]
        if len(exact) == 1:
            m = Match(r.txn_id, biz, AUTO, "EXACT_BILL", [(exact[0].id, amt)], payer=exact[0].party)
            return self._finish(m, None, True, r, None)
        sols, done = find_subsets(pool, amt, 6)
        if sols:
            unique = len(sols) == 1 and done
            m = Match(r.txn_id, biz, AUTO if unique else SUGGEST, "CLUBBED_BILLS",
                      [(d.id, d.remaining) for d in sols[0]], payer=sols[0][0].party)
            return self._finish(m, None, True, r, None)
        return Match(r.txn_id, biz, ASK, "NO_BILL", payer=parties[0], note="supplier known; no open bill fits")

    def _finish(self, m: Match, handle, known, r, chq, roundoff_doc=None) -> Match:
        amt = abs(r.amount)
        if m.tier == AUTO:
            rule_class = (m.business_id, m.rule)
            if self.audit_ledger and rule_class in self.audit_ledger.suspended_classes():
                m.tier = SUGGEST
                m.note = ((m.note + " · " if m.note else "") +
                          "rule suspended after an audit miss (D60)")
            elif rule_class not in _AUTO_QUALIFIED:
                m.tier = SUGGEST
                m.note = ((m.note + " · " if m.note else "") +
                          f"strict rule (D60): {m.rule} requires human confirmation")
            elif amt >= _AUTO_MAX_AMOUNT:
                m.tier = SUGGEST
                m.note = ((m.note + " · " if m.note else "") +
                          f"amount >= ₹1 Lakh (₹{amt:,.0f}): requires human confirmation")

        if chq:
            m.payer_date = r.txn_date   # type: ignore[attr-defined]
            self.cheques[chq.group(2)] = m
        return self._apply(m, roundoff_doc)

    def _load_confirmed_handles(self) -> dict[str, str]:
        path = config.STATE_DIR / "confirmed_handles.json"
        if path.exists():
            try:
                import json
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def confirm_payer(self, handle: str, party: str) -> None:
        """Person confirms a payer handle in the review queue (D60 Task 4.2)."""
        self.handle_memory[handle] = party
        config.STATE_DIR.mkdir(parents=True, exist_ok=True)
        path = config.STATE_DIR / "confirmed_handles.json"
        try:
            import json
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.handle_memory, f, indent=2)
        except Exception:
            pass


def match_all(
    pack: Pack,
    audit_ledger: AuditLedger | None = None,
    vault: Any | None = None,
    collections: list[Any] | None = None,
) -> dict[str, Match]:
    mt = Matcher(pack, audit_ledger=audit_ledger, vault=vault, collections=collections)
    out: dict[str, Match] = {}
    for r in pack.bank.sort_values(["txn_date", "seq"]).itertuples():
        m = mt.match(r)
        if m is not None:
            out[r.txn_id] = m   # a bounce rewrites its deposit's match in place, so both lines show BOUNCED
    return out
